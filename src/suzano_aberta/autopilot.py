from __future__ import annotations

import json
import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from typing import Any, Literal

from .lineage import LineageDataset, LineageEvent, LineageJournal, emit_lineage, new_run_id
from .observability import add_span_event, operation_span
from .release import manifest_path_for, write_snapshot_manifest
from .snapshot import SnapshotError, snapshot_checksum_path, sync_latest_snapshot

AutopilotAction = Literal["updated", "current", "skipped", "busy", "failed"]


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AutoUpdatePolicy:
    check_interval_seconds: int = 900
    failure_backoff_seconds: int = 300
    max_stale_seconds: int = 21_600
    lock_stale_seconds: int = 1_800
    minimum_records_ratio: float = 0.85

    def __post_init__(self) -> None:
        if self.check_interval_seconds < 0:
            raise ValueError("check_interval_seconds não pode ser negativo")
        if self.failure_backoff_seconds < 1:
            raise ValueError("failure_backoff_seconds deve ser positivo")
        if self.max_stale_seconds < 1:
            raise ValueError("max_stale_seconds deve ser positivo")
        if self.lock_stale_seconds < 1:
            raise ValueError("lock_stale_seconds deve ser positivo")
        if not 0.0 < self.minimum_records_ratio <= 1.0:
            raise ValueError("minimum_records_ratio deve estar entre 0 e 1")


@dataclass(frozen=True, slots=True)
class AutopilotStatus:
    database: str
    database_exists: bool
    records: int
    due: bool
    fresh: bool
    locked: bool
    last_attempt_at: str | None
    last_success_at: str | None
    last_error: str | None
    consecutive_failures: int
    successful_checks: int
    updates: int
    remote_checksum: str | None
    database_modified_at: str | None
    next_check_at: str | None
    quality_status: str | None = None
    quality_score: int | None = None
    manifest_sha256: str | None = None
    lineage_run_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AutopilotResult:
    action: AutopilotAction
    records: int
    checked_at: str
    checksum: str | None = None
    error: str | None = None
    quality_status: str | None = None
    quality_score: int | None = None
    manifest_sha256: str | None = None
    lineage_run_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.action != "failed"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AutonomousDataManager:
    """Mantém um snapshot local fresco, validado e observável sem operação manual."""

    def __init__(
        self,
        database: str | Path = "suzano-aberta.sqlite3",
        *,
        policy: AutoUpdatePolicy | None = None,
        timeout: float = 120.0,
        state_path: str | Path | None = None,
        lock_path: str | Path | None = None,
    ) -> None:
        self.database = Path(database)
        self.policy = policy or AutoUpdatePolicy()
        self.timeout = timeout
        self.state_path = Path(state_path) if state_path is not None else Path(f"{self.database}.autopilot.json")
        self.lock_path = Path(lock_path) if lock_path is not None else Path(f"{self.database}.autopilot.lock")
        self.lineage = LineageJournal(Path(f"{self.database}.lineage.jsonl"))

    def _read_state(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_state(self, payload: dict[str, object]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(f".{self.state_path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.state_path)

    def _record_count(self) -> int:
        if not self.database.exists():
            return 0
        try:
            connection = sqlite3.connect(f"file:{self.database.resolve().as_posix()}?mode=ro", uri=True)
            try:
                row = connection.execute("SELECT COUNT(*) FROM records WHERE active=1").fetchone()
            finally:
                connection.close()
        except sqlite3.Error:
            return 0
        return int(row[0]) if row is not None else 0

    def _remote_checksum(self) -> str | None:
        path = snapshot_checksum_path(self.database)
        try:
            value = path.read_text(encoding="utf-8").strip().split()[0]
        except (FileNotFoundError, OSError, IndexError):
            return None
        return value or None

    def _is_lock_stale(self) -> bool:
        try:
            age = time.time() - self.lock_path.stat().st_mtime
        except OSError:
            return False
        return age > self.policy.lock_stale_seconds

    def _acquire_lock(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if not self._is_lock_stale():
                    return False
                try:
                    self.lock_path.unlink()
                except OSError:
                    return False
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump({"pid": os.getpid(), "acquired_at": _now().isoformat()}, handle)
            return True
        return False

    def _release_lock(self) -> None:
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass

    def _schedule(self, state: dict[str, Any], now: datetime) -> tuple[bool, str | None]:
        last_attempt = _parse_datetime(state.get("last_attempt_at"))
        failures = int(state.get("consecutive_failures") or 0)
        interval = self.policy.failure_backoff_seconds if failures else self.policy.check_interval_seconds
        if last_attempt is None:
            return True, None
        next_check = last_attempt + timedelta(seconds=interval)
        return now >= next_check, next_check.isoformat()

    def status(self) -> AutopilotStatus:
        state = self._read_state()
        now = _now()
        due, next_check = self._schedule(state, now)
        records = self._record_count()
        last_success = _parse_datetime(state.get("last_success_at"))
        if last_success is None and self.database.exists():
            try:
                last_success = datetime.fromtimestamp(self.database.stat().st_mtime, tz=UTC)
            except OSError:
                last_success = None
        fresh = records > 0 and last_success is not None and now - last_success <= timedelta(seconds=self.policy.max_stale_seconds)
        modified_at: str | None = None
        if self.database.exists():
            try:
                modified_at = datetime.fromtimestamp(self.database.stat().st_mtime, tz=UTC).isoformat()
            except OSError:
                pass
        return AutopilotStatus(
            database=str(self.database),
            database_exists=self.database.exists(),
            records=records,
            due=due or records == 0,
            fresh=fresh,
            locked=self.lock_path.exists() and not self._is_lock_stale(),
            last_attempt_at=str(state.get("last_attempt_at")) if state.get("last_attempt_at") else None,
            last_success_at=last_success.isoformat() if last_success is not None else None,
            last_error=str(state.get("last_error")) if state.get("last_error") else None,
            consecutive_failures=int(state.get("consecutive_failures") or 0),
            successful_checks=int(state.get("successful_checks") or 0),
            updates=int(state.get("updates") or 0),
            remote_checksum=self._remote_checksum(),
            database_modified_at=modified_at,
            next_check_at=next_check,
            quality_status=str(state.get("quality_status")) if state.get("quality_status") else None,
            quality_score=int(state["quality_score"]) if isinstance(state.get("quality_score"), int) else None,
            manifest_sha256=str(state.get("manifest_sha256")) if state.get("manifest_sha256") else None,
            lineage_run_id=str(state.get("lineage_run_id")) if state.get("lineage_run_id") else None,
        )

    def ensure_fresh(self, *, force: bool = False) -> AutopilotResult:
        with operation_span(
            "suzano.autopilot.ensure_fresh",
            attributes={"database": str(self.database), "force": force},
        ):
            return self._ensure_fresh(force=force)

    def _ensure_fresh(self, *, force: bool) -> AutopilotResult:
        now = _now()
        state = self._read_state()
        due, _ = self._schedule(state, now)
        records_before = self._record_count()
        if not force and records_before > 0 and not due:
            return AutopilotResult(
                action="skipped",
                records=records_before,
                checked_at=now.isoformat(),
                checksum=self._remote_checksum(),
                quality_status=str(state.get("quality_status")) if state.get("quality_status") else None,
                quality_score=int(state["quality_score"]) if isinstance(state.get("quality_score"), int) else None,
                manifest_sha256=str(state.get("manifest_sha256")) if state.get("manifest_sha256") else None,
                lineage_run_id=str(state.get("lineage_run_id")) if state.get("lineage_run_id") else None,
            )
        if not self._acquire_lock():
            return AutopilotResult(
                action="busy",
                records=records_before,
                checked_at=now.isoformat(),
                checksum=self._remote_checksum(),
            )

        run_id = new_run_id()
        input_dataset = LineageDataset(namespace="github-release", name="suzano-aberta/data-latest")
        output_dataset = LineageDataset(namespace="sqlite", name=str(self.database))
        emit_lineage(
            LineageEvent(event_type="START", run_id=run_id, job_name="autopilot.sync", inputs=[input_dataset], outputs=[output_dataset]),
            journal=self.lineage,
        )
        add_span_event("autopilot.sync.start", {"run_id": run_id})

        try:
            state = self._read_state()
            if not force:
                due_after_lock, _ = self._schedule(state, now)
                records_after_lock = self._record_count()
                if records_after_lock > 0 and not due_after_lock:
                    emit_lineage(
                        LineageEvent(event_type="COMPLETE", run_id=run_id, job_name="autopilot.sync", inputs=[input_dataset], outputs=[output_dataset], run_facets={"result": {"value": "skipped-after-lock"}}),
                        journal=self.lineage,
                    )
                    return AutopilotResult(
                        action="skipped",
                        records=records_after_lock,
                        checked_at=now.isoformat(),
                        checksum=self._remote_checksum(),
                        lineage_run_id=run_id,
                    )

            checksum_before = self._remote_checksum()
            minimum_records = max(1, int(records_before * self.policy.minimum_records_ratio)) if records_before else 1
            try:
                records = sync_latest_snapshot(
                    self.database,
                    timeout=self.timeout,
                    min_records=minimum_records,
                )
                current_manifest_path = manifest_path_for(self.database)
                previous_manifest = current_manifest_path if current_manifest_path.exists() else None
                _, quality, manifest_digest = write_snapshot_manifest(
                    self.database,
                    previous_manifest=previous_manifest,
                    lineage_run_id=run_id,
                )
            except (SnapshotError, OSError, ValueError) as exc:
                failures = int(state.get("consecutive_failures") or 0) + 1
                failure_state: dict[str, object] = {
                    "schema": 2,
                    "last_attempt_at": now.isoformat(),
                    "last_success_at": state.get("last_success_at") if isinstance(state.get("last_success_at"), str) else None,
                    "last_error": f"{type(exc).__name__}: {exc}",
                    "consecutive_failures": failures,
                    "successful_checks": int(state.get("successful_checks") or 0),
                    "updates": int(state.get("updates") or 0),
                    "records": self._record_count(),
                    "remote_checksum": self._remote_checksum(),
                    "quality_status": state.get("quality_status"),
                    "quality_score": state.get("quality_score"),
                    "manifest_sha256": state.get("manifest_sha256"),
                    "lineage_run_id": run_id,
                }
                self._write_state(failure_state)
                emit_lineage(
                    LineageEvent(event_type="FAIL", run_id=run_id, job_name="autopilot.sync", inputs=[input_dataset], outputs=[output_dataset], run_facets={"error": {"message": str(exc), "type": type(exc).__name__}}),
                    journal=self.lineage,
                )
                add_span_event("autopilot.sync.failed", {"run_id": run_id, "error": str(exc)})
                return AutopilotResult(
                    action="failed",
                    records=self._record_count(),
                    checked_at=now.isoformat(),
                    checksum=self._remote_checksum(),
                    error=str(failure_state["last_error"]),
                    lineage_run_id=run_id,
                )

            checksum_after = self._remote_checksum()
            changed = records_before == 0 or checksum_before != checksum_after
            success_state: dict[str, object] = {
                "schema": 2,
                "last_attempt_at": now.isoformat(),
                "last_success_at": now.isoformat(),
                "last_error": None,
                "consecutive_failures": 0,
                "successful_checks": int(state.get("successful_checks") or 0) + 1,
                "updates": int(state.get("updates") or 0) + (1 if changed else 0),
                "records": records,
                "remote_checksum": checksum_after,
                "quality_status": quality.status,
                "quality_score": quality.score,
                "manifest_sha256": manifest_digest,
                "lineage_run_id": run_id,
            }
            self._write_state(success_state)
            emit_lineage(
                LineageEvent(
                    event_type="COMPLETE",
                    run_id=run_id,
                    job_name="autopilot.sync",
                    inputs=[input_dataset],
                    outputs=[output_dataset],
                    run_facets={
                        "suzanoQuality": {
                            "status": quality.status,
                            "score": quality.score,
                            "manifestSha256": manifest_digest,
                        }
                    },
                ),
                journal=self.lineage,
            )
            add_span_event("autopilot.sync.complete", {"run_id": run_id, "records": records, "quality_score": quality.score})
            return AutopilotResult(
                action="updated" if changed else "current",
                records=records,
                checked_at=now.isoformat(),
                checksum=checksum_after,
                quality_status=quality.status,
                quality_score=quality.score,
                manifest_sha256=manifest_digest,
                lineage_run_id=run_id,
            )
        finally:
            self._release_lock()

    def run_forever(
        self,
        *,
        stop_event: Event | None = None,
        on_result: Callable[[AutopilotResult], None] | None = None,
    ) -> None:
        stopper = stop_event or Event()
        while not stopper.is_set():
            result = self.ensure_fresh()
            if on_result is not None:
                on_result(result)
            interval = self.policy.failure_backoff_seconds if result.action == "failed" else self.policy.check_interval_seconds
            stopper.wait(max(1, interval))

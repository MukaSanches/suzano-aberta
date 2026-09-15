from __future__ import annotations

import csv
import json
import sqlite3
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import cast

from .models import Change, ChangeType, CollectionReport, PublicRecord
from .parsing import normalize_search


SCHEMA_VERSION = 2
BASE_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    year INTEGER,
    title TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    search_text TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_records_kind ON records(kind);
CREATE INDEX IF NOT EXISTS idx_records_year ON records(year);
CREATE INDEX IF NOT EXISTS idx_records_active ON records(active);
CREATE INDEX IF NOT EXISTS idx_records_last_seen ON records(last_seen);
CREATE TABLE IF NOT EXISTS changes (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    change_type TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    previous_hash TEXT,
    current_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_changes_record_id ON changes(record_id);
CREATE INDEX IF NOT EXISTS idx_changes_observed_at ON changes(observed_at);
CREATE TABLE IF NOT EXISTS collection_runs (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    profile TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    records INTEGER NOT NULL,
    sources_ok INTEGER NOT NULL,
    sources_failed INTEGER NOT NULL,
    new_records INTEGER NOT NULL,
    changed_records INTEGER NOT NULL,
    missing_records INTEGER NOT NULL,
    reactivated_records INTEGER NOT NULL,
    errors_json TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str | Path = "suzano-aberta.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(BASE_SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        columns = {
            str(row["name"])
            for row in self._conn.execute("PRAGMA table_info(records)").fetchall()
        }
        with self._conn:
            if "year" not in columns:
                self._conn.execute("ALTER TABLE records ADD COLUMN year INTEGER")
            if "search_text" not in columns:
                self._conn.execute(
                    "ALTER TABLE records ADD COLUMN search_text TEXT NOT NULL DEFAULT ''"
                )
            self._conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def upsert_many(self, records: Iterable[PublicRecord]) -> list[Change]:
        now = datetime.now(UTC)
        changes: list[Change] = []
        with self._conn:
            for record in records:
                content_hash = record.fingerprint()
                previous = self._conn.execute(
                    "SELECT content_hash, active FROM records WHERE id = ?",
                    (record.id,),
                ).fetchone()
                payload = record.model_dump_json()
                search_text = normalize_search(
                    " ".join(
                        [
                            record.id,
                            record.kind,
                            record.title,
                            record.summary or "",
                            json.dumps(record.attributes, ensure_ascii=False, default=str),
                        ]
                    )
                )
                if previous is None:
                    self._conn.execute(
                        """
                        INSERT INTO records(
                            id, kind, year, title, source_name, source_url,
                            first_seen, last_seen, content_hash, search_text, payload_json, active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                        (
                            record.id,
                            record.kind,
                            record.year,
                            record.title,
                            record.source.name,
                            record.source.url,
                            now.isoformat(),
                            now.isoformat(),
                            content_hash,
                            search_text,
                            payload,
                        ),
                    )
                    changes.append(
                        Change(
                            record_id=record.id,
                            kind=record.kind,
                            change_type="novo",
                            observed_at=now,
                            current_hash=content_hash,
                        )
                    )
                    continue

                previous_hash = str(previous["content_hash"])
                was_active = bool(previous["active"])
                changed = previous_hash != content_hash
                self._conn.execute(
                    """
                    UPDATE records
                    SET kind=?, year=?, title=?, source_name=?, source_url=?, last_seen=?,
                        content_hash=?, search_text=?, payload_json=?, active=1
                    WHERE id=?
                    """,
                    (
                        record.kind,
                        record.year,
                        record.title,
                        record.source.name,
                        record.source.url,
                        now.isoformat(),
                        content_hash,
                        search_text,
                        payload,
                        record.id,
                    ),
                )
                if not was_active:
                    change_type: ChangeType = "reativado"
                elif changed:
                    change_type = "alterado"
                else:
                    continue
                changes.append(
                    Change(
                        record_id=record.id,
                        kind=record.kind,
                        change_type=change_type,
                        observed_at=now,
                        previous_hash=previous_hash,
                        current_hash=content_hash,
                    )
                )

            self._insert_changes(changes)
        return changes

    def mark_missing(
        self,
        *,
        observed_ids: set[str],
        id_prefixes: Sequence[str],
        year: int | None,
    ) -> list[Change]:
        if not id_prefixes:
            return []
        prefix_clause = " OR ".join("id LIKE ?" for _ in id_prefixes)
        params: list[object] = [f"{prefix}%" for prefix in id_prefixes]
        year_clause: str
        if year is None:
            year_clause = "year IS NULL"
        else:
            year_clause = "year = ?"
            params.append(year)
        rows = self._conn.execute(
            f"""
            SELECT id, kind, content_hash FROM records
            WHERE active=1 AND ({prefix_clause}) AND {year_clause}
            """,
            params,
        ).fetchall()
        now = datetime.now(UTC)
        changes: list[Change] = []
        with self._conn:
            for row in rows:
                record_id = str(row["id"])
                if record_id in observed_ids:
                    continue
                self._conn.execute("UPDATE records SET active=0 WHERE id=?", (record_id,))
                changes.append(
                    Change(
                        record_id=record_id,
                        kind=str(row["kind"]),
                        change_type="ausente",
                        observed_at=now,
                        previous_hash=str(row["content_hash"]),
                        current_hash=None,
                    )
                )
            self._insert_changes(changes)
        return changes

    def _insert_changes(self, changes: Iterable[Change]) -> None:
        for change in changes:
            self._conn.execute(
                """
                INSERT INTO changes(
                    record_id, kind, change_type, observed_at, previous_hash, current_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    change.record_id,
                    change.kind,
                    change.change_type,
                    change.observed_at.isoformat(),
                    change.previous_hash,
                    change.current_hash,
                ),
            )

    def save_run(self, *, year: int, profile: str, report: CollectionReport) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO collection_runs(
                    year, profile, started_at, finished_at, records, sources_ok, sources_failed,
                    new_records, changed_records, missing_records, reactivated_records, errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    year,
                    profile,
                    report.started_at.isoformat(),
                    report.finished_at.isoformat(),
                    report.records,
                    report.sources_ok,
                    report.sources_failed,
                    report.new_records,
                    report.changed_records,
                    report.missing_records,
                    report.reactivated_records,
                    json.dumps(report.errors, ensure_ascii=False),
                ),
            )

    def get(self, record_id: str) -> PublicRecord | None:
        row = self._conn.execute(
            "SELECT payload_json FROM records WHERE id=?",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return PublicRecord.model_validate_json(str(row["payload_json"]))

    def search(
        self,
        query: str,
        *,
        limit: int = 50,
        kind: str | None = None,
        year: int | None = None,
        active_only: bool = True,
    ) -> list[PublicRecord]:
        needle = f"%{normalize_search(query)}%"
        clauses = ["search_text LIKE ?"]
        params: list[object] = [needle]
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if year is not None:
            clauses.append("year = ?")
            params.append(year)
        if active_only:
            clauses.append("active = 1")
        params.append(max(1, limit))
        rows = self._conn.execute(
            f"""
            SELECT payload_json FROM records
            WHERE {' AND '.join(clauses)}
            ORDER BY last_seen DESC, id
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [PublicRecord.model_validate_json(str(row["payload_json"])) for row in rows]

    def history(self, record_id: str, *, limit: int = 100) -> list[Change]:
        rows = self._conn.execute(
            "SELECT * FROM changes WHERE record_id=? ORDER BY seq DESC LIMIT ?",
            (record_id, max(1, limit)),
        ).fetchall()
        return [self._row_to_change(row) for row in rows]

    def latest_changes(
        self,
        *,
        limit: int = 50,
        since: datetime | None = None,
    ) -> list[Change]:
        if since is None:
            rows = self._conn.execute(
                "SELECT * FROM changes ORDER BY seq DESC LIMIT ?",
                (max(1, limit),),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM changes WHERE observed_at >= ?
                ORDER BY seq DESC LIMIT ?
                """,
                (since.isoformat(), max(1, limit)),
            ).fetchall()
        return [self._row_to_change(row) for row in rows]

    @staticmethod
    def _row_to_change(row: sqlite3.Row) -> Change:
        return Change(
            record_id=str(row["record_id"]),
            kind=str(row["kind"]),
            change_type=cast(ChangeType, str(row["change_type"])),
            observed_at=datetime.fromisoformat(str(row["observed_at"])),
            previous_hash=str(row["previous_hash"]) if row["previous_hash"] else None,
            current_hash=str(row["current_hash"]) if row["current_hash"] else None,
        )

    def counts_by_kind(self, *, active_only: bool = True) -> dict[str, int]:
        where = "WHERE active=1" if active_only else ""
        rows = self._conn.execute(
            f"SELECT kind, COUNT(*) AS total FROM records {where} GROUP BY kind ORDER BY kind"
        ).fetchall()
        return {str(row["kind"]): int(row["total"]) for row in rows}

    def total_records(self, *, active_only: bool = True) -> int:
        where = "WHERE active=1" if active_only else ""
        row = self._conn.execute(f"SELECT COUNT(*) AS total FROM records {where}").fetchone()
        return int(row["total"]) if row else 0

    def export_json(self, path: str | Path, *, active_only: bool = False) -> int:
        payload = self._export_payload(active_only=active_only)
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return len(payload)

    def export_jsonl(self, path: str | Path, *, active_only: bool = False) -> int:
        payload = self._export_payload(active_only=active_only)
        with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
            for item in payload:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        return len(payload)

    def export_csv(self, path: str | Path, *, active_only: bool = False) -> int:
        payload = self._export_payload(active_only=active_only)
        fields = ["id", "kind", "title", "date", "year", "summary", "source_name", "source_url", "attributes_json"]
        with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for item in payload:
                source = item.get("source") or {}
                writer.writerow(
                    {
                        "id": item.get("id", ""),
                        "kind": item.get("kind", ""),
                        "title": item.get("title", ""),
                        "date": item.get("date", ""),
                        "year": item.get("year", ""),
                        "summary": item.get("summary", ""),
                        "source_name": source.get("name", ""),
                        "source_url": source.get("url", ""),
                        "attributes_json": json.dumps(item.get("attributes") or {}, ensure_ascii=False),
                    }
                )
        return len(payload)

    def _export_payload(self, *, active_only: bool) -> list[dict[str, object]]:
        where = "WHERE active=1" if active_only else ""
        rows = self._conn.execute(
            f"SELECT payload_json FROM records {where} ORDER BY kind, id"
        ).fetchall()
        return [json.loads(str(row["payload_json"])) for row in rows]

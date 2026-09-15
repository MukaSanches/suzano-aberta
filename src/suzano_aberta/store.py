from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Literal, cast

from .models import Change, PublicRecord


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_records_kind ON records(kind);
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
CREATE INDEX IF NOT EXISTS idx_changes_observed_at ON changes(observed_at);
"""


class Store:
    def __init__(self, path: str | Path = "suzano-aberta.sqlite3") -> None:
        self.path = Path(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

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
                    "SELECT content_hash FROM records WHERE id = ?", (record.id,)
                ).fetchone()
                payload = record.model_dump_json()
                if previous is None:
                    self._conn.execute(
                        """
                        INSERT INTO records(
                            id, kind, title, source_name, source_url,
                            first_seen, last_seen, content_hash, payload_json, active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                        (
                            record.id,
                            record.kind,
                            record.title,
                            record.source.name,
                            record.source.url,
                            now.isoformat(),
                            now.isoformat(),
                            content_hash,
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
                changed = previous_hash != content_hash
                self._conn.execute(
                    """
                    UPDATE records
                    SET kind=?, title=?, source_name=?, source_url=?, last_seen=?,
                        content_hash=?, payload_json=?, active=1
                    WHERE id=?
                    """,
                    (
                        record.kind,
                        record.title,
                        record.source.name,
                        record.source.url,
                        now.isoformat(),
                        content_hash,
                        payload,
                        record.id,
                    ),
                )
                if changed:
                    changes.append(
                        Change(
                            record_id=record.id,
                            kind=record.kind,
                            change_type="alterado",
                            observed_at=now,
                            previous_hash=previous_hash,
                            current_hash=content_hash,
                        )
                    )

            for change in changes:
                self._conn.execute(
                    """
                    INSERT INTO changes(record_id, kind, change_type, observed_at, previous_hash, current_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
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
        return changes

    def search(self, query: str, *, limit: int = 50) -> list[PublicRecord]:
        needle = f"%{query.casefold()}%"
        rows = self._conn.execute(
            """
            SELECT payload_json FROM records
            WHERE lower(title) LIKE ? OR lower(payload_json) LIKE ?
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (needle, needle, limit),
        ).fetchall()
        return [PublicRecord.model_validate_json(str(row["payload_json"])) for row in rows]

    def latest_changes(self, *, limit: int = 50) -> list[Change]:
        rows = self._conn.execute(
            "SELECT * FROM changes ORDER BY seq DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            Change(
                record_id=str(row["record_id"]),
                kind=str(row["kind"]),
                change_type=cast(
                    Literal["novo", "alterado", "ausente"],
                    str(row["change_type"]),
                ),
                observed_at=datetime.fromisoformat(str(row["observed_at"])),
                previous_hash=str(row["previous_hash"])
                if row["previous_hash"]
                else None,
                current_hash=str(row["current_hash"])
                if row["current_hash"]
                else None,
            )
            for row in rows
        ]

    def counts_by_kind(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT kind, COUNT(*) AS total FROM records WHERE active=1 GROUP BY kind ORDER BY kind"
        ).fetchall()
        return {str(row["kind"]): int(row["total"]) for row in rows}

    def export_json(self, path: str | Path) -> int:
        rows = self._conn.execute(
            "SELECT payload_json FROM records ORDER BY kind, id"
        ).fetchall()
        payload = [json.loads(str(row["payload_json"])) for row in rows]
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return len(payload)

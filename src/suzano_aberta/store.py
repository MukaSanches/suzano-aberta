from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Literal, cast

from .models import Change, PublicRecord


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=MEMORY;
PRAGMA cache_size=-65536;
PRAGMA mmap_size=268435456;
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
CREATE INDEX IF NOT EXISTS idx_records_source_name ON records(source_name);
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

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
    id UNINDEXED,
    title,
    summary,
    attributes,
    source_name,
    tokenize='unicode61 remove_diacritics 2'
);
"""


def _flatten(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten(item) for item in value)
    return str(value)


def _fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query.casefold(), flags=re.UNICODE)
    return " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens)


class Store:
    def __init__(self, path: str | Path = "suzano-aberta.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._fts_enabled = self._initialize_fts()

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

    @property
    def fts_enabled(self) -> bool:
        return self._fts_enabled

    def _initialize_fts(self) -> bool:
        try:
            self._conn.executescript(FTS_SCHEMA)
        except sqlite3.OperationalError:
            return False

        indexed = int(self._conn.execute("SELECT COUNT(*) FROM records_fts").fetchone()[0])
        total = self.count_records()
        if indexed != total:
            self.rebuild_search_index()
        return True

    def _index_record(self, record: PublicRecord) -> None:
        if not self._fts_enabled:
            return
        self._conn.execute("DELETE FROM records_fts WHERE id = ?", (record.id,))
        self._conn.execute(
            """
            INSERT INTO records_fts(id, title, summary, attributes, source_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.title,
                record.summary or "",
                _flatten(record.attributes),
                record.source.name,
            ),
        )

    def rebuild_search_index(self) -> int:
        try:
            self._conn.executescript(FTS_SCHEMA)
        except sqlite3.OperationalError:
            self._fts_enabled = False
            return 0

        rows = self._conn.execute("SELECT payload_json FROM records WHERE active=1").fetchall()
        with self._conn:
            self._conn.execute("DELETE FROM records_fts")
            for row in rows:
                record = PublicRecord.model_validate_json(str(row["payload_json"]))
                self._conn.execute(
                    """
                    INSERT INTO records_fts(id, title, summary, attributes, source_name)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.title,
                        record.summary or "",
                        _flatten(record.attributes),
                        record.source.name,
                    ),
                )
        self._fts_enabled = True
        return len(rows)

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
                    self._index_record(record)
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
                self._index_record(record)
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

    def get(self, record_id: str) -> PublicRecord | None:
        row = self._conn.execute(
            "SELECT payload_json FROM records WHERE id=? AND active=1", (record_id,)
        ).fetchone()
        if row is None:
            return None
        return PublicRecord.model_validate_json(str(row["payload_json"]))

    def search(self, query: str, *, limit: int = 50) -> list[PublicRecord]:
        clean_query = query.strip()
        if not clean_query:
            return []

        if self._fts_enabled:
            match = _fts_query(clean_query)
            if match:
                try:
                    rows = self._conn.execute(
                        """
                        SELECT records.payload_json
                        FROM records_fts
                        JOIN records ON records.id = records_fts.id
                        WHERE records_fts MATCH ? AND records.active=1
                        ORDER BY bm25(records_fts, 8.0, 4.0, 2.0, 1.0), records.last_seen DESC
                        LIMIT ?
                        """,
                        (match, limit),
                    ).fetchall()
                    if rows:
                        return [
                            PublicRecord.model_validate_json(str(row["payload_json"]))
                            for row in rows
                        ]
                except sqlite3.OperationalError:
                    pass

        needle = f"%{clean_query.casefold()}%"
        rows = self._conn.execute(
            """
            SELECT payload_json FROM records
            WHERE active=1 AND (lower(title) LIKE ? OR lower(payload_json) LIKE ?)
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (needle, needle, limit),
        ).fetchall()
        return [PublicRecord.model_validate_json(str(row["payload_json"])) for row in rows]

    def web_seed_urls(self, *, limit: int = 5000) -> list[str]:
        """Retorna páginas previamente descobertas para o próximo ciclo continuar de onde parou."""
        rows = self._conn.execute(
            """
            SELECT source_url
            FROM records
            WHERE active=1 AND kind='pagina_web' AND source_name LIKE 'Web pública — %'
            ORDER BY last_seen ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [str(row["source_url"]) for row in rows]

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

    def count_records(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS total FROM records WHERE active=1").fetchone()
        return int(row["total"]) if row is not None else 0

    def optimize(self) -> None:
        if self._fts_enabled:
            self._conn.execute("INSERT INTO records_fts(records_fts) VALUES('optimize')")
        self._conn.execute("PRAGMA optimize")

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

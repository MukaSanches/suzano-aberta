from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Literal, cast

from .models import Change, PublicRecord, RecordVersion, TemporalDiff


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
CREATE TABLE IF NOT EXISTS record_versions (
    record_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    observed_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY(record_id, version)
);
CREATE INDEX IF NOT EXISTS idx_record_versions_observed_at ON record_versions(observed_at);
CREATE INDEX IF NOT EXISTS idx_record_versions_record_time ON record_versions(record_id, observed_at DESC);
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


def _change_from_row(row: sqlite3.Row) -> Change:
    return Change(
        record_id=str(row["record_id"]),
        kind=str(row["kind"]),
        change_type=cast(Literal["novo", "alterado", "ausente"], str(row["change_type"])),
        observed_at=datetime.fromisoformat(str(row["observed_at"])),
        previous_hash=str(row["previous_hash"]) if row["previous_hash"] else None,
        current_hash=str(row["current_hash"]) if row["current_hash"] else None,
    )


class Store:
    def __init__(self, path: str | Path = "suzano-aberta.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._backfill_versions()
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

    def _backfill_versions(self) -> None:
        """Migração aditiva: snapshots antigos passam a ter uma versão-base."""
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO record_versions(record_id, version, observed_at, content_hash, payload_json)
                SELECT id, 1, first_seen, content_hash, payload_json
                FROM records
                """
            )

    def _next_version(self, record_id: str) -> int:
        row = self._conn.execute(
            "SELECT MAX(version) FROM record_versions WHERE record_id=?",
            (record_id,),
        ).fetchone()
        return int(row[0] or 0) + 1 if row is not None else 1

    def _append_version(self, record: PublicRecord, *, observed_at: datetime, content_hash: str) -> None:
        self._conn.execute(
            """
            INSERT INTO record_versions(record_id, version, observed_at, content_hash, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.id,
                self._next_version(record.id),
                observed_at.isoformat(),
                content_hash,
                record.model_dump_json(),
            ),
        )

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
                    self._append_version(record, observed_at=now, content_hash=content_hash)
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
                    self._append_version(record, observed_at=now, content_hash=content_hash)
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

    def get_at(self, record_id: str, at: datetime) -> PublicRecord | None:
        moment = at.astimezone(UTC) if at.tzinfo is not None else at.replace(tzinfo=UTC)
        row = self._conn.execute(
            """
            SELECT payload_json FROM record_versions
            WHERE record_id=? AND observed_at<=?
            ORDER BY observed_at DESC, version DESC
            LIMIT 1
            """,
            (record_id, moment.isoformat()),
        ).fetchone()
        if row is None:
            return None
        return PublicRecord.model_validate_json(str(row["payload_json"]))

    def history(self, record_id: str, *, limit: int = 100) -> list[RecordVersion]:
        rows = self._conn.execute(
            """
            SELECT record_id,version,observed_at,content_hash,payload_json
            FROM record_versions
            WHERE record_id=?
            ORDER BY version DESC
            LIMIT ?
            """,
            (record_id, limit),
        ).fetchall()
        return [
            RecordVersion(
                record_id=str(row["record_id"]),
                version=int(row["version"]),
                observed_at=datetime.fromisoformat(str(row["observed_at"])),
                content_hash=str(row["content_hash"]),
                record=PublicRecord.model_validate_json(str(row["payload_json"])),
            )
            for row in rows
        ]

    def diff(self, start: datetime, end: datetime, *, kind: str | None = None, limit: int = 500) -> TemporalDiff:
        start_utc = start.astimezone(UTC) if start.tzinfo is not None else start.replace(tzinfo=UTC)
        end_utc = end.astimezone(UTC) if end.tzinfo is not None else end.replace(tzinfo=UTC)
        if start_utc > end_utc:
            raise ValueError("start não pode ser posterior a end")
        clauses = ["observed_at>?", "observed_at<=?"]
        params: list[object] = [start_utc.isoformat(), end_utc.isoformat()]
        if kind:
            clauses.append("kind=?")
            params.append(kind)
        where = " AND ".join(clauses)
        rows = self._conn.execute(
            f"SELECT * FROM changes WHERE {where} ORDER BY seq DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        items = [_change_from_row(row) for row in rows]
        totals = self._conn.execute(
            f"""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN change_type='novo' THEN 1 ELSE 0 END) AS new_count,
                   SUM(CASE WHEN change_type='alterado' THEN 1 ELSE 0 END) AS changed_count,
                   SUM(CASE WHEN change_type='ausente' THEN 1 ELSE 0 END) AS absent_count
            FROM changes WHERE {where}
            """,
            params,
        ).fetchone()
        return TemporalDiff(
            from_time=start_utc,
            to_time=end_utc,
            total=int(totals["total"] or 0) if totals else 0,
            new=int(totals["new_count"] or 0) if totals else 0,
            changed=int(totals["changed_count"] or 0) if totals else 0,
            absent=int(totals["absent_count"] or 0) if totals else 0,
            items=items,
        )

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
        return [_change_from_row(row) for row in rows]

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

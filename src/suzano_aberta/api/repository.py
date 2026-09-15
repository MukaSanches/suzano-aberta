from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from ..models import Change, PublicRecord, RecordKind


def _fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query.casefold(), flags=re.UNICODE)
    return " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens)


class ApiRepository:
    """Camada de leitura da API. Nunca cria, altera ou reindexa o acervo."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        uri = f"file:{self.path.resolve().as_posix()}?mode=ro"
        self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA query_only=ON")
        self._fts_enabled = self._table_exists("records_fts")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ApiRepository":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def fts_enabled(self) -> bool:
        return self._fts_enabled

    def _table_exists(self, name: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
            (name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _filters(
        *,
        kind: RecordKind | None,
        year: int | None,
        source: str | None,
        prefix: str = "records",
    ) -> tuple[list[str], list[object]]:
        clauses = [f"{prefix}.active=1"]
        params: list[object] = []
        if kind is not None:
            clauses.append(f"{prefix}.kind=?")
            params.append(kind)
        if year is not None:
            clauses.append(f"CAST(json_extract({prefix}.payload_json, '$.year') AS INTEGER)=?")
            params.append(year)
        if source:
            clauses.append(f"lower({prefix}.source_name) LIKE ?")
            params.append(f"%{source.casefold()}%")
        return clauses, params

    @staticmethod
    def _decode(rows: list[sqlite3.Row]) -> list[PublicRecord]:
        return [PublicRecord.model_validate_json(str(row["payload_json"])) for row in rows]

    def get(self, record_id: str) -> PublicRecord | None:
        row = self._conn.execute(
            "SELECT payload_json FROM records WHERE id=? AND active=1",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return PublicRecord.model_validate_json(str(row["payload_json"]))

    def list_records(
        self,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PublicRecord], int]:
        clauses, params = self._filters(kind=kind, year=year, source=source)
        where = " AND ".join(clauses)
        total = int(
            self._conn.execute(
                f"SELECT COUNT(*) FROM records WHERE {where}",
                params,
            ).fetchone()[0]
        )
        rows = self._conn.execute(
            f"""
            SELECT payload_json FROM records
            WHERE {where}
            ORDER BY last_seen DESC, id ASC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        return self._decode(rows), total

    def search(
        self,
        query: str,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PublicRecord], int]:
        clean_query = query.strip()
        if not clean_query:
            return [], 0
        clauses, params = self._filters(kind=kind, year=year, source=source)
        where = " AND ".join(clauses)
        match = _fts_query(clean_query)

        if self._fts_enabled and match:
            try:
                total = int(
                    self._conn.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM records_fts
                        JOIN records ON records.id = records_fts.id
                        WHERE records_fts MATCH ? AND {where}
                        """,
                        [match, *params],
                    ).fetchone()[0]
                )
                if total:
                    rows = self._conn.execute(
                        f"""
                        SELECT records.payload_json
                        FROM records_fts
                        JOIN records ON records.id = records_fts.id
                        WHERE records_fts MATCH ? AND {where}
                        ORDER BY bm25(records_fts, 8.0, 4.0, 2.0, 1.0), records.last_seen DESC
                        LIMIT ? OFFSET ?
                        """,
                        [match, *params, limit, offset],
                    ).fetchall()
                    return self._decode(rows), total
            except sqlite3.OperationalError:
                pass

        like_clauses = [
            *clauses,
            "(lower(records.title) LIKE ? OR lower(records.payload_json) LIKE ?)",
        ]
        needle = f"%{clean_query.casefold()}%"
        like_params = [*params, needle, needle]
        like_where = " AND ".join(like_clauses)
        total = int(
            self._conn.execute(
                f"SELECT COUNT(*) FROM records WHERE {like_where}",
                like_params,
            ).fetchone()[0]
        )
        rows = self._conn.execute(
            f"""
            SELECT payload_json FROM records
            WHERE {like_where}
            ORDER BY last_seen DESC, id ASC
            LIMIT ? OFFSET ?
            """,
            [*like_params, limit, offset],
        ).fetchall()
        return self._decode(rows), total

    def counts_by_kind(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT kind, COUNT(*) AS total FROM records WHERE active=1 GROUP BY kind ORDER BY kind"
        ).fetchall()
        return {str(row["kind"]): int(row["total"]) for row in rows}

    def source_counts(self, *, limit: int = 50) -> list[tuple[str, int]]:
        rows = self._conn.execute(
            """
            SELECT source_name, COUNT(*) AS total
            FROM records
            WHERE active=1
            GROUP BY source_name
            ORDER BY total DESC, source_name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [(str(row["source_name"]), int(row["total"])) for row in rows]

    def stats(self) -> dict[str, object]:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS total, MIN(first_seen) AS first_seen, MAX(last_seen) AS last_seen
            FROM records WHERE active=1
            """
        ).fetchone()
        return {
            "records": int(row["total"]) if row else 0,
            "first_seen": str(row["first_seen"]) if row and row["first_seen"] else None,
            "last_seen": str(row["last_seen"]) if row and row["last_seen"] else None,
            "fts_enabled": self._fts_enabled,
            "database_bytes": self.path.stat().st_size,
            "sqlite_version": sqlite3.sqlite_version,
        }

    def changes(
        self,
        *,
        kind: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Change], int]:
        clauses: list[str] = []
        params: list[object] = []
        if kind:
            clauses.append("kind=?")
            params.append(kind)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        total = int(
            self._conn.execute(
                f"SELECT COUNT(*) FROM changes {where}",
                params,
            ).fetchone()[0]
        )
        rows = self._conn.execute(
            f"""
            SELECT * FROM changes {where}
            ORDER BY seq DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        items = [
            Change(
                record_id=str(row["record_id"]),
                kind=str(row["kind"]),
                change_type=cast(
                    Literal["novo", "alterado", "ausente"],
                    str(row["change_type"]),
                ),
                observed_at=datetime.fromisoformat(str(row["observed_at"])),
                previous_hash=str(row["previous_hash"]) if row["previous_hash"] else None,
                current_hash=str(row["current_hash"]) if row["current_hash"] else None,
            )
            for row in rows
        ]
        return items, total

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast

from ..models import Change, PublicRecord, RecordKind

SortMode = Literal["date_desc", "date_asc", "relevance"]
DateMode = Literal["effective", "record", "observed"]

DOCUMENT_KINDS: tuple[RecordKind, ...] = (
    "arquivo",
    "arquivo_historico",
    "diario",
    "documento_fiscal",
    "documento_orcamentario",
    "lei",
    "decreto",
)
LEGISLATION_KINDS: tuple[RecordKind, ...] = ("lei", "decreto", "proposicao")
PROCUREMENT_KINDS: tuple[RecordKind, ...] = ("licitacao", "contrato", "ata")


def _fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query.casefold(), flags=re.UNICODE)
    return " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens)


class ApiRepository:
    """Camada de leitura da API.

    A conexão abre o snapshot SQLite em modo somente leitura e trata o arquivo
    publicado como imutável durante a vida daquela conexão. Cada requisição abre
    sua própria conexão, então uma troca atômica do snapshot passa a valer nas
    requisições seguintes sem permitir mutação acidental pela API.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        uri = f"file:{self.path.resolve().as_posix()}?mode=ro&immutable=1"
        self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA query_only=ON")
        self._conn.execute("PRAGMA trusted_schema=OFF")
        self._conn.execute("PRAGMA busy_timeout=1000")
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
    def _record_date_expr(prefix: str = "records") -> str:
        payload = f"{prefix}.payload_json"
        sessions = f"json_extract({payload}, '$.attributes.sessions')"
        session_min = (
            "(SELECT MIN(json_extract(session.value, '$.session_date')) "
            f"FROM json_each({sessions}) AS session "
            "WHERE json_extract(session.value, '$.session_date') IS NOT NULL)"
        )
        raw = f"COALESCE(json_extract({payload}, '$.date'), {session_min})"
        year = f"CAST(json_extract({payload}, '$.year') AS INTEGER)"
        return (
            "CASE "
            f"WHEN {raw} GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*' "
            f"THEN substr({raw},1,10) "
            f"WHEN length({raw})>=10 AND substr({raw},3,1)='/' AND substr({raw},6,1)='/' "
            f"THEN substr({raw},7,4)||'-'||substr({raw},4,2)||'-'||substr({raw},1,2) "
            f"WHEN {year} BETWEEN 1800 AND 2200 THEN printf('%04d-01-01',{year}) "
            "ELSE NULL END"
        )

    @classmethod
    def _date_expr(cls, mode: DateMode, prefix: str = "records") -> str:
        observed = f"substr({prefix}.last_seen,1,10)"
        if mode == "observed":
            return observed
        record = cls._record_date_expr(prefix)
        if mode == "record":
            return record
        return f"COALESCE(({record}), {observed})"

    @classmethod
    def _filters(
        cls,
        *,
        kind: RecordKind | None,
        kinds: tuple[RecordKind, ...] | None,
        year: int | None,
        source: str | None,
        date_from: str | None,
        date_to: str | None,
        date_mode: DateMode,
        prefix: str = "records",
    ) -> tuple[list[str], list[object]]:
        clauses = [f"{prefix}.active=1"]
        params: list[object] = []
        if kind is not None:
            clauses.append(f"{prefix}.kind=?")
            params.append(kind)
        elif kinds:
            placeholders = ",".join("?" for _ in kinds)
            clauses.append(f"{prefix}.kind IN ({placeholders})")
            params.extend(kinds)
        if year is not None:
            clauses.append(f"CAST(json_extract({prefix}.payload_json, '$.year') AS INTEGER)=?")
            params.append(year)
        if source:
            clauses.append(f"lower({prefix}.source_name) LIKE ?")
            params.append(f"%{source.casefold()}%")
        date_expr = cls._date_expr(date_mode, prefix)
        if date_from:
            clauses.append(f"{date_expr}>=?")
            params.append(date_from)
        if date_to:
            clauses.append(f"{date_expr}<=?")
            params.append(date_to)
        return clauses, params

    @classmethod
    def _order_by(cls, sort: SortMode, *, date_mode: DateMode, with_rank: bool) -> str:
        date_expr = cls._date_expr(date_mode)
        if sort == "date_asc":
            return f"{date_expr} ASC, records.id ASC"
        if sort == "relevance" and with_rank:
            return f"bm25(records_fts, 8.0, 4.0, 2.0, 1.0), {date_expr} DESC, records.id ASC"
        return f"{date_expr} DESC, records.id ASC"

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

    def record_storage_metadata(self, record_id: str) -> dict[str, str] | None:
        row = self._conn.execute(
            "SELECT first_seen,last_seen,content_hash FROM records WHERE id=? AND active=1",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "first_seen": str(row["first_seen"]),
            "last_seen": str(row["last_seen"]),
            "content_hash": str(row["content_hash"]),
        }

    def list_records(
        self,
        *,
        kind: RecordKind | None = None,
        kinds: tuple[RecordKind, ...] | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PublicRecord], int]:
        clauses, params = self._filters(
            kind=kind,
            kinds=kinds,
            year=year,
            source=source,
            date_from=date_from,
            date_to=date_to,
            date_mode=date_mode,
        )
        where = " AND ".join(clauses)
        total = int(self._conn.execute(f"SELECT COUNT(*) FROM records WHERE {where}", params).fetchone()[0])
        order_by = self._order_by(sort, date_mode=date_mode, with_rank=False)
        rows = self._conn.execute(
            f"SELECT records.payload_json FROM records WHERE {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return self._decode(rows), total

    def search(
        self,
        query: str,
        *,
        kind: RecordKind | None = None,
        kinds: tuple[RecordKind, ...] | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PublicRecord], int]:
        clean_query = query.strip()
        if not clean_query:
            return self.list_records(
                kind=kind,
                kinds=kinds,
                year=year,
                source=source,
                date_from=date_from,
                date_to=date_to,
                date_mode=date_mode,
                sort=sort,
                limit=limit,
                offset=offset,
            )
        clauses, params = self._filters(
            kind=kind,
            kinds=kinds,
            year=year,
            source=source,
            date_from=date_from,
            date_to=date_to,
            date_mode=date_mode,
        )
        where = " AND ".join(clauses)
        match = _fts_query(clean_query)

        if self._fts_enabled and match:
            try:
                total = int(
                    self._conn.execute(
                        f"SELECT COUNT(*) FROM records_fts JOIN records ON records.id=records_fts.id WHERE records_fts MATCH ? AND {where}",
                        [match, *params],
                    ).fetchone()[0]
                )
                if total:
                    order_by = self._order_by(sort, date_mode=date_mode, with_rank=True)
                    rows = self._conn.execute(
                        f"SELECT records.payload_json FROM records_fts JOIN records ON records.id=records_fts.id WHERE records_fts MATCH ? AND {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
                        [match, *params, limit, offset],
                    ).fetchall()
                    return self._decode(rows), total
            except sqlite3.OperationalError:
                pass

        like_clauses = [*clauses, "(lower(records.title) LIKE ? OR lower(records.payload_json) LIKE ?)"]
        needle = f"%{clean_query.casefold()}%"
        like_params = [*params, needle, needle]
        like_where = " AND ".join(like_clauses)
        total = int(self._conn.execute(f"SELECT COUNT(*) FROM records WHERE {like_where}", like_params).fetchone()[0])
        order_by = self._order_by(sort, date_mode=date_mode, with_rank=False)
        rows = self._conn.execute(
            f"SELECT records.payload_json FROM records WHERE {like_where} ORDER BY {order_by} LIMIT ? OFFSET ?",
            [*like_params, limit, offset],
        ).fetchall()
        return self._decode(rows), total

    def documents(
        self,
        query: str = "",
        *,
        year: int | None = None,
        source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PublicRecord], int]:
        return self.search(
            query,
            kinds=DOCUMENT_KINDS,
            year=year,
            source=source,
            date_from=date_from,
            date_to=date_to,
            date_mode=date_mode,
            sort=sort,
            limit=limit,
            offset=offset,
        )

    def legislation(
        self,
        query: str = "",
        *,
        year: int | None = None,
        source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PublicRecord], int]:
        return self.search(
            query,
            kinds=LEGISLATION_KINDS,
            year=year,
            source=source,
            date_from=date_from,
            date_to=date_to,
            date_mode=date_mode,
            sort=sort,
            limit=limit,
            offset=offset,
        )

    def procurements(
        self,
        query: str = "",
        *,
        year: int | None = None,
        source: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PublicRecord], int]:
        return self.search(
            query,
            kinds=PROCUREMENT_KINDS,
            year=year,
            source=source,
            date_from=date_from,
            date_to=date_to,
            date_mode=date_mode,
            sort=sort,
            limit=limit,
            offset=offset,
        )

    def counts_by_kind(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT kind, COUNT(*) AS total FROM records WHERE active=1 GROUP BY kind ORDER BY kind"
        ).fetchall()
        return {str(row["kind"]): int(row["total"]) for row in rows}

    def count_kinds(self, kinds: tuple[RecordKind, ...]) -> int:
        placeholders = ",".join("?" for _ in kinds)
        row = self._conn.execute(
            f"SELECT COUNT(*) FROM records WHERE active=1 AND kind IN ({placeholders})",
            kinds,
        ).fetchone()
        return int(row[0]) if row else 0

    def source_counts(self, *, limit: int = 50) -> list[tuple[str, int]]:
        rows = self._conn.execute(
            "SELECT source_name, COUNT(*) AS total FROM records WHERE active=1 GROUP BY source_name ORDER BY total DESC, source_name ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [(str(row["source_name"]), int(row["total"])) for row in rows]

    def source_catalog(self, *, limit: int = 200) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT source_name, COUNT(*) AS total,
                   MIN(first_seen) AS first_seen, MAX(last_seen) AS last_seen
            FROM records
            WHERE active=1
            GROUP BY source_name
            ORDER BY total DESC, source_name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "name": str(row["source_name"]),
                "records": int(row["total"]),
                "first_seen": str(row["first_seen"]) if row["first_seen"] else None,
                "last_seen": str(row["last_seen"]) if row["last_seen"] else None,
            }
            for row in rows
        ]

    def stats(self) -> dict[str, object]:
        row = self._conn.execute(
            "SELECT COUNT(*) AS total, MIN(first_seen) AS first_seen, MAX(last_seen) AS last_seen FROM records WHERE active=1"
        ).fetchone()
        return {
            "records": int(row["total"]) if row else 0,
            "documents": self.count_kinds(DOCUMENT_KINDS),
            "legislation": self.count_kinds(LEGISLATION_KINDS),
            "procurements": self.count_kinds(PROCUREMENT_KINDS),
            "first_seen": str(row["first_seen"]) if row and row["first_seen"] else None,
            "last_seen": str(row["last_seen"]) if row and row["last_seen"] else None,
            "fts_enabled": self._fts_enabled,
            "database_bytes": self.path.stat().st_size,
            "sqlite_version": sqlite3.sqlite_version,
        }

    def dataset_version(self) -> str:
        stats = self.stats()
        raw = "|".join(
            [
                str(stats.get("records", 0)),
                str(stats.get("documents", 0)),
                str(stats.get("legislation", 0)),
                str(stats.get("procurements", 0)),
                str(stats.get("last_seen") or ""),
                str(stats.get("database_bytes", 0)),
            ]
        )
        return sha256(raw.encode("utf-8")).hexdigest()[:24]

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
        total = int(self._conn.execute(f"SELECT COUNT(*) FROM changes {where}", params).fetchone()[0])
        rows = self._conn.execute(
            f"SELECT * FROM changes {where} ORDER BY seq DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        items = [
            Change(
                record_id=str(row["record_id"]),
                kind=str(row["kind"]),
                change_type=cast(Literal["novo", "alterado", "ausente"], str(row["change_type"])),
                observed_at=datetime.fromisoformat(str(row["observed_at"])),
                previous_hash=str(row["previous_hash"]) if row["previous_hash"] else None,
                current_hash=str(row["current_hash"]) if row["current_hash"] else None,
            )
            for row in rows
        ]
        return items, total

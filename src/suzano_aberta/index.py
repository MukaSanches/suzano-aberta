from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from types import TracebackType
from typing import Literal, cast

from pydantic import BaseModel, Field

from .api.repository import ApiRepository
from .models import Change, PublicRecord, RecordKind

SortMode = Literal["date_desc", "date_asc", "relevance"]
DateMode = Literal["effective", "record", "observed"]


class LocalPage(BaseModel):
    """Página de resultados da consulta local."""

    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    next_offset: int | None = Field(default=None, ge=0)
    previous_offset: int | None = Field(default=None, ge=0)
    items: list[PublicRecord]

    @property
    def has_more(self) -> bool:
        return self.next_offset is not None


class LocalStats(BaseModel):
    records: int = Field(ge=0)
    documents: int = Field(ge=0)
    legislation: int = Field(ge=0)
    procurements: int = Field(ge=0)
    first_seen: str | None = None
    last_seen: str | None = None
    fts_enabled: bool
    database_bytes: int = Field(ge=0)
    sqlite_version: str
    dataset_version: str
    kinds: dict[str, int]


def _date_value(value: date | str | None) -> str | None:
    return value.isoformat() if isinstance(value, date) else value


def _page(items: list[PublicRecord], total: int, *, limit: int, offset: int) -> LocalPage:
    next_offset = offset + limit if offset + limit < total else None
    previous_offset = max(0, offset - limit) if offset > 0 else None
    return LocalPage(
        total=total,
        limit=limit,
        offset=offset,
        next_offset=next_offset,
        previous_offset=previous_offset,
        items=items,
    )


class SuzanoIndex:
    """Fachada tipada e somente leitura para consultar um snapshot local.

    Use esta classe quando o aplicativo já possui o arquivo SQLite e não precisa
    subir a API HTTP. Ela compartilha a mesma camada de consulta da API pública,
    mantendo filtros, ordenação e semântica de busca consistentes entre os dois
    modos de consumo.
    """

    def __init__(self, database: str | Path = "suzano-aberta.sqlite3") -> None:
        self.database = Path(database)
        self._repository = ApiRepository(self.database)

    def close(self) -> None:
        self._repository.close()

    def __enter__(self) -> SuzanoIndex:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def record(self, record_id: str) -> PublicRecord | None:
        return self._repository.get(record_id)

    def records(
        self,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> LocalPage:
        items, total = self._repository.list_records(
            kind=kind,
            year=year,
            source=source,
            date_from=_date_value(date_from),
            date_to=_date_value(date_to),
            date_mode=date_mode,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        return _page(items, total, limit=limit, offset=offset)

    def search(
        self,
        query: str,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> LocalPage:
        items, total = self._repository.search(
            query,
            kind=kind,
            year=year,
            source=source,
            date_from=_date_value(date_from),
            date_to=_date_value(date_to),
            date_mode=date_mode,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        return _page(items, total, limit=limit, offset=offset)

    def documents(
        self,
        query: str = "",
        *,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> LocalPage:
        items, total = self._repository.documents(
            query,
            year=year,
            source=source,
            date_from=_date_value(date_from),
            date_to=_date_value(date_to),
            date_mode=date_mode,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        return _page(items, total, limit=limit, offset=offset)

    def legislation(
        self,
        query: str = "",
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> LocalPage:
        if kind is not None and kind not in {"lei", "decreto", "proposicao"}:
            raise ValueError("kind deve ser lei, decreto ou proposicao.")
        if kind is None:
            items, total = self._repository.legislation(
                query,
                year=year,
                date_from=_date_value(date_from),
                date_to=_date_value(date_to),
                date_mode=date_mode,
                sort=sort,
                limit=limit,
                offset=offset,
            )
        else:
            items, total = self._repository.search(
                query,
                kind=kind,
                year=year,
                date_from=_date_value(date_from),
                date_to=_date_value(date_to),
                date_mode=date_mode,
                sort=sort,
                limit=limit,
                offset=offset,
            )
        return _page(items, total, limit=limit, offset=offset)

    def procurements(
        self,
        query: str = "",
        *,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> LocalPage:
        items, total = self._repository.procurements(
            query,
            year=year,
            source=source,
            date_from=_date_value(date_from),
            date_to=_date_value(date_to),
            date_mode=date_mode,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        return _page(items, total, limit=limit, offset=offset)

    def changes(
        self,
        *,
        kind: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Change], int]:
        return self._repository.changes(kind=kind, limit=limit, offset=offset)

    def stats(self) -> LocalStats:
        raw = self._repository.stats()
        first_seen = raw["first_seen"]
        last_seen = raw["last_seen"]
        return LocalStats(
            records=cast(int, raw["records"]),
            documents=cast(int, raw["documents"]),
            legislation=cast(int, raw["legislation"]),
            procurements=cast(int, raw["procurements"]),
            first_seen=first_seen if isinstance(first_seen, str) else None,
            last_seen=last_seen if isinstance(last_seen, str) else None,
            fts_enabled=cast(bool, raw["fts_enabled"]),
            database_bytes=cast(int, raw["database_bytes"]),
            sqlite_version=str(raw["sqlite_version"]),
            dataset_version=self._repository.dataset_version(),
            kinds=self._repository.counts_by_kind(),
        )

    def iter_records(
        self,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        page_size: int = 100,
        max_items: int | None = None,
    ) -> Iterator[PublicRecord]:
        offset = 0
        emitted = 0
        while True:
            page = self.records(
                kind=kind,
                year=year,
                source=source,
                date_from=date_from,
                date_to=date_to,
                date_mode=date_mode,
                sort=sort,
                limit=page_size,
                offset=offset,
            )
            for item in page.items:
                if max_items is not None and emitted >= max_items:
                    return
                yield item
                emitted += 1
            if page.next_offset is None:
                return
            offset = page.next_offset

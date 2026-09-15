from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Literal

from .catalog import SOURCES
from .http import PoliteHttpClient
from .models import Change, CollectionReport, PublicRecord, SourceStatus
from .sources import CamaraSource, PrefeituraSource
from .store import Store


Profile = Literal["completo", "legislativo", "executivo"]
Collector = tuple[str, Callable[[], list[PublicRecord]]]


class Suzano:
    """Fachada principal da biblioteca."""

    def __init__(
        self,
        *,
        database: str | Path = "suzano-aberta.sqlite3",
        timeout: float = 20.0,
        min_interval: float = 0.15,
    ) -> None:
        self.database = Path(database)
        self.http = PoliteHttpClient(timeout=timeout, min_interval=min_interval)
        self.camara = CamaraSource(self.http)
        self.prefeitura = PrefeituraSource(self.http)

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> Suzano:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def collect(self, *, year: int, profile: Profile = "completo") -> CollectionReport:
        """Executa coletores independentes e preserva tudo que concluir com sucesso."""
        started = datetime.now(UTC)
        records: list[PublicRecord] = []
        errors: list[str] = []
        collectors: list[Collector] = []
        sessions_cache: list[PublicRecord] | None = None

        def sessions() -> list[PublicRecord]:
            nonlocal sessions_cache
            if sessions_cache is None:
                sessions_cache = self.camara.sessions(year=year)
            return sessions_cache

        def propositions() -> list[PublicRecord]:
            return self.camara.propositions(year=year, sessions=sessions())

        if profile in {"completo", "legislativo"}:
            collectors.extend(
                [
                    ("Câmara / vereadores", self.camara.councilors),
                    ("Câmara / sessões", sessions),
                    ("Câmara / proposições", propositions),
                    ("Câmara / contratos", lambda: self.camara.contracts(year=year)),
                    ("Câmara / comissões", self.camara.committees),
                    ("Câmara / presenças", lambda: self.camara.attendance(year=year)),
                    ("Câmara / diário oficial", lambda: self.camara.diary(year=year, limit=250)),
                ]
            )
        if profile in {"completo", "executivo"}:
            collectors.extend(
                [
                    ("Prefeitura / licitações", lambda: self.prefeitura.tenders(year=year)),
                    ("Prefeitura / secretarias", self.prefeitura.secretariats),
                    ("Prefeitura / contas públicas", lambda: self.prefeitura.fiscal_documents(year=year, limit=400)),
                    ("Prefeitura / orçamento", lambda: self.prefeitura.budget_documents(year=year, limit=250)),
                    ("Prefeitura / imprensa oficial", lambda: self.prefeitura.official_gazette(year=year, limit=300)),
                    ("Prefeitura / leis e decretos", lambda: self.prefeitura.legal_acts(year=year, limit=300)),
                    ("Prefeitura / notícias", lambda: self.prefeitura.news(year=year, limit=100)),
                ]
            )

        ok = 0
        failed = 0
        for label, collector in collectors:
            try:
                records.extend(collector())
                ok += 1
            except Exception as exc:
                failed += 1
                errors.append(f"{label}: {type(exc).__name__}: {exc}")

        unique = {record.id: record for record in records}
        with Store(self.database) as store:
            changes = store.upsert_many(unique.values())

        finished = datetime.now(UTC)
        return CollectionReport(
            started_at=started,
            finished_at=finished,
            records=len(unique),
            sources_ok=ok,
            sources_failed=failed,
            new_records=sum(change.change_type == "novo" for change in changes),
            changed_records=sum(change.change_type == "alterado" for change in changes),
            errors=errors,
        )

    def search(self, query: str, *, limit: int = 50) -> list[PublicRecord]:
        with Store(self.database) as store:
            return store.search(query, limit=limit)

    def snapshot(self) -> dict[str, int]:
        with Store(self.database) as store:
            return store.counts_by_kind()

    def changes(self, *, limit: int = 50) -> list[Change]:
        with Store(self.database) as store:
            return store.latest_changes(limit=limit)

    def doctor(self) -> list[SourceStatus]:
        statuses: list[SourceStatus] = []
        for source in SOURCES:
            ok, status_code, elapsed_ms, detail = self.http.head_or_get(source.url)
            statuses.append(
                SourceStatus(
                    source=source.name,
                    url=source.url,
                    ok=ok,
                    status_code=status_code,
                    elapsed_ms=elapsed_ms,
                    detail=detail,
                )
            )
        return statuses


def explain(record: PublicRecord) -> str:
    lines = [record.title]
    if record.summary:
        lines.extend(["", record.summary])
    if record.date:
        lines.extend(["", f"Data: {record.date}"])
    if record.attributes:
        lines.append("")
        for key, value in record.attributes.items():
            if value in (None, "", [], {}):
                continue
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
    lines.extend(["", f"Fonte: {record.source.name}", record.source.url])
    return "\n".join(lines)

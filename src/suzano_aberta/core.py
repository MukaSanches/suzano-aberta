from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class CollectorSpec:
    label: str
    id_prefixes: tuple[str, ...]
    year_scoped: bool
    collect: Callable[[], list[PublicRecord]]


class Suzano:
    """Fachada principal da biblioteca Suzano Aberta."""

    def __init__(
        self,
        *,
        database: str | Path = "suzano-aberta.sqlite3",
        timeout: float = 20.0,
        min_interval: float = 0.20,
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
        """Coleta cada fonte isoladamente e só invalida dados de fontes concluídas."""
        if year < 2000 or year > datetime.now().year + 1:
            raise ValueError("Ano de referência fora do intervalo esperado")

        started = datetime.now(UTC)
        errors: list[str] = []
        all_records: dict[str, PublicRecord] = {}
        all_changes: list[Change] = []
        sources_ok = 0
        sources_failed = 0
        sessions_cache: list[PublicRecord] | None = None

        def sessions() -> list[PublicRecord]:
            nonlocal sessions_cache
            if sessions_cache is None:
                sessions_cache = self.camara.sessions(year=year)
            return sessions_cache

        collectors: list[CollectorSpec] = []
        if profile in {"completo", "legislativo"}:
            collectors.extend(
                [
                    CollectorSpec("Câmara / vereadores", ("camara:vereador:",), False, self.camara.councilors),
                    CollectorSpec("Câmara / sessões", ("camara:sessao:",), True, sessions),
                    CollectorSpec(
                        "Câmara / proposições",
                        ("camara:proposicao:",),
                        True,
                        lambda: self.camara.propositions(year=year, sessions=sessions()),
                    ),
                    CollectorSpec(
                        "Câmara / contratos",
                        ("camara:contrato:",),
                        True,
                        lambda: self.camara.contracts(year=year),
                    ),
                    CollectorSpec(
                        "Câmara / licitações e dispensas",
                        ("camara:licitacao:",),
                        True,
                        lambda: self.camara.procurements(year=year),
                    ),
                    CollectorSpec(
                        "Câmara / atas de registro de preços",
                        ("camara:ata-preco:",),
                        True,
                        lambda: self.camara.price_registries(year=year),
                    ),
                    CollectorSpec(
                        "Câmara / comissões",
                        ("camara:comissao:",),
                        True,
                        lambda: self.camara.committees(year=year),
                    ),
                    CollectorSpec(
                        "Câmara / presenças",
                        ("camara:presenca:",),
                        True,
                        lambda: self.camara.attendance(year=year),
                    ),
                    CollectorSpec(
                        "Câmara / diário oficial",
                        ("camara:diario:",),
                        True,
                        lambda: self.camara.diary(year=year),
                    ),
                ]
            )

        if profile in {"completo", "executivo"}:
            collectors.extend(
                [
                    CollectorSpec(
                        "Prefeitura / licitações",
                        ("prefeitura:licitacao:",),
                        True,
                        lambda: self.prefeitura.tenders(year=year),
                    ),
                    CollectorSpec(
                        "Prefeitura / secretarias",
                        ("prefeitura:secretaria:",),
                        False,
                        self.prefeitura.secretariats,
                    ),
                    CollectorSpec(
                        "Prefeitura / contas públicas",
                        ("prefeitura:fiscal:",),
                        True,
                        lambda: self.prefeitura.fiscal_documents(year=year),
                    ),
                    CollectorSpec(
                        "Prefeitura / orçamento",
                        ("prefeitura:orcamento:",),
                        True,
                        lambda: self.prefeitura.budget_documents(year=year),
                    ),
                    CollectorSpec(
                        "Prefeitura / imprensa oficial",
                        ("prefeitura:diario:",),
                        True,
                        lambda: self.prefeitura.official_gazette(year=year),
                    ),
                    CollectorSpec(
                        "Prefeitura / leis e decretos",
                        ("prefeitura:ato:",),
                        True,
                        lambda: self.prefeitura.legal_acts(year=year),
                    ),
                    CollectorSpec(
                        "Prefeitura / concursos públicos",
                        ("prefeitura:concurso:",),
                        True,
                        lambda: self.prefeitura.contests(year=year),
                    ),
                    CollectorSpec(
                        "Prefeitura / transferências especiais",
                        ("prefeitura:transferencia:",),
                        True,
                        lambda: self.prefeitura.special_transfers(year=year),
                    ),
                    CollectorSpec(
                        "Prefeitura / parcerias e convênios",
                        ("prefeitura:parceria:",),
                        True,
                        lambda: self.prefeitura.partnerships(year=year),
                    ),
                    CollectorSpec(
                        "Prefeitura / notícias",
                        ("prefeitura:noticia:",),
                        True,
                        lambda: self.prefeitura.news(year=year),
                    ),
                ]
            )

        with Store(self.database) as store:
            for spec in collectors:
                try:
                    batch = spec.collect()
                    unique_batch = {record.id: record for record in batch}
                    batch_changes = store.upsert_many(unique_batch.values())
                    missing_changes = store.mark_missing(
                        observed_ids=set(unique_batch),
                        id_prefixes=spec.id_prefixes,
                        year=year if spec.year_scoped else None,
                    )
                    all_changes.extend(batch_changes)
                    all_changes.extend(missing_changes)
                    all_records.update(unique_batch)
                    sources_ok += 1
                except Exception as exc:
                    sources_failed += 1
                    errors.append(f"{spec.label}: {type(exc).__name__}: {exc}")

            finished = datetime.now(UTC)
            report = CollectionReport(
                started_at=started,
                finished_at=finished,
                records=len(all_records),
                sources_ok=sources_ok,
                sources_failed=sources_failed,
                new_records=sum(change.change_type == "novo" for change in all_changes),
                changed_records=sum(change.change_type == "alterado" for change in all_changes),
                missing_records=sum(change.change_type == "ausente" for change in all_changes),
                reactivated_records=sum(change.change_type == "reativado" for change in all_changes),
                errors=errors,
            )
            store.save_run(year=year, profile=profile, report=report)
        return report

    def search(
        self,
        query: str,
        *,
        limit: int = 50,
        kind: str | None = None,
        year: int | None = None,
    ) -> list[PublicRecord]:
        with Store(self.database) as store:
            return store.search(query, limit=limit, kind=kind, year=year)

    def get(self, record_id: str) -> PublicRecord | None:
        with Store(self.database) as store:
            return store.get(record_id)

    def history(self, record_id: str, *, limit: int = 100) -> list[Change]:
        with Store(self.database) as store:
            return store.history(record_id, limit=limit)

    def snapshot(self) -> dict[str, int]:
        with Store(self.database) as store:
            return store.counts_by_kind()

    def changes(self, *, limit: int = 50, since: datetime | None = None) -> list[Change]:
        with Store(self.database) as store:
            return store.latest_changes(limit=limit, since=since)

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
    if record.source.observed_on:
        lines.append(f"Observado em: {record.source.observed_on}")
    if record.source.content_sha256:
        lines.append(f"SHA-256 da resposta observada: {record.source.content_sha256}")
    lines.append(f"Coletado em UTC: {record.source.collected_at.isoformat()}")
    return "\n".join(lines)

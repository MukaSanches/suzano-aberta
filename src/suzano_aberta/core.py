from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Literal

from .catalog import SOURCES
from .discovery import WebDiscovery
from .http import PoliteHttpClient
from .integrity import check_transparency_integrity
from .models import (
    Change,
    CollectionReport,
    IntegrityReport,
    PublicRecord,
    RefreshReport,
    SourceStatus,
)
from .snapshot import SnapshotError, sync_latest_snapshot
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
        auto_sync: bool = True,
    ) -> None:
        self.database = Path(database)
        self.http = PoliteHttpClient(timeout=timeout, min_interval=min_interval)
        self.camara = CamaraSource(self.http)
        self.prefeitura = PrefeituraSource(self.http)
        self.auto_sync = auto_sync
        self.last_bootstrap_error: str | None = None

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
                    (
                        "Prefeitura / contas públicas",
                        lambda: self.prefeitura.fiscal_documents(year=year, limit=400),
                    ),
                    (
                        "Prefeitura / orçamento",
                        lambda: self.prefeitura.budget_documents(year=year, limit=250),
                    ),
                    (
                        "Prefeitura / imprensa oficial",
                        lambda: self.prefeitura.official_gazette(year=year, limit=300),
                    ),
                    (
                        "Prefeitura / leis e decretos",
                        lambda: self.prefeitura.legal_acts(year=year, limit=300),
                    ),
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

    def refresh(
        self,
        *,
        years: Iterable[int] | None = None,
        profile: Profile = "completo",
        discover: bool = True,
        include_news: bool = True,
        max_pages: int = 750,
        max_depth: int = 3,
    ) -> RefreshReport:
        """Atualiza dados oficiais, descobre páginas e otimiza o índice local."""
        started = datetime.now(UTC)
        current_year = started.year
        resolved_years = sorted(
            set(years if years is not None else (current_year - 2, current_year - 1, current_year))
        )
        errors: list[str] = []
        official_seen = 0
        discovered_seen = 0
        new_records = 0
        changed_records = 0
        failed = 0

        for year in resolved_years:
            report = self.collect(year=year, profile=profile)
            official_seen += report.records
            new_records += report.new_records
            changed_records += report.changed_records
            failed += report.sources_failed
            errors.extend(report.errors)

        if discover:
            discovery = WebDiscovery(self.http)
            discovered: list[PublicRecord] = []
            try:
                discovered.extend(
                    discovery.discover(
                        (source.url for source in SOURCES),
                        max_pages=max_pages,
                        max_depth=max_depth,
                    )
                )
            except Exception as exc:
                errors.append(f"Descoberta web: {type(exc).__name__}: {exc}")
                failed += 1
            if include_news:
                try:
                    discovered.extend(discovery.discover_news())
                except Exception as exc:
                    errors.append(f"Descoberta de notícias: {type(exc).__name__}: {exc}")
                    failed += 1

            unique = {record.id: record for record in discovered}
            discovered_seen = len(unique)
            if unique:
                with Store(self.database) as store:
                    web_changes = store.upsert_many(unique.values())
                new_records += sum(item.change_type == "novo" for item in web_changes)
                changed_records += sum(item.change_type == "alterado" for item in web_changes)
            failed += discovery.stats.failed

        with Store(self.database) as store:
            store.optimize()
            indexed_records = store.count_records()

        return RefreshReport(
            started_at=started,
            finished_at=datetime.now(UTC),
            years=resolved_years,
            official_records_seen=official_seen,
            discovered_records_seen=discovered_seen,
            new_records=new_records,
            changed_records=changed_records,
            indexed_records=indexed_records,
            sources_failed=failed,
            errors=errors,
        )

    def sync(self) -> int:
        """Instala o snapshot público pré-indexado mais recente."""
        return sync_latest_snapshot(self.database)

    def reindex(self) -> int:
        with Store(self.database) as store:
            count = store.rebuild_search_index()
            store.optimize()
            return count

    def search(
        self,
        query: str,
        *,
        limit: int = 50,
        live_fallback: bool = True,
    ) -> list[PublicRecord]:
        self._bootstrap_search_database()
        with Store(self.database) as store:
            records = store.search(query, limit=limit)
        if records or not live_fallback:
            return records

        discovery = WebDiscovery(self.http)
        try:
            fresh = discovery.discover_news((query,), per_query=max(25, limit))
        except Exception:
            return []
        if not fresh:
            return []
        with Store(self.database) as store:
            store.upsert_many(fresh)
            return store.search(query, limit=limit)

    def _bootstrap_search_database(self) -> None:
        if not self.auto_sync:
            return
        needs_snapshot = not self.database.exists()
        if not needs_snapshot:
            try:
                with Store(self.database) as store:
                    needs_snapshot = store.count_records() == 0
            except Exception:
                needs_snapshot = True
        if not needs_snapshot:
            return
        try:
            self.sync()
            self.last_bootstrap_error = None
        except (SnapshotError, OSError) as exc:
            self.last_bootstrap_error = str(exc)

    def snapshot(self) -> dict[str, int]:
        with Store(self.database) as store:
            return store.counts_by_kind()

    def changes(self, *, limit: int = 50) -> list[Change]:
        with Store(self.database) as store:
            return store.latest_changes(limit=limit)

    def integrity(self) -> IntegrityReport:
        """Executa verificações determinísticas de integridade em fontes públicas selecionadas."""
        return check_transparency_integrity(self.http)

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

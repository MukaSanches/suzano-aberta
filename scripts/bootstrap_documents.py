from __future__ import annotations

import argparse
import json
from pathlib import Path

from suzano_aberta.catalog import EXPANSION_SEEDS, SOURCES
from suzano_aberta.discovery import WebDiscovery
from suzano_aberta.http import PoliteHttpClient
from suzano_aberta.store import Store

DIRECT_DOCUMENT_SEEDS: tuple[str, ...] = (
    "https://suzano.sp.gov.br/wp-content/uploads/2026/05/PLANO-ESTRATEGICO-INSTITUCIONAL-2025-2028.pdf",
    "https://suzano.sp.gov.br/wp-content/uploads/2026/05/SIGILO-LAI.pdf",
    "https://suzano.sp.gov.br/wp-content/uploads/2026/04/PE-019-2026-Aquisicao-de-computador-com-sistema-operacional-e-monitor-SRP-ComprasGov.pdf",
    "https://suzano.sp.gov.br/wp-content/uploads/2026/01/Edicao-EXTRA-016.1-27.01.2026.pdf",
    "https://www.camarasuzano.sp.gov.br/downloads/pca2026.pdf",
    "https://www.camarasuzano.sp.gov.br/wp-content/uploads/2026/03/Parej-301-A-2026-PGL-PE-001-2026-SRP-1.pdf",
)

DOCUMENT_CATEGORIES = {
    "compras-publicas",
    "contratos",
    "diario",
    "fiscal",
    "legislacao",
    "orcamento",
    "transparencia",
}


def _upsert(database: Path, records: list[object]) -> int:
    if not records:
        return 0
    with Store(database) as store:
        changes = store.upsert_many(records)  # type: ignore[arg-type]
        store.optimize()
    return len(changes)


def bootstrap(database: Path, *, max_pages: int, max_documents: int) -> dict[str, object]:
    http = PoliteHttpClient(timeout=25.0, min_interval=0.12)
    direct_records = []
    hub_records = []
    try:
        direct = WebDiscovery(http)
        direct_records = direct.discover(
            DIRECT_DOCUMENT_SEEDS,
            max_pages=max(1, len(DIRECT_DOCUMENT_SEEDS)),
            max_depth=0,
            max_documents=len(DIRECT_DOCUMENT_SEEDS),
            include_sitemaps=False,
        )
        _upsert(database, direct_records)

        hub_seeds = [source.url for source in SOURCES if source.category in DOCUMENT_CATEGORIES]
        hub_seeds.extend(url for url in EXPANSION_SEEDS if not url.casefold().endswith(".pdf"))
        hubs = WebDiscovery(http)
        hub_records = hubs.discover(
            dict.fromkeys(hub_seeds),
            max_pages=max_pages,
            max_depth=2,
            max_documents=max_documents,
            include_sitemaps=False,
        )
        _upsert(database, hub_records)
    finally:
        http.close()

    with Store(database) as store:
        counts = store.counts_by_kind()
        total = store.count_records()

    documents = int(counts.get("arquivo", 0))
    if documents < 1:
        raise RuntimeError(
            "Nenhum documento público foi indexado; recusando continuar com um snapshot sem arquivos."
        )

    return {
        "records": total,
        "documents": documents,
        "direct_records_seen": len(direct_records),
        "hub_records_seen": len(hub_records),
        "counts_by_kind": counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prioriza documentos públicos oficiais antes da coleta geral do Suzano Aberta."
    )
    parser.add_argument("--database", type=Path, default=Path("suzano-aberta.sqlite3"))
    parser.add_argument("--max-pages", type=int, default=120)
    parser.add_argument("--max-documents", type=int, default=500)
    args = parser.parse_args()
    if args.max_pages < 1 or args.max_documents < 1:
        parser.error("--max-pages e --max-documents devem ser >= 1")
    result = bootstrap(
        args.database,
        max_pages=args.max_pages,
        max_documents=args.max_documents,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

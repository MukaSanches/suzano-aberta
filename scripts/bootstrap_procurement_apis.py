from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from suzano_aberta.http import PoliteHttpClient
from suzano_aberta.models import PublicRecord
from suzano_aberta.sources import ComprasGovSource, PncpSource
from suzano_aberta.store import Store


def _years(raw: str | None) -> list[int]:
    if raw:
        values = sorted({int(part.strip()) for part in raw.split(",") if part.strip()})
        if not values:
            raise ValueError("nenhum ano válido informado")
        return values
    current = datetime.now(UTC).year
    return [current - 2, current - 1, current]


def bootstrap(database: Path, years: list[int]) -> dict[str, object]:
    records: dict[str, PublicRecord] = {}
    errors: list[str] = []
    source_counts = {
        "pncp_contratacoes": 0,
        "pncp_contratos": 0,
        "pncp_atas": 0,
        "comprasgov_contratacoes": 0,
    }

    with PoliteHttpClient(timeout=15.0, min_interval=0.08, max_response_bytes=16 * 1024 * 1024) as http:
        pncp = PncpSource(http)
        compras = ComprasGovSource(http)
        for year in years:
            collectors = (
                ("pncp_contratacoes", lambda year=year: pncp.procurements(year=year)),
                ("pncp_contratos", lambda year=year: pncp.contracts(year=year)),
                ("pncp_atas", lambda year=year: pncp.atas(year=year)),
                ("comprasgov_contratacoes", lambda year=year: compras.procurements(year=year)),
            )
            for label, collector in collectors:
                try:
                    batch = collector()
                except Exception as exc:
                    errors.append(f"{label}/{year}: {type(exc).__name__}: {exc}")
                    continue
                source_counts[label] += len(batch)
                for record in batch:
                    records[record.id] = record

    api_records = sum(source_counts.values())
    if api_records < 1:
        raise RuntimeError(
            "PNCP e Compras.gov não retornaram registros de Suzano para os anos solicitados: "
            + (" | ".join(errors) if errors else "sem erro detalhado")
        )

    with Store(database) as store:
        changes = store.upsert_many(records.values())
        store.optimize()
        counts = store.counts_by_kind()
        total = store.count_records()

    result: dict[str, object] = {
        "years": years,
        "api_records_seen": api_records,
        "unique_api_records": len(records),
        "new_or_changed": len(changes),
        "records": total,
        "counts_by_kind": counts,
        "sources": source_counts,
        "errors": errors,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atualiza rapidamente PNCP e Compras.gov antes de publicar o checkpoint de compras."
    )
    parser.add_argument("--database", type=Path, default=Path("suzano-aberta.sqlite3"))
    parser.add_argument(
        "--years",
        help="Anos separados por vírgula. Padrão: ano atual e dois anteriores.",
    )
    args = parser.parse_args()
    try:
        years = _years(args.years)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(bootstrap(args.database, years), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

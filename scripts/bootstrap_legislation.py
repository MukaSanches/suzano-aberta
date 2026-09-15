from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from suzano_aberta.http import PoliteHttpClient
from suzano_aberta.sources.legislacao import LegislacaoSource
from suzano_aberta.store import Store


def bootstrap(database: Path, *, from_year: int, to_year: int) -> dict[str, object]:
    if from_year > to_year:
        raise ValueError("from_year não pode ser posterior a to_year")

    records = {}
    errors: list[str] = []
    started = datetime.now(UTC)
    with PoliteHttpClient(timeout=20.0, min_interval=0.12) as http:
        source = LegislacaoSource(http)
        for year in range(to_year, from_year - 1, -1):
            try:
                for record in source.collect(year=year):
                    records[record.id] = record
            except Exception as exc:
                errors.append(f"{year}: {type(exc).__name__}: {exc}")

    with Store(database) as store:
        changes = store.upsert_many(records.values())
        store.optimize()
        counts = store.counts_by_kind()
        total = store.count_records()

    existing_legislation = int(counts.get("lei", 0)) + int(counts.get("decreto", 0))
    fresh = len(records)
    reused_snapshot = fresh == 0 and existing_legislation > 0

    result: dict[str, object] = {
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "from_year": from_year,
        "to_year": to_year,
        "legislation_seen": fresh,
        "legislation_available": existing_legislation,
        "reused_previous_snapshot": reused_snapshot,
        "new_records": sum(change.change_type == "novo" for change in changes),
        "changed_records": sum(change.change_type == "alterado" for change in changes),
        "database_records": total,
        "errors": errors,
    }
    return result


def main() -> None:
    current_year = datetime.now(UTC).year
    parser = argparse.ArgumentParser(
        description=(
            "Carrega índices anuais oficiais de leis municipais e complementares da Câmara de Suzano. "
            "Se a fonte estiver temporariamente indisponível, preserva a última legislação válida já "
            "existente no snapshot em vez de interromper toda a atualização."
        )
    )
    parser.add_argument("--database", type=Path, default=Path("suzano-aberta.sqlite3"))
    parser.add_argument("--from-year", type=int, default=1949)
    parser.add_argument("--to-year", type=int, default=current_year)
    args = parser.parse_args()
    result = bootstrap(args.database, from_year=args.from_year, to_year=args.to_year)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))

    if int(result["legislation_seen"]) > 0:
        return
    if int(result["legislation_available"]) > 0:
        print(
            "AVISO: a fonte legislativa não respondeu nesta execução; "
            "a última legislação válida do snapshot foi preservada."
        )
        return
    raise SystemExit(
        "nenhuma lei municipal foi coletada e o snapshot não contém legislação anterior válida"
    )


if __name__ == "__main__":
    main()

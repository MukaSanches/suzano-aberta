from __future__ import annotations

import argparse
import gzip
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


LAW_NUMBER_RE = re.compile(r"\b(?:lei(?:\s+complementar)?|decreto)\s*(?:n\s*[º°o.]?\s*)?([0-9][0-9.]*)", re.I)


def fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


def identity(item: dict[str, Any]) -> tuple[str, str, str, str]:
    kind = str(item.get("kind") or "")
    title = str(item.get("title") or "")
    match = LAW_NUMBER_RE.search(fold(title))
    number = re.sub(r"\D", "", match.group(1)) if match else ""
    date = str(item.get("effective_date") or item.get("date") or "")
    type_hint = "complementar" if "lei complementar" in fold(title) else kind
    if number:
        return kind, type_hint, number, date
    return kind, type_hint, fold(title), date


def source_priority(item: dict[str, Any]) -> tuple[int, int]:
    source = item.get("source") or {}
    name = fold(source.get("name"))
    kind = str(item.get("kind") or "")
    if kind == "lei" and "camara" in name and "legislacao" in name:
        return 30, 1
    if kind == "decreto" and "prefeitura" in name:
        return 30, 1
    if "prefeitura" in name or "camara" in name:
        return 20, 1
    return 10, 0


def sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("effective_date") or item.get("date") or ""),
        str(item.get("title") or ""),
        str(item.get("id") or ""),
    )


def build(source: Path, output: Path) -> dict[str, Any]:
    with gzip.open(source, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    raw_items = payload.get("items") or []
    if not isinstance(raw_items, list):
        raise RuntimeError("coleção legislativa publicada não contém uma lista de itens")

    selected: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "")
        if kind not in {"lei", "decreto", "proposicao"}:
            continue
        key = identity(raw)
        current = selected.get(key)
        if current is None or source_priority(raw) > source_priority(current):
            selected[key] = raw

    items = sorted(selected.values(), key=sort_key, reverse=True)
    counts = Counter(str(item.get("kind") or "") for item in items)
    if counts.get("lei", 0) < 1:
        raise RuntimeError("feed do navegador recusado: nenhuma lei foi encontrada")

    sources = sorted({
        str((item.get("source") or {}).get("name") or "").strip()
        for item in items
        if str((item.get("source") or {}).get("name") or "").strip()
    })
    meta = {
        "schema": 1,
        "generated_at": (payload.get("meta") or {}).get("generated_at"),
        "total": len(items),
        "raw_total": len(raw_items),
        "counts_by_kind": dict(sorted(counts.items())),
        "sources": sources,
        "default_sort": "date_desc",
        "source_file": source.name,
    }
    result = {"meta": meta, "items": items}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materializa um feed JSON sem compressão para a página de legislação do navegador."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("web/api/v1/legislacao.json.gz"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("web/data/legislation.json"),
    )
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()

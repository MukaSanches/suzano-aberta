from __future__ import annotations

import argparse
import gzip
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


KINDS = ("lei", "decreto", "proposicao")
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


def browser_item(item: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields needed by the browser legislation experience.

    The canonical full record remains available through the generated Data API and
    detail collections. Keeping this feed deliberately small cuts parse time and
    memory pressure on phones and older desktops.
    """

    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    compact_source = {
        key: source.get(key)
        for key in ("name", "url")
        if source.get(key) not in (None, "")
    }
    compact: dict[str, Any] = {}
    for key in (
        "id",
        "kind",
        "title",
        "summary",
        "date",
        "effective_date",
        "date_basis",
        "year",
        "document_url",
        "source_name",
        "source_url",
    ):
        value = item.get(key)
        if value not in (None, ""):
            compact[key] = value
    if compact_source:
        compact["source"] = compact_source
    return compact


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
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
        if kind not in set(KINDS):
            continue
        key = identity(raw)
        current = selected.get(key)
        if current is None or source_priority(raw) > source_priority(current):
            selected[key] = raw

    canonical = sorted(selected.values(), key=sort_key, reverse=True)
    items = [browser_item(item) for item in canonical]
    counts = Counter(str(item.get("kind") or "") for item in items)
    if counts.get("lei", 0) < 1:
        raise RuntimeError("feed do navegador recusado: nenhuma lei foi encontrada")

    sources = sorted({
        str((item.get("source") or {}).get("name") or item.get("source_name") or "").strip()
        for item in items
        if str((item.get("source") or {}).get("name") or item.get("source_name") or "").strip()
    })

    stem = output.stem
    shard_files = {kind: f"{stem}-{kind}.json" for kind in KINDS}
    meta = {
        "schema": 2,
        "generated_at": (payload.get("meta") or {}).get("generated_at"),
        "total": len(items),
        "raw_total": len(raw_items),
        "counts_by_kind": dict(sorted(counts.items())),
        "sources": sources,
        "default_sort": "date_desc",
        "source_file": source.name,
        "shards": shard_files,
        "browser_fields": [
            "id",
            "kind",
            "title",
            "summary",
            "date",
            "effective_date",
            "date_basis",
            "year",
            "document_url",
            "source",
            "source_name",
            "source_url",
        ],
    }

    # Compatibility feed: existing validators and fallback paths can still use it.
    write_json(output, {"meta": meta, "items": items})

    # Fast path: the browser loads only the selected category. Because every shard
    # is already sorted newest-first, the common page load does no client sorting.
    for kind in KINDS:
        shard_items = [item for item in items if item.get("kind") == kind]
        write_json(
            output.with_name(shard_files[kind]),
            {
                "meta": {**meta, "scope_kind": kind, "scope_total": len(shard_items)},
                "items": shard_items,
            },
        )

    # Tiny metadata document lets the worker validate counts without downloading
    # the compatibility feed first.
    write_json(output.with_name(f"{stem}-index.json"), {"meta": meta})
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materializa feeds compactos e particionados para a página de legislação do navegador."
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

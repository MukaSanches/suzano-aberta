from __future__ import annotations

import argparse
import gzip
import html
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

KINDS = ("lei", "decreto", "proposicao")
PAGE_SIZE = 40
LAW_NUMBER_RE = re.compile(r"\b(?:lei(?:\s+complementar)?|decreto)\s*(?:n\s*[º°o.]?\s*)?([0-9][0-9.]*)", re.I)
BOOTSTRAP_START = "<!-- legislation-bootstrap:start -->"
BOOTSTRAP_END = "<!-- legislation-bootstrap:end -->"


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
    return (kind, type_hint, number if number else fold(title), date)


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
    return (str(item.get("effective_date") or item.get("date") or ""), str(item.get("title") or ""), str(item.get("id") or ""))


def browser_item(item: dict[str, Any]) -> dict[str, Any]:
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    compact_source = {key: source.get(key) for key in ("name", "url") if source.get(key) not in (None, "")}
    compact: dict[str, Any] = {}
    for key in ("id", "kind", "title", "summary", "date", "effective_date", "date_basis", "year", "document_url", "source_name", "source_url"):
        value = item.get(key)
        if value not in (None, ""):
            compact[key] = value
    if compact_source:
        compact["source"] = compact_source
    return compact


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _display_date(value: str) -> str:
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value or "")
    return f"{match.group(3)}/{match.group(2)}/{match.group(1)}" if match else (value or "Data não informada")


def _source(item: dict[str, Any]) -> tuple[str, str, str]:
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    name = str(source.get("name") or item.get("source_name") or "Fonte pública")
    official = str(item.get("document_url") or source.get("url") or item.get("source_url") or "")
    page = str(source.get("url") or item.get("source_url") or item.get("document_url") or "")
    return name, official, page


def _initial_results_html(items: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for item in items:
        kind = str(item.get("kind") or "")
        date = str(item.get("effective_date") or item.get("date") or (f"{item.get('year')}-01-01" if item.get("year") else ""))
        title = str(item.get("title") or "Registro legislativo")
        summary = str(item.get("summary") or "")[:520]
        source_name, official, page = _source(item)
        if kind in {"lei", "decreto"}:
            internal = f"./norma.html?id={quote(str(item.get('id') or ''))}&source={quote(page)}"
            href = internal
            action = f'<a data-detail-link href="{html.escape(internal, quote=True)}">Visualizar {"decreto" if kind == "decreto" else "lei"}</a>'
            target = ""
        else:
            href = page or official or "#"
            action = ""
            target = ' target="_blank" rel="noopener noreferrer"' if href != "#" else ""
        kind_label = {"lei": "Lei", "decreto": "Decreto", "proposicao": "Proposição"}.get(kind, "Registro")
        official_link = f'<a href="{html.escape(official or page, quote=True)}" target="_blank" rel="noopener noreferrer">Fonte oficial</a>' if official or page else ""
        year_hint = '<span title="A fonte informa somente o ano.">data por ano</span>' if item.get("date_basis") == "year" else ""
        rows.append('<li class="result">' f'<div class="result-meta"><span class="tag">{html.escape(kind_label)}</span><time datetime="{html.escape(date, quote=True)}">{html.escape(_display_date(date))}</time>{year_hint}</div>' f'<h2 class="result-title"><a href="{html.escape(href, quote=True)}"{target}>{html.escape(title)}</a></h2>' + (f'<p>{html.escape(summary)}</p>' if summary else "") + f'<div class="result-actions">{action}{official_link}<span>{html.escape(source_name)}</span></div></li>')
    return '<ul class="result-list">' + "".join(rows) + '</ul>'


def inject_bootstrap(page: Path, *, meta: dict[str, Any], laws: list[dict[str, Any]]) -> None:
    if not page.exists():
        return
    text = page.read_text(encoding="utf-8")
    text = re.sub(re.escape(BOOTSTRAP_START) + r".*?" + re.escape(BOOTSTRAP_END) + r"\n?", "", text, flags=re.S)
    bootstrap = {"meta": meta, "kind": "lei", "sort": "date_desc", "offset": 0, "limit": PAGE_SIZE, "total": int((meta.get("counts_by_kind") or {}).get("lei", len(laws))), "items": laws[:PAGE_SIZE]}
    inline = json.dumps(bootstrap, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    block = f'{BOOTSTRAP_START}\n<script type="application/json" id="legislation-bootstrap">{inline}</script>\n{BOOTSTRAP_END}\n'
    script_marker = '<script defer src="./assets/legislation-v9.js"></script>'
    if script_marker not in text:
        raise RuntimeError("legislacao.html não contém o cliente legislation-v9.js")
    text = text.replace(script_marker, block + script_marker, 1)
    initial = _initial_results_html(laws[:PAGE_SIZE])
    pattern = re.compile(r'<div data-results(?:\s+data-bootstrap-results="true")? aria-live="polite">.*?</div>', re.S)
    text, count = pattern.subn(f'<div data-results data-bootstrap-results="true" aria-live="polite">{initial}</div>', text, count=1)
    if count != 1:
        raise RuntimeError("não foi possível materializar os resultados iniciais da legislação")
    total = int((meta.get("counts_by_kind") or {}).get("lei", len(laws)))
    text = re.sub(r'<p class="result-count" data-result-count>.*?</p>', f'<p class="result-count" data-result-count>{total:,} resultados</p>'.replace(",", "."), text, count=1)
    page.write_text(text, encoding="utf-8")


def build(source: Path, output: Path, *, page: Path | None = None) -> dict[str, Any]:
    with gzip.open(source, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    raw_items = payload.get("items") or []
    if not isinstance(raw_items, list):
        raise RuntimeError("coleção legislativa publicada não contém uma lista de itens")
    selected: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for raw in raw_items:
        if not isinstance(raw, dict) or str(raw.get("kind") or "") not in KINDS:
            continue
        key = identity(raw)
        current = selected.get(key)
        if current is None or source_priority(raw) > source_priority(current):
            selected[key] = raw
    items = [browser_item(item) for item in sorted(selected.values(), key=sort_key, reverse=True)]
    counts = Counter(str(item.get("kind") or "") for item in items)
    if counts.get("lei", 0) < 1:
        raise RuntimeError("feed do navegador recusado: nenhuma lei foi encontrada")
    sources = sorted({str((item.get("source") or {}).get("name") or item.get("source_name") or "").strip() for item in items if str((item.get("source") or {}).get("name") or item.get("source_name") or "").strip()})
    stem = output.stem
    shard_files = {kind: f"{stem}-{kind}.json" for kind in KINDS}
    meta = {"schema": 3, "generated_at": (payload.get("meta") or {}).get("generated_at"), "total": len(items), "raw_total": len(raw_items), "counts_by_kind": dict(sorted(counts.items())), "sources": sources, "default_sort": "date_desc", "source_file": source.name, "shards": shard_files, "bootstrap": f"{stem}-bootstrap.json", "browser_fields": ["id", "kind", "title", "summary", "date", "effective_date", "date_basis", "year", "document_url", "source", "source_name", "source_url"]}
    write_json(output, {"meta": meta, "items": items})
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for kind in KINDS:
        shard_items = [item for item in items if item.get("kind") == kind]
        by_kind[kind] = shard_items
        write_json(output.with_name(shard_files[kind]), {"meta": {**meta, "scope_kind": kind, "scope_total": len(shard_items)}, "items": shard_items})
    write_json(output.with_name(f"{stem}-index.json"), {"meta": meta})
    bootstrap = {"meta": meta, "kind": "lei", "sort": "date_desc", "offset": 0, "limit": PAGE_SIZE, "total": int(counts.get("lei", 0)), "items": by_kind["lei"][:PAGE_SIZE]}
    write_json(output.with_name(f"{stem}-bootstrap.json"), bootstrap)
    if page is not None:
        inject_bootstrap(page, meta=meta, laws=by_kind["lei"])
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Materializa feeds rápidos para a página de legislação.")
    parser.add_argument("--source", type=Path, default=Path("web/api/v1/legislacao.json.gz"))
    parser.add_argument("--output", type=Path, default=Path("web/data/legislation.json"))
    parser.add_argument("--page", type=Path, default=Path("web/legislacao.html"))
    args = parser.parse_args()
    result = build(args.source, args.output, page=args.page)
    try:
        from scripts.inject_line11_module import inject_homepage
    except ModuleNotFoundError:
        from inject_line11_module import inject_homepage
    homepage = args.page.parent / "index.html"
    if homepage.exists():
        inject_homepage(homepage)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

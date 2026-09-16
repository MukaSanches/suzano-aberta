from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STOPWORDS = {
    "a", "ao", "aos", "as", "com", "da", "das", "de", "do", "dos", "e", "em", "na", "nas",
    "no", "nos", "o", "os", "ou", "para", "por", "que", "se", "sem", "um", "uma", "uns", "umas",
    "the", "and", "of", "to", "in", "for", "on", "www", "http", "https", "com", "br",
}
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]+")
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
BR_DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})")
DOCUMENT_KINDS = {
    "arquivo", "arquivo_historico", "diario", "documento_fiscal", "documento_orcamentario",
    "lei", "decreto",
}
LEGISLATION_KINDS = {"lei", "decreto", "proposicao"}
SEARCH_CONTEXT_KEYS = (
    "ementa", "assunto", "tema", "objeto", "descricao", "descricao_complementar",
    "texto", "texto_integral", "autor", "author", "processo", "numero", "modalidade",
    "situacao", "contratada", "contractor", "fornecedor", "orgao", "secretaria",
)


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_like = "".join(char for char in decomposed if not unicodedata.combining(char))
    return ascii_like.casefold()


def flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(f"{key} {flatten(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(flatten(item) for item in value)
    return str(value)


def search_context(payload: dict[str, Any], *, max_chars: int = 1100) -> str:
    """Extrai evidência legível para explicar por que um registro apareceu na busca.

    O índice completo continua usando todos os atributos. Este campo é apenas um
    trecho compacto e de alto sinal para que a interface mostre contexto útil em
    vez de texto de navegação ou o início arbitrário de uma página.
    """
    attributes = payload.get("attributes") or {}
    if not isinstance(attributes, dict):
        return ""

    parts: list[str] = []
    seen: set[str] = set()
    for key in SEARCH_CONTEXT_KEYS:
        if key not in attributes:
            continue
        text = re.sub(r"\s+", " ", flatten(attributes.get(key))).strip()
        if not text:
            continue
        marker = normalize_text(text[:180])
        if marker in seen:
            continue
        seen.add(marker)
        label = key.replace("_", " ")
        parts.append(f"{label}: {text}")
        if sum(len(part) for part in parts) >= max_chars:
            break

    if not parts and str(payload.get("kind") or "") not in {"pagina_web", "noticia"}:
        generic = re.sub(r"\s+", " ", flatten(attributes)).strip()
        if generic:
            parts.append(generic)

    return " · ".join(parts)[:max_chars]


def tokens_for(payload: dict[str, Any], *, max_tokens: int) -> list[str]:
    source = payload.get("source") or {}
    parts = [
        str(payload.get("title") or ""),
        str(payload.get("summary") or ""),
        str(source.get("name") or ""),
        flatten(payload.get("attributes") or {}),
    ]
    text = normalize_text(" ".join(parts))
    seen: set[str] = set()
    result: list[str] = []
    for token in TOKEN_RE.findall(text):
        if token in STOPWORDS or len(token) < 2 or len(token) > 64 or token in seen:
            continue
        seen.add(token)
        result.append(token)
        if len(result) >= max_tokens:
            break
    return result


def canonical_date(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    match = ISO_DATE_RE.match(raw)
    if match:
        year, month, day = map(int, match.groups())
    else:
        match = BR_DATE_RE.match(raw)
        if not match:
            return None
        day, month, year = map(int, match.groups())
    try:
        return datetime(year, month, day, tzinfo=UTC).date().isoformat()
    except ValueError:
        return None


def effective_date(payload: dict[str, Any], last_seen: str) -> tuple[str, str]:
    """Resolve somente datas públicas comprováveis para ordenação cronológica.

    ``last_seen`` continua no contrato da função porque a data de observação é
    preservada em cada item publicado, mas ela nunca deve ser promovida a data
    efetiva do fato. Isso evita que conteúdo histórico descoberto hoje pareça
    ter sido publicado hoje.
    """
    _ = last_seen
    record_date = canonical_date(payload.get("date"))
    if record_date:
        return record_date, "record"
    year = payload.get("year")
    try:
        year_value = int(year)
    except (TypeError, ValueError):
        year_value = 0
    if 1800 <= year_value <= 2200:
        return f"{year_value:04d}-01-01", "year"
    return "", "unknown"


def shard_for(token: str) -> int:
    first = ord(token[0]) if token else 0
    second = ord(token[1]) if len(token) > 1 else 0
    return (first * 31 + second) & 31


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def write_json_gzip(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))


def public_item(payload: dict[str, Any], *, effective: str, basis: str, last_seen: str) -> dict[str, Any]:
    source = payload.get("source") or {}
    attributes = payload.get("attributes") or {}
    document_url = attributes.get("document_url") or attributes.get("pdf_url") or source.get("url")
    return {
        "id": payload.get("id"),
        "kind": payload.get("kind"),
        "title": payload.get("title"),
        "summary": payload.get("summary"),
        "date": payload.get("date"),
        "effective_date": effective,
        "date_basis": basis,
        "year": payload.get("year"),
        "source": {"name": source.get("name"), "url": source.get("url")},
        "document_url": document_url,
        "last_seen": last_seen,
    }


def build(database: Path, output: Path, *, max_tokens_per_record: int = 1800) -> dict[str, Any]:
    uri = f"file:{database.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        check = conn.execute("PRAGMA quick_check").fetchone()[0]
        if str(check).casefold() != "ok":
            raise RuntimeError(f"SQLite quick_check falhou: {check}")
        rows = conn.execute(
            """
            SELECT id, kind, title, source_name, source_url, last_seen, payload_json
            FROM records
            WHERE active=1
            """
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise RuntimeError("O banco não contém registros ativos; o portal não será publicado com acervo vazio.")

    enriched: list[tuple[sqlite3.Row, dict[str, Any], str, str]] = []
    for row in rows:
        payload = json.loads(str(row["payload_json"]))
        effective, basis = effective_date(payload, str(row["last_seen"]))
        enriched.append((row, payload, effective, basis))
    enriched.sort(key=lambda item: (item[2], str(item[0]["id"])), reverse=True)

    record_rows: list[list[Any]] = []
    api_rows: list[dict[str, Any]] = []
    postings: dict[str, list[int]] = defaultdict(list)
    kinds: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    years: Counter[int] = Counter()
    documents = 0
    legislation = 0
    latest: list[dict[str, Any]] = []
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for index, (row, payload, effective, basis) in enumerate(enriched):
        source = payload.get("source") or {}
        year = payload.get("year")
        try:
            year_value = int(year) if year is not None else None
        except (TypeError, ValueError):
            year_value = None
        summary = str(payload.get("summary") or "")
        kind = str(payload.get("kind") or row["kind"])
        context = search_context(payload)
        compact = [
            str(payload.get("id") or row["id"]), kind,
            str(payload.get("title") or row["title"]), payload.get("date"), year_value,
            str(source.get("name") or row["source_name"]), str(source.get("url") or row["source_url"]),
            str(row["last_seen"]), summary[:500], effective, basis, context,
        ]
        record_rows.append(compact)
        item = public_item(payload, effective=effective, basis=basis, last_seen=str(row["last_seen"]))
        api_rows.append(item)
        kinds[kind] += 1
        sources[compact[5]] += 1
        if year_value is not None:
            years[year_value] += 1
        if kind in DOCUMENT_KINDS:
            documents += 1
        if kind in LEGISLATION_KINDS:
            legislation += 1
        if effective:
            by_date[effective].append(item)
        if len(latest) < 40 and effective:
            latest.append({
                "id": compact[0], "kind": compact[1], "title": compact[2], "date": compact[3],
                "effective_date": effective, "date_basis": basis, "year": compact[4],
                "source_name": compact[5], "source_url": compact[6],
            })
        for token in tokens_for(payload, max_tokens=max_tokens_per_record):
            postings[token].append(index)

    if documents < 1:
        raise RuntimeError("O acervo validado não contém documentos; publicação recusada.")
    if legislation < 1:
        raise RuntimeError("O acervo validado não contém leis, decretos ou proposições; publicação recusada.")

    output.mkdir(parents=True, exist_ok=True)
    index_dir = output / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    for old in index_dir.glob("*.json.gz"):
        old.unlink()

    shards: list[dict[str, list[int]]] = [dict() for _ in range(32)]
    for token, ids in postings.items():
        shards[shard_for(token)][token] = ids
    for number, shard in enumerate(shards):
        write_json_gzip(index_dir / f"{number:02x}.json.gz", dict(sorted(shard.items())))

    lexicon = sorted(postings)
    write_json_gzip(output / "records.json.gz", record_rows)
    write_json_gzip(output / "lexicon.json.gz", lexicon)

    years_sorted = sorted(years)
    generated_at = datetime.now(UTC).isoformat()
    manifest = {
        "schema": 2,
        "generated_at": generated_at,
        "records": len(record_rows),
        "documents": documents,
        "legislation": legislation,
        "sources": len(sources),
        "years_covered": len(years),
        "first_year": years_sorted[0] if years_sorted else None,
        "last_year": years_sorted[-1] if years_sorted else None,
        "tokens": len(lexicon),
        "search_shards": 32,
        "default_sort": "date_desc",
        "default_date_mode": "effective",
        "counts_by_kind": dict(sorted(kinds.items())),
        "top_sources": [{"name": name, "records": count} for name, count in sources.most_common(30)],
        "years": [{"year": year, "records": years[year]} for year in sorted(years, reverse=True)],
        "latest": latest,
        "snapshot": "https://github.com/MukaSanches/suzano-aberta/releases/tag/data-latest",
        "record_fields": [
            "id", "kind", "title", "date", "year", "source_name", "source_url", "last_seen",
            "summary", "effective_date", "date_basis", "search_context",
        ],
    }
    write_json(output / "manifest.json", manifest)

    # API estática de alta disponibilidade, publicada no mesmo GitHub Pages.
    api_root = output.parent / "api"
    if api_root.exists():
        shutil.rmtree(api_root)
    documents_rows = [item for item in api_rows if item["kind"] in DOCUMENT_KINDS]
    legislation_rows = [item for item in api_rows if item["kind"] in LEGISLATION_KINDS]
    stats = {
        "generated_at": generated_at,
        "records": len(api_rows),
        "documents": len(documents_rows),
        "legislation": len(legislation_rows),
        "sources": len(sources),
        "years_covered": len(years),
        "kinds": dict(sorted(kinds.items())),
    }
    write_json(api_root / "health" / "ready.json", {
        "status": "ok", "ready": True, **stats,
    })
    write_json(api_root / "v1" / "index.json", {
        "name": "Suzano Aberta Data API",
        "version": "1.0",
        "generated_at": generated_at,
        "default_sort": "effective_date desc",
        "date_semantics": {
            "record": "data publicada pelo registro",
            "year": "ano conhecido, sem dia/mês disponível",
            "unknown": "data pública não informada; a data de observação permanece em last_seen",
        },
        "endpoints": {
            "stats": "./stats.json",
            "records": "./records.json.gz",
            "documents": "./documentos.json.gz",
            "legislation": "./legislacao.json.gz",
            "by_date": "./by-date/YYYY/MM/DD.json.gz",
        },
    })
    write_json(api_root / "v1" / "stats.json", stats)
    write_json_gzip(api_root / "v1" / "records.json.gz", {"meta": stats, "items": api_rows})
    write_json_gzip(api_root / "v1" / "documentos.json.gz", {"meta": stats, "items": documents_rows})
    write_json_gzip(api_root / "v1" / "legislacao.json.gz", {"meta": stats, "items": legislation_rows})
    for effective, items in by_date.items():
        year, month, day = effective.split("-")
        write_json_gzip(api_root / "v1" / "by-date" / year / month / f"{day}.json.gz", {
            "date": effective,
            "count": len(items),
            "items": items,
        })

    digest = hashlib.sha256()
    for root in (output, api_root):
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "manifest.sha256":
                digest.update(path.relative_to(output.parent).as_posix().encode())
                digest.update(path.read_bytes())
    (output / "manifest.sha256").write_text(digest.hexdigest() + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o índice estático e a Data API do portal Suzano Aberta.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("web/data"))
    parser.add_argument("--max-tokens-per-record", type=int, default=1800)
    args = parser.parse_args()
    manifest = build(args.database, args.output, max_tokens_per_record=args.max_tokens_per_record)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()

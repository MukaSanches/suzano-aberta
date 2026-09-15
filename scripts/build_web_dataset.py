from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
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
            ORDER BY last_seen DESC, id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise RuntimeError("O banco não contém registros ativos; o portal não será publicado com acervo vazio.")

    record_rows: list[list[Any]] = []
    postings: dict[str, list[int]] = defaultdict(list)
    kinds: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    years: Counter[int] = Counter()
    documents = 0
    latest: list[dict[str, Any]] = []
    document_kinds = {"arquivo", "arquivo_historico", "diario", "documento_fiscal", "documento_orcamentario"}

    for index, row in enumerate(rows):
        payload = json.loads(str(row["payload_json"]))
        source = payload.get("source") or {}
        year = payload.get("year")
        try:
            year_value = int(year) if year is not None else None
        except (TypeError, ValueError):
            year_value = None
        summary = str(payload.get("summary") or "")
        compact = [
            str(payload.get("id") or row["id"]), str(payload.get("kind") or row["kind"]),
            str(payload.get("title") or row["title"]), payload.get("date"), year_value,
            str(source.get("name") or row["source_name"]), str(source.get("url") or row["source_url"]),
            str(row["last_seen"]), summary[:500],
        ]
        record_rows.append(compact)
        kinds[compact[1]] += 1
        sources[compact[5]] += 1
        if year_value is not None:
            years[year_value] += 1
        if compact[1] in document_kinds:
            documents += 1
        if len(latest) < 40:
            latest.append({
                "id": compact[0], "kind": compact[1], "title": compact[2], "date": compact[3],
                "year": compact[4], "source_name": compact[5], "source_url": compact[6],
            })
        for token in tokens_for(payload, max_tokens=max_tokens_per_record):
            postings[token].append(index)

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
    manifest = {
        "schema": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "records": len(record_rows),
        "documents": documents,
        "sources": len(sources),
        "years_covered": len(years),
        "first_year": years_sorted[0] if years_sorted else None,
        "last_year": years_sorted[-1] if years_sorted else None,
        "tokens": len(lexicon),
        "search_shards": 32,
        "counts_by_kind": dict(sorted(kinds.items())),
        "top_sources": [{"name": name, "records": count} for name, count in sources.most_common(30)],
        "years": [{"year": year, "records": years[year]} for year in sorted(years, reverse=True)],
        "latest": latest,
        "snapshot": "https://github.com/MukaSanches/suzano-aberta/releases/tag/data-latest",
        "record_fields": ["id", "kind", "title", "date", "year", "source_name", "source_url", "last_seen", "summary"],
    }
    write_json(output / "manifest.json", manifest)

    digest = hashlib.sha256()
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "manifest.sha256":
            digest.update(path.relative_to(output).as_posix().encode())
            digest.update(path.read_bytes())
    (output / "manifest.sha256").write_text(digest.hexdigest() + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o índice estático do portal Suzano Aberta.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("web/data"))
    parser.add_argument("--max-tokens-per-record", type=int, default=1800)
    args = parser.parse_args()
    manifest = build(args.database, args.output, max_tokens_per_record=args.max_tokens_per_record)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()

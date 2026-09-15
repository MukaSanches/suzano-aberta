from __future__ import annotations

import argparse
import copy
import gzip
import json
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

DETAIL_KINDS = {"lei", "decreto", "proposicao", "licitacao", "contrato", "ata"}
PROCUREMENT_KINDS = {"licitacao", "contrato", "ata"}
CNPJ_RE = re.compile(r"(?<!\d)(\d{2})[.\s]?(\d{3})[.\s]?(\d{3})[/\s]?(\d{4})[-\s]?(\d{2})(?!\d)")
REF_RE = re.compile(r"\b(\d{1,6}/(?:[A-Z]{2,12}/)?(?:19|20)\d{2})\b", re.I)
LAW_RE = re.compile(r"\blei(?:\s+complementar)?\s*(?:n[º°.]?|:)?\s*(\d{1,6})(?:[./-](\d{4}))?", re.I)
PROCUREMENT_CONTEXT_RE = re.compile(
    r"\b(licita[cç][aã]o|preg[aã]o|concorr[eê]ncia|dispensa|inexigibilidade|"
    r"processo(?:\s+de\s+compra)?|contrato|edital|chamada\s+p[uú]blica|leil[aã]o|"
    r"ata\s+de\s+registro\s+de\s+pre[cç]os)\b",
    re.I,
)
SUPPLIER_KEYS = {
    "contractor", "contratada", "contratado", "fornecedor", "fornecedora",
    "razao_social", "razão_social", "supplier",
}
IDENTIFIER_KEYS = {
    "identifier", "numero", "número", "number", "processo", "processo_administrativo",
    "processo_de_compra", "numero_controle_pncp", "numerocontrolepncp",
    "numero_controle_pncp_compra", "numerocontrolepncpcompra", "compras_gov", "id_compra",
}
PNCP_KEYS = (
    "numero_controle_pncp", "numerocontrolepncp", "numero_controle_pncp_compra",
    "numerocontrolepncpcompra",
)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value.casefold()).strip()


def canonical_url(value: str) -> str:
    try:
        parts = urlsplit(str(value or "").strip())
    except ValueError:
        return ""
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return ""
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path.rstrip("/") or "/", "", ""))


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


def sanitize(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return None
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:50_000]
    if isinstance(value, list):
        return [sanitize(item, depth=depth + 1) for item in value[:200]]
    if isinstance(value, tuple):
        return [sanitize(item, depth=depth + 1) for item in value[:200]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 200:
                break
            out[str(key)[:120]] = sanitize(item, depth=depth + 1)
        return out
    return str(value)[:10_000]


def shard_for(record_id: str) -> str:
    total = 0
    for char in record_id:
        total = ((total * 33) + ord(char)) & 0xFFFFFFFF
    return f"{total & 15:x}"


def write_gzip(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))


def attr_values(attributes: dict[str, Any], keys: set[str]) -> list[str]:
    values: list[str] = []
    for key, value in attributes.items():
        normalized_key = normalize(key).replace(" ", "_")
        if normalized_key not in keys or value in (None, "", [], {}):
            continue
        if isinstance(value, (str, int, float)):
            values.append(str(value))
    return values


def relation_keys(payload: dict[str, Any]) -> dict[str, str]:
    record_id = str(payload.get("id") or "")
    kind = str(payload.get("kind") or "")
    title = str(payload.get("title") or "")
    summary = str(payload.get("summary") or "")
    attributes = payload.get("attributes") or {}
    source = payload.get("source") or {}
    text = " ".join((title, summary, flatten(attributes)))
    keys: dict[str, str] = {}

    for match in CNPJ_RE.finditer(text):
        digits = "".join(match.groups())
        keys[f"cnpj:{digits}"] = f"mesmo CNPJ {digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"

    source_url = canonical_url(str(source.get("url") or ""))
    document_url = canonical_url(str(attributes.get("document_url") or attributes.get("pdf_url") or ""))
    for url in (source_url, document_url):
        if url:
            keys[f"url:{url}"] = "mesma fonte ou documento oficial"

    identifier_values = attr_values(attributes, IDENTIFIER_KEYS)
    for value in identifier_values:
        normalized = normalize(value).replace(" ", "")
        if normalized:
            keys[f"id:{normalized}"] = f"mesmo identificador {value.strip()}"

    procurement_context = kind in PROCUREMENT_KINDS or bool(PROCUREMENT_CONTEXT_RE.search(text))
    if procurement_context:
        for match in REF_RE.finditer(text):
            value = match.group(1).upper()
            keys[f"proc:{normalize(value).replace(' ', '')}"] = f"mesmo processo ou referência {value}"

    for match in LAW_RE.finditer(text):
        number, year = match.groups()
        value = f"{number}/{year}" if year else number
        keys[f"law:{value}"] = f"referência à mesma norma {value}"

    if kind == "lei":
        number = attributes.get("numero") or attributes.get("identifier")
        if number:
            value = str(number).strip()
            keys[f"law:{value}"] = f"mesma norma {value}"

    for supplier in attr_values(attributes, SUPPLIER_KEYS):
        normalized_supplier = normalize(supplier)
        if len(normalized_supplier) >= 5:
            keys[f"supplier:{normalized_supplier}"] = f"mesmo fornecedor: {supplier.strip()}"

    if not record_id:
        return {}
    return keys


def descriptor(payload: dict[str, Any], reason: str) -> dict[str, Any]:
    source = payload.get("source") or {}
    return {
        "id": payload.get("id"),
        "kind": payload.get("kind"),
        "title": payload.get("title"),
        "date": payload.get("date"),
        "year": payload.get("year"),
        "source_url": source.get("url"),
        "reason": reason,
    }


def compact_detail(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source") or {}
    attributes = payload.get("attributes") or {}
    return {
        "id": payload.get("id"),
        "kind": payload.get("kind"),
        "title": payload.get("title"),
        "summary": payload.get("summary"),
        "date": payload.get("date"),
        "year": payload.get("year"),
        "source": {
            "name": source.get("name"),
            "url": source.get("url"),
            "collected_at": source.get("collected_at"),
            "content_sha256": source.get("content_sha256"),
        },
        "attributes": sanitize(attributes),
    }


def procurement_identity(item: dict[str, Any]) -> str:
    attrs = item.get("attributes") or {}
    for key, value in attrs.items():
        normalized_key = normalize(key).replace(" ", "_")
        if normalized_key in PNCP_KEYS and value not in (None, ""):
            token = re.sub(r"\W+", "", normalize(str(value)))
            if token:
                return f"pncp:{token}"
    return f"record:{item.get('id')}"


def procurement_score(item: dict[str, Any]) -> int:
    attrs = item.get("attributes") or {}
    source = item.get("source") or {}
    meaningful = sum(value not in (None, "", [], {}) for value in attrs.values())
    documents = attrs.get("documentos") or []
    score = meaningful + (len(documents) * 3 if isinstance(documents, list) else 0)
    host = urlsplit(str(source.get("url") or "")).netloc.casefold()
    if "suzano.sp.gov.br" in host or "camarasuzano.sp.gov.br" in host:
        score += 5
    if item.get("summary"):
        score += 2
    return score


def merge_procurements(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[procurement_identity(item)].append(item)

    merged: list[dict[str, Any]] = []
    for group in grouped.values():
        ranked = sorted(group, key=procurement_score, reverse=True)
        base = copy.deepcopy(ranked[0])
        attrs = base.setdefault("attributes", {})
        sources: list[dict[str, str]] = []
        origin_ids: list[str] = []

        for candidate in ranked:
            origin_ids.append(str(candidate.get("id") or ""))
            source = candidate.get("source") or {}
            name = str(source.get("name") or "Fonte pública")
            url = str(source.get("url") or "")
            if url and not any(current["url"] == url for current in sources):
                sources.append({"name": name, "url": url})
            candidate_attrs = candidate.get("attributes") or {}
            for key, value in candidate_attrs.items():
                if attrs.get(key) in (None, "", [], {}) and value not in (None, "", [], {}):
                    attrs[key] = copy.deepcopy(value)
            for field in ("summary", "date", "year"):
                if base.get(field) in (None, "") and candidate.get(field) not in (None, ""):
                    base[field] = candidate[field]

        attrs["fontes_cruzadas"] = sources
        attrs["fontes_total"] = len(sources)
        attrs["registros_origem"] = [value for value in dict.fromkeys(origin_ids) if value]
        merged.append(base)

    merged.sort(
        key=lambda item: (str(item.get("date") or ""), str(item.get("id") or "")),
        reverse=True,
    )
    return merged


def build(database: Path, output: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        check = conn.execute("PRAGMA quick_check").fetchone()[0]
        if str(check).casefold() != "ok":
            raise RuntimeError(f"SQLite quick_check falhou: {check}")
        rows = conn.execute(
            """
            SELECT id, payload_json
            FROM records
            WHERE active=1
            """
        ).fetchall()
    finally:
        conn.close()

    payloads: dict[str, dict[str, Any]] = {}
    details: dict[str, dict[str, Any]] = {}
    key_members: dict[str, list[str]] = defaultdict(list)
    key_reasons: dict[tuple[str, str], str] = {}

    for row in rows:
        payload = json.loads(str(row["payload_json"]))
        record_id = str(payload.get("id") or row["id"])
        payload["id"] = record_id
        payloads[record_id] = payload
        if str(payload.get("kind") or "") in DETAIL_KINDS:
            details[record_id] = compact_detail(payload)
        for key, reason in relation_keys(payload).items():
            key_members[key].append(record_id)
            key_reasons[(record_id, key)] = reason

    related: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for key, members in key_members.items():
        unique = list(dict.fromkeys(members))
        if len(unique) < 2 or len(unique) > 100:
            continue
        for record_id in unique:
            reason = key_reasons.get((record_id, key), "relação por identificador público")
            for other_id in unique:
                if other_id == record_id:
                    continue
                other = payloads.get(other_id)
                if other is None:
                    continue
                current = related[record_id].get(other_id)
                candidate = descriptor(other, reason)
                if current is None:
                    related[record_id][other_id] = candidate

    relation_shards: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(dict)
    for record_id, values in related.items():
        items = list(values.values())
        items.sort(key=lambda item: (str(item.get("date") or ""), str(item.get("id") or "")), reverse=True)
        relation_shards[shard_for(record_id)][record_id] = items[:40]

    detail_shards: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for record_id, detail in details.items():
        detail["related_count"] = len(related.get(record_id, {}))
        detail_shards[shard_for(record_id)][record_id] = detail

    for shard in "0123456789abcdef":
        write_gzip(output / "details" / f"{shard}.json.gz", detail_shards.get(shard, {}))
        write_gzip(output / "relations" / f"{shard}.json.gz", relation_shards.get(shard, {}))

    raw_procurements = [
        details[record_id]
        for record_id in details
        if str(details[record_id].get("kind") or "") in PROCUREMENT_KINDS
    ]
    procurements = merge_procurements(raw_procurements)
    write_gzip(output / "contratacoes.json.gz", {"items": procurements})

    api_root = output.parent / "api" / "v1"
    write_gzip(api_root / "contratacoes.json.gz", {"items": procurements})
    relation_count = sum(len(values) for values in related.values())
    source_names = {
        str(item.get("source", {}).get("name") or "")
        for item in raw_procurements
        if item.get("source", {}).get("name")
    }
    summary = {
        "records": len(payloads),
        "details": len(details),
        "procurements": len(procurements),
        "procurements_raw": len(raw_procurements),
        "procurement_sources": len(source_names),
        "records_with_relations": len(related),
        "relation_edges": relation_count,
        "detail_shards": 16,
        "relation_shards": 16,
    }
    (output / "enrichment.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera detalhes, relações determinísticas e coleção de contratações para o portal."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("web/data"))
    args = parser.parse_args()
    print(json.dumps(build(args.database, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

CONTROL_RE = re.compile(r"^(\d{14})-(\d+)-(\d+)/(\d{4})(?:-(\d+))?$")
PROCUREMENT_KINDS = {"licitacao", "contrato", "ata"}


def _parse_control(value: Any) -> tuple[str, int, int, int, int | None] | None:
    match = CONTROL_RE.match(str(value or "").strip())
    if not match:
        return None
    cnpj, type_id, sequence, year, child = match.groups()
    return cnpj, int(type_id), int(sequence), int(year), int(child) if child else None


def _exact_pncp_url(value: Any) -> bool:
    try:
        parsed = urlsplit(str(value or "").strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or parsed.netloc.casefold() != "pncp.gov.br":
        return False
    path = parsed.path.rstrip("/")
    return bool(
        re.fullmatch(r"/app/(?:editais|contratos)/\d{14}/\d{4}/\d+", path)
        or re.fullmatch(r"/app/atas/\d{14}/\d{4}/\d+/\d+", path)
    )


def _looks_like_pncp(record: dict[str, Any]) -> bool:
    attrs = record.get("attributes") or {}
    source = record.get("source") or {}
    crossed = attrs.get("fontes_cruzadas") or []
    text = " ".join(
        [
            str(source.get("name") or ""),
            str(source.get("url") or ""),
            str(attrs.get("fonte_api") or ""),
            *(f"{item.get('name', '')} {item.get('url', '')}" for item in crossed if isinstance(item, dict)),
        ]
    ).casefold()
    return "pncp" in text or "pncp.gov.br" in text


def resolve_official_url(record: dict[str, Any]) -> tuple[str, str] | None:
    """Return (url, quality) where quality is exact, search or original."""
    kind = str(record.get("kind") or "")
    if kind not in PROCUREMENT_KINDS:
        return None

    attrs = record.get("attributes") or {}
    explicit = attrs.get("official_url") or attrs.get("portal_url")
    if _exact_pncp_url(explicit):
        return str(explicit), "exact"

    control = _parse_control(
        attrs.get("numero_controle_pncp")
        or attrs.get("numeroControlePNCP")
        or attrs.get("identifier")
    )
    if control:
        cnpj, type_id, sequence, year, child = control
        if kind == "licitacao" and type_id == 1:
            return f"https://pncp.gov.br/app/editais/{cnpj}/{year}/{sequence}", "exact"
        if kind == "contrato" and type_id == 2:
            return f"https://pncp.gov.br/app/contratos/{cnpj}/{year}/{sequence}", "exact"
        if kind == "ata" and type_id == 1 and child:
            return f"https://pncp.gov.br/app/atas/{cnpj}/{year}/{sequence}/{child}", "exact"

    if kind == "ata":
        purchase = _parse_control(
            attrs.get("numero_controle_pncp_compra") or attrs.get("numeroControlePNCPCompra")
        )
        ata_sequence = (
            attrs.get("sequencial_ata")
            or attrs.get("sequencialAta")
            or (control[2] if control and control[1] == 3 else None)
            or (control[4] if control else None)
        )
        try:
            ata_sequence_number = int(ata_sequence) if ata_sequence is not None else 0
        except (TypeError, ValueError):
            ata_sequence_number = 0
        if purchase and purchase[1] == 1 and ata_sequence_number > 0:
            cnpj, _, purchase_sequence, purchase_year, _ = purchase
            return (
                f"https://pncp.gov.br/app/atas/{cnpj}/{purchase_year}/{purchase_sequence}/{ata_sequence_number}",
                "exact",
            )

    if _looks_like_pncp(record):
        section = "atas" if kind == "ata" else "contratos" if kind == "contrato" else "editais"
        query = (
            attrs.get("numero_controle_pncp")
            or attrs.get("identifier")
            or attrs.get("numero")
            or record.get("title")
            or ""
        )
        return f"https://pncp.gov.br/app/{section}?q={quote(str(query))}", "search"

    source = record.get("source") or {}
    url = str(source.get("url") or attrs.get("portal_url") or "").strip()
    if url:
        return url, "original"
    return None


def enrich_record(record: dict[str, Any]) -> bool:
    resolved = resolve_official_url(record)
    if not resolved:
        return False
    url, quality = resolved
    attrs = record.setdefault("attributes", {})
    changed = attrs.get("official_url") != url or attrs.get("official_url_quality") != quality
    attrs["official_url"] = url
    attrs["official_url_quality"] = quality

    if _looks_like_pncp(record):
        source = record.setdefault("source", {})
        if quality == "exact" and source.get("url") != url:
            source["url"] = url
            changed = True
        crossed = attrs.get("fontes_cruzadas")
        if isinstance(crossed, list):
            for item in crossed:
                if not isinstance(item, dict):
                    continue
                text = f"{item.get('name', '')} {item.get('url', '')}".casefold()
                if "pncp" in text and item.get("url") != url:
                    item["url"] = url
                    changed = True
    return changed


def _read_gzip(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _write_gzip(path: Path, payload: Any) -> None:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))


def enrich_file(path: Path) -> tuple[int, int, int]:
    payload = _read_gzip(path)
    records: list[dict[str, Any]] = []
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        records = [item for item in payload["items"] if isinstance(item, dict)]
    elif isinstance(payload, dict):
        records = [item for item in payload.values() if isinstance(item, dict)]

    changed = 0
    exact = 0
    search = 0
    for record in records:
        if enrich_record(record):
            changed += 1
        quality = (record.get("attributes") or {}).get("official_url_quality")
        if quality == "exact":
            exact += 1
        elif quality == "search":
            search += 1
    _write_gzip(path, payload)
    return changed, exact, search


def enrich_portal(root: Path) -> dict[str, int]:
    files = [
        root / "data" / "contratacoes.json.gz",
        root / "api" / "v1" / "contratacoes.json.gz",
        *(root / "data" / "details" / f"{shard}.json.gz" for shard in "0123456789abcdef"),
    ]
    changed = exact = search = processed = 0
    for path in files:
        if not path.exists():
            continue
        file_changed, file_exact, file_search = enrich_file(path)
        changed += file_changed
        exact += file_exact
        search += file_search
        processed += 1
    return {"files": processed, "changed": changed, "exact": exact, "search": search}


def main() -> None:
    parser = argparse.ArgumentParser(description="Materializa links oficiais canônicos nas coleções públicas do portal.")
    parser.add_argument("--root", type=Path, default=Path("web"))
    args = parser.parse_args()
    result = enrich_portal(args.root)
    if result["files"] < 1:
        raise SystemExit("nenhum conjunto de dados do portal foi encontrado")
    if result["exact"] < 1:
        raise SystemExit("nenhum link oficial direto pôde ser materializado")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

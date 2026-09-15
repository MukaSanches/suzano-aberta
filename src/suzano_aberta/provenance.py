from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit

from .models import PublicRecord

PROV_CONTEXT = "https://www.w3.org/ns/prov.jsonld"
DCAT_CONTEXT = "https://www.w3.org/ns/dcat.jsonld"
PROJECT_URL = "https://github.com/MukaSanches/suzano-aberta"
PORTAL_URL = "https://mukasanches.github.io/suzano-aberta/"


def source_host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").casefold()
    except ValueError:
        return ""


def source_class(url: str) -> str:
    host = source_host(url)
    if host.endswith("suzano.sp.gov.br") or host.endswith("camarasuzano.sp.gov.br"):
        return "municipal_official"
    if host.endswith("pncp.gov.br") or host.endswith("compras.gov.br") or host.endswith("gov.br"):
        return "federal_official"
    if host.endswith("tce.sp.gov.br") or host.endswith("tcesp.gov.br"):
        return "oversight_official"
    if host.endswith("archive.org") or host.endswith("web.archive.org") or host.endswith("commoncrawl.org"):
        return "public_archive"
    return "public_web"


def record_provenance(record: PublicRecord) -> dict[str, Any]:
    entity_id = f"urn:suzano-aberta:record:{record.id}"
    source_url = record.source.url
    activity_id = f"urn:suzano-aberta:collection:{sha256((record.id + str(record.source.collected_at)).encode()).hexdigest()[:24]}"
    agent_id = f"urn:suzano-aberta:source:{sha256(source_host(source_url).encode()).hexdigest()[:20]}"

    entity: dict[str, Any] = {
        "@id": entity_id,
        "@type": "prov:Entity",
        "prov:label": record.title,
        "prov:wasDerivedFrom": {"@id": source_url},
        "prov:wasGeneratedBy": {"@id": activity_id},
        "suzano:recordKind": record.kind,
        "suzano:recordId": record.id,
        "suzano:fingerprint": record.fingerprint(),
    }
    if record.date:
        entity["suzano:recordDate"] = record.date
    if record.source.content_sha256:
        entity["suzano:sourceContentSha256"] = record.source.content_sha256

    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "dct": "http://purl.org/dc/terms/",
            "suzano": "https://mukasanches.github.io/suzano-aberta/ns#",
        },
        "record": record.id,
        "source_class": source_class(source_url),
        "entity": entity,
        "activity": {
            "@id": activity_id,
            "@type": "prov:Activity",
            "prov:endedAtTime": record.source.collected_at.astimezone(UTC).isoformat(),
            "prov:used": {"@id": source_url},
            "prov:wasAssociatedWith": {"@id": agent_id},
        },
        "agent": {
            "@id": agent_id,
            "@type": "prov:Agent",
            "prov:label": record.source.name,
            "suzano:host": source_host(source_url),
        },
        "source": {
            "url": source_url,
            "name": record.source.name,
            "collected_at": record.source.collected_at.astimezone(UTC).isoformat(),
            "content_sha256": record.source.content_sha256,
        },
    }


def dcat_catalog(*, stats: dict[str, object], distributions: list[dict[str, str]]) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "@context": {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dct": "http://purl.org/dc/terms/",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "prov": "http://www.w3.org/ns/prov#",
        },
        "@id": f"{PORTAL_URL}catalog",
        "@type": "dcat:Catalog",
        "dct:title": "Suzano Aberta",
        "dct:description": "Catálogo aberto de dados, documentos e publicações públicas relacionadas ao município de Suzano, SP.",
        "dct:modified": now,
        "dct:license": "https://www.apache.org/licenses/LICENSE-2.0",
        "foaf:homepage": {"@id": PORTAL_URL},
        "dcat:dataset": {
            "@id": f"{PORTAL_URL}dataset/acervo",
            "@type": "dcat:Dataset",
            "dct:title": "Acervo Suzano Aberta",
            "dct:description": "Índice rastreável e pesquisável de registros públicos coletados de fontes oficiais e públicas.",
            "dct:publisher": {"@id": PROJECT_URL},
            "dct:spatial": "Suzano, São Paulo, Brasil",
            "suzano:records": stats.get("records", 0),
            "suzano:documents": stats.get("documents", 0),
            "suzano:legislation": stats.get("legislation", 0),
            "dcat:distribution": distributions,
        },
    }

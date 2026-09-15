from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote, unquote, urlencode, urlsplit

from .discovery import normalize_url
from .http import PoliteHttpClient
from .models import PublicRecord, SourceRef


OFFICIAL_ARCHIVE_DOMAINS = (
    "suzano.sp.gov.br",
    "www.suzano.sp.gov.br",
    "camarasuzano.sp.gov.br",
    "www.camarasuzano.sp.gov.br",
)

DOCUMENT_SUFFIXES = {
    ".7z",
    ".csv",
    ".doc",
    ".docx",
    ".json",
    ".odt",
    ".ods",
    ".pdf",
    ".ppt",
    ".pptx",
    ".rar",
    ".rtf",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}


@dataclass(slots=True)
class ArchiveStats:
    indexed: int = 0
    failed: int = 0
    common_crawl: int = 0
    wayback: int = 0
    internet_archive: int = 0


def _record_id(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return f"hist:{digest}"


def _title_from_url(url: str) -> str:
    path = unquote(urlsplit(url).path).rstrip("/")
    name = PurePosixPath(path).name if path else ""
    return name or url


def _year_from_timestamp(timestamp: str | None) -> int | None:
    if not timestamp or len(timestamp) < 4:
        return None
    prefix = timestamp[:4]
    return int(prefix) if prefix.isdigit() else None


def _looks_like_document(url: str, mime: str = "") -> bool:
    suffix = PurePosixPath(unquote(urlsplit(url).path)).suffix.casefold()
    if suffix in DOCUMENT_SUFFIXES:
        return True
    lowered = mime.casefold()
    return any(
        marker in lowered
        for marker in (
            "application/pdf",
            "application/msword",
            "officedocument",
            "spreadsheet",
            "presentation",
            "text/csv",
            "application/zip",
        )
    )


class ArchiveDiscovery:
    """Descobre URLs e arquivos históricos em índices públicos de preservação da web."""

    def __init__(self, http: PoliteHttpClient) -> None:
        self.http = http
        self.stats = ArchiveStats()

    def discover(
        self,
        *,
        max_records: int = 50_000,
        common_crawl_collections: int = 8,
        include_wayback: bool = True,
        include_internet_archive: bool = True,
    ) -> list[PublicRecord]:
        if max_records <= 0:
            return []
        records: dict[str, PublicRecord] = {}

        try:
            self._common_crawl(
                records,
                max_records=max_records,
                collections=max(1, common_crawl_collections),
            )
        except Exception:
            self.stats.failed += 1

        if include_wayback and len(records) < max_records:
            try:
                self._wayback(records, max_records=max_records)
            except Exception:
                self.stats.failed += 1

        if include_internet_archive and len(records) < max_records:
            try:
                self._internet_archive(records, max_records=max_records)
            except Exception:
                self.stats.failed += 1

        self.stats.indexed = len(records)
        return list(records.values())

    def _common_crawl(
        self,
        records: dict[str, PublicRecord],
        *,
        max_records: int,
        collections: int,
    ) -> None:
        result = self.http.get("https://index.commoncrawl.org/collinfo.json", attempts=2)
        payload: Any = json.loads(result.text)
        if not isinstance(payload, list):
            return
        collection_ids = [
            str(item.get("id"))
            for item in payload
            if isinstance(item, dict) and item.get("id")
        ][:collections]

        for collection_id in collection_ids:
            if len(records) >= max_records:
                break
            for domain in OFFICIAL_ARCHIVE_DOMAINS:
                if len(records) >= max_records:
                    break
                query = urlencode(
                    {
                        "url": f"{domain}/*",
                        "output": "json",
                        "filter": "status:200",
                        "collapse": "urlkey",
                    }
                )
                endpoint = f"https://index.commoncrawl.org/{quote(collection_id, safe='')}-index?{query}"
                try:
                    response = self.http.get(endpoint, attempts=2)
                except Exception:
                    self.stats.failed += 1
                    continue
                for line in response.text.splitlines():
                    if len(records) >= max_records:
                        return
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item: Any = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(item, dict):
                        continue
                    original = str(item.get("url") or "").strip()
                    normalized = normalize_url(original)
                    if normalized is None:
                        continue
                    mime = str(item.get("mime") or "")
                    timestamp = str(item.get("timestamp") or "") or None
                    key = _record_id(normalized)
                    record = PublicRecord(
                        id=key,
                        kind="arquivo_historico",
                        title=_title_from_url(normalized),
                        summary="URL pública preservada no índice Common Crawl para os domínios oficiais de Suzano.",
                        date=timestamp,
                        year=_year_from_timestamp(timestamp),
                        attributes={
                            "url_original": normalized,
                            "arquivo": _looks_like_document(normalized, mime),
                            "mime": mime,
                            "captura": timestamp,
                            "indice": collection_id,
                            "digest": item.get("digest"),
                            "tamanho": item.get("length"),
                            "warc": item.get("filename"),
                            "offset": item.get("offset"),
                            "origem_catalogo": "common-crawl",
                        },
                        source=SourceRef(
                            name=f"Common Crawl — {collection_id}",
                            url=normalized,
                            content_sha256=str(item.get("digest")) if item.get("digest") else None,
                        ),
                    )
                    records[key] = record
                    self.stats.common_crawl += 1

    def _wayback(self, records: dict[str, PublicRecord], *, max_records: int) -> None:
        for domain in OFFICIAL_ARCHIVE_DOMAINS:
            if len(records) >= max_records:
                return
            remaining = max_records - len(records)
            query = urlencode(
                {
                    "url": f"{domain}/*",
                    "output": "json",
                    "fl": "timestamp,original,mimetype,digest,statuscode,length",
                    "filter": "statuscode:200",
                    "collapse": "urlkey",
                    "limit": str(min(remaining, 20_000)),
                }
            )
            endpoint = f"https://web.archive.org/cdx/search/cdx?{query}"
            try:
                response = self.http.get(endpoint, attempts=2)
                payload: Any = json.loads(response.text)
            except Exception:
                self.stats.failed += 1
                continue
            if not isinstance(payload, list) or len(payload) < 2:
                continue
            header = payload[0]
            if not isinstance(header, list):
                continue
            columns = [str(item) for item in header]
            for raw in payload[1:]:
                if len(records) >= max_records:
                    return
                if not isinstance(raw, list):
                    continue
                values = {columns[index]: value for index, value in enumerate(raw) if index < len(columns)}
                original = str(values.get("original") or "").strip()
                normalized = normalize_url(original)
                if normalized is None:
                    continue
                timestamp = str(values.get("timestamp") or "") or None
                mime = str(values.get("mimetype") or "")
                snapshot_url = (
                    f"https://web.archive.org/web/{timestamp}id_/{normalized}"
                    if timestamp
                    else normalized
                )
                key = _record_id(normalized)
                records[key] = PublicRecord(
                    id=key,
                    kind="arquivo_historico",
                    title=_title_from_url(normalized),
                    summary="Recurso dos domínios oficiais de Suzano preservado pelo Internet Archive.",
                    date=timestamp,
                    year=_year_from_timestamp(timestamp),
                    attributes={
                        "url_original": normalized,
                        "url_preservada": snapshot_url,
                        "arquivo": _looks_like_document(normalized, mime),
                        "mime": mime,
                        "captura": timestamp,
                        "digest": values.get("digest"),
                        "tamanho": values.get("length"),
                        "origem_catalogo": "wayback-cdx",
                    },
                    source=SourceRef(name="Internet Archive — Wayback Machine", url=snapshot_url),
                )
                self.stats.wayback += 1

    def _internet_archive(self, records: dict[str, PublicRecord], *, max_records: int) -> None:
        remaining = min(max_records - len(records), 2_000)
        if remaining <= 0:
            return
        query = 'Suzano AND ("São Paulo" OR prefeitura OR município OR camara OR câmara)'
        params = [
            ("q", query),
            ("fl[]", "identifier"),
            ("fl[]", "title"),
            ("fl[]", "description"),
            ("fl[]", "date"),
            ("fl[]", "year"),
            ("fl[]", "mediatype"),
            ("rows", str(remaining)),
            ("page", "1"),
            ("output", "json"),
        ]
        endpoint = "https://archive.org/advancedsearch.php?" + urlencode(params)
        result = self.http.get(endpoint, attempts=2)
        payload: Any = json.loads(result.text)
        if not isinstance(payload, dict):
            return
        response = payload.get("response")
        if not isinstance(response, dict):
            return
        docs = response.get("docs")
        if not isinstance(docs, list):
            return
        for item in docs:
            if len(records) >= max_records:
                return
            if not isinstance(item, dict):
                continue
            identifier = str(item.get("identifier") or "").strip()
            if not identifier:
                continue
            details_url = f"https://archive.org/details/{quote(identifier, safe='') }"
            title = str(item.get("title") or identifier)
            date = str(item.get("date") or item.get("year") or "") or None
            year = _year_from_timestamp(date)
            key = _record_id(details_url)
            records[key] = PublicRecord(
                id=key,
                kind="arquivo_historico",
                title=title[:500],
                summary=str(item.get("description") or "Item público relacionado a Suzano no Internet Archive.")[:1200],
                date=date,
                year=year,
                attributes={
                    "identifier": identifier,
                    "mediatype": item.get("mediatype"),
                    "origem_catalogo": "archive.org-advanced-search",
                    "consulta": query,
                },
                source=SourceRef(name="Internet Archive", url=details_url),
            )
            self.stats.internet_archive += 1

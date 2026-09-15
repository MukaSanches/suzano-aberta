from __future__ import annotations

import hashlib
import re
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, quote_plus, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from bs4.element import Tag

from .documents import document_suffix, extract_document_text
from .http import DEFAULT_USER_AGENT, HttpResult, PoliteHttpClient
from .models import PublicRecord, SourceRef


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
    ".tar",
    ".tgz",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}

ASSET_SUFFIXES = {
    ".avi",
    ".bmp",
    ".css",
    ".eot",
    ".exe",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".m4a",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".ogg",
    ".otf",
    ".png",
    ".svg",
    ".ttf",
    ".wav",
    ".webp",
    ".woff",
    ".woff2",
}

DEFAULT_NEWS_QUERIES = (
    "Suzano SP",
    '"Prefeitura de Suzano"',
    '"Câmara de Suzano"',
    "Suzano licitação",
    "Suzano contrato",
    "Suzano saúde",
    "Suzano educação",
    "Suzano obras",
    "Suzano concurso público",
    "Suzano orçamento",
    "Suzano diário oficial",
    "Suzano transporte",
    "Suzano meio ambiente",
)


@dataclass(slots=True)
class DiscoveryStats:
    fetched: int = 0
    indexed: int = 0
    skipped: int = 0
    failed: int = 0
    documents_seen: int = 0
    documents_fetched: int = 0


@dataclass(frozen=True, slots=True)
class DocumentLink:
    url: str
    label: str | None
    discovered_from: str | None
    depth: int


def normalize_url(url: str) -> str | None:
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return None
    host = parts.netloc.casefold()
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}
    ]
    query = urlencode(query_items, doseq=True)
    return urlunsplit((parts.scheme.lower(), host, path, query, ""))


def _host_key(host: str) -> str:
    value = host.casefold().split(":", 1)[0]
    return value.removeprefix("www.")


def _suffix(url: str) -> str:
    return PurePosixPath(unquote(urlsplit(url).path)).suffix.casefold()


def _is_document_candidate(url: str) -> bool:
    return _suffix(url) in DOCUMENT_SUFFIXES


def _is_asset(url: str) -> bool:
    return _suffix(url) in ASSET_SUFFIXES


def _content_is_document(content_type: str, url: str) -> bool:
    if _is_document_candidate(url):
        return True
    lowered = content_type.casefold()
    return any(
        marker in lowered
        for marker in (
            "application/pdf",
            "application/msword",
            "officedocument",
            "spreadsheet",
            "presentation",
            "text/csv",
            "application/json",
            "application/xml",
            "text/plain",
            "application/zip",
        )
    )


def _record_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}:{digest}"


def _document_title(url: str, label: str | None) -> str:
    clean_label = " ".join((label or "").split())
    if clean_label and len(clean_label) >= 3:
        return clean_label[:500]
    path = unquote(urlsplit(url).path).rstrip("/")
    name = PurePosixPath(path).name
    return name or url


class WebDiscovery:
    """Descobre páginas e documentos públicos sem depender de catálogo manual exaustivo."""

    def __init__(self, http: PoliteHttpClient) -> None:
        self.http = http
        self.stats = DiscoveryStats()
        self._robots: dict[str, RobotFileParser | None] = {}
        self._sitemaps_seen: set[str] = set()

    def discover(
        self,
        seed_urls: Iterable[str],
        *,
        max_pages: int = 500,
        max_depth: int = 3,
        max_documents: int = 250,
        max_document_bytes: int = 20_000_000,
        document_text_chars: int = 500_000,
        allowed_hosts: Iterable[str] | None = None,
        include_sitemaps: bool = True,
    ) -> list[PublicRecord]:
        seeds = [url for item in seed_urls if (url := normalize_url(item)) is not None]
        if not seeds or max_pages <= 0:
            return []

        hosts = {_host_key(urlsplit(url).netloc) for url in seeds}
        if allowed_hosts is not None:
            hosts.update(_host_key(item) for item in allowed_hosts)

        frontier: deque[tuple[str, int, str | None]] = deque(
            (url, 0, None) for url in dict.fromkeys(seeds)
        )
        document_queue: deque[DocumentLink] = deque()
        document_seen: set[str] = set()

        if include_sitemaps:
            for origin in dict.fromkeys(self._origin(url) for url in seeds):
                for url in self._sitemap_candidates(origin, max_urls=max_pages * 8):
                    if not self._host_allowed(url, hosts):
                        continue
                    if _is_document_candidate(url):
                        if url not in document_seen:
                            document_seen.add(url)
                            document_queue.append(DocumentLink(url, None, origin, 0))
                    elif not _is_asset(url):
                        frontier.append((url, 0, origin))

        records: dict[str, PublicRecord] = {}
        seen: set[str] = set()
        while frontier and self.stats.fetched < max_pages:
            url, depth, discovered_from = frontier.popleft()
            if url in seen:
                continue
            seen.add(url)
            if not self._host_allowed(url, hosts):
                self.stats.skipped += 1
                continue
            if _is_document_candidate(url):
                if url not in document_seen:
                    document_seen.add(url)
                    document_queue.append(DocumentLink(url, None, discovered_from, depth))
                continue
            if _is_asset(url):
                self.stats.skipped += 1
                continue
            if not self._robots_allowed(url):
                self.stats.skipped += 1
                continue

            try:
                result = self.http.get(url, attempts=2)
            except Exception:
                self.stats.failed += 1
                continue
            self.stats.fetched += 1

            content_type = result.content_type.casefold()
            final_url = normalize_url(result.url) or url
            is_html = "html" in content_type or result.text.lstrip().lower().startswith(
                ("<!doctype html", "<html")
            )
            if not is_html:
                if _content_is_document(result.content_type, final_url):
                    record = self._document_record(
                        DocumentLink(final_url, None, discovered_from, depth),
                        result=result,
                        max_document_bytes=max_document_bytes,
                        document_text_chars=document_text_chars,
                    )
                    records[record.id] = record
                    self.stats.documents_seen += 1
                    self.stats.documents_fetched += 1
                    self.stats.indexed += 1
                else:
                    self.stats.skipped += 1
                continue

            soup = BeautifulSoup(result.text, "html.parser")
            for node in soup(["script", "style", "noscript", "template"]):
                node.decompose()

            text = " ".join(soup.get_text(" ", strip=True).split())
            if len(text) < 40:
                self.stats.skipped += 1
                continue

            title = self._title(soup, final_url)
            date, year = self._date(soup)
            page_links, document_links = self._links(soup, final_url, hosts, depth=depth)
            content_sha = hashlib.sha256(result.content).hexdigest()
            record = PublicRecord(
                id=_record_id("web", final_url),
                kind="pagina_web",
                title=title,
                summary=text[:1200],
                date=date,
                year=year,
                attributes={
                    "texto": text[:100_000],
                    "url_canonica": final_url,
                    "descoberta_de": discovered_from,
                    "profundidade": depth,
                    "links_descobertos": len(page_links) + len(document_links),
                    "arquivos_descobertos": len(document_links),
                    "content_type": result.content_type,
                },
                source=SourceRef(
                    name=f"Web pública — {urlsplit(final_url).netloc}",
                    url=final_url,
                    content_sha256=content_sha,
                ),
            )
            records[record.id] = record
            self.stats.indexed += 1

            for item in document_links:
                if item.url in document_seen:
                    continue
                document_seen.add(item.url)
                document_queue.append(item)
                metadata = self._document_record(item)
                records[metadata.id] = metadata
                self.stats.documents_seen += 1
                self.stats.indexed += 1

            if depth < max_depth:
                for link in page_links:
                    if link not in seen:
                        frontier.append((link, depth + 1, final_url))

        downloaded: set[str] = set()
        while document_queue and len(downloaded) < max_documents:
            item = document_queue.popleft()
            if item.url in downloaded:
                continue
            downloaded.add(item.url)
            if not self._robots_allowed(item.url):
                continue
            try:
                result = self.http.get(item.url, attempts=2)
            except Exception:
                self.stats.failed += 1
                continue
            record = self._document_record(
                item,
                result=result,
                max_document_bytes=max_document_bytes,
                document_text_chars=document_text_chars,
            )
            records[record.id] = record
            self.stats.documents_fetched += 1

        return list(records.values())

    def discover_news(
        self,
        queries: Iterable[str] = DEFAULT_NEWS_QUERIES,
        *,
        per_query: int = 100,
    ) -> list[PublicRecord]:
        """Indexa menções recentes da web via o feed público do Google News."""
        records: dict[str, PublicRecord] = {}
        for query in queries:
            feed_url = (
                "https://news.google.com/rss/search?q="
                f"{quote_plus(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            )
            try:
                result = self.http.get(feed_url, attempts=2)
                root = ElementTree.fromstring(result.content)
            except Exception:
                self.stats.failed += 1
                continue

            for item in root.findall(".//item")[:per_query]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                if not title or not link:
                    continue
                published_raw = (item.findtext("pubDate") or "").strip()
                published = None
                year = None
                if published_raw:
                    try:
                        parsed = parsedate_to_datetime(published_raw)
                        published = parsed.isoformat()
                        year = parsed.year
                    except (TypeError, ValueError, OverflowError):
                        published = published_raw
                source_node = item.find("source")
                publisher = (
                    (source_node.text or "Google News").strip()
                    if source_node is not None
                    else "Google News"
                )
                key = normalize_url(link) or link
                record = PublicRecord(
                    id=_record_id("news-web", key),
                    kind="pagina_web",
                    title=title,
                    summary=f"Menção pública encontrada para a consulta: {query}",
                    date=published,
                    year=year,
                    attributes={
                        "consulta_descoberta": query,
                        "publicador": publisher,
                        "tipo_descoberta": "google-news-rss",
                    },
                    source=SourceRef(name=publisher, url=link),
                )
                records[record.id] = record
        return list(records.values())

    def _document_record(
        self,
        item: DocumentLink,
        *,
        result: HttpResult | None = None,
        max_document_bytes: int = 20_000_000,
        document_text_chars: int = 500_000,
    ) -> PublicRecord:
        final_url = normalize_url(result.url) if result is not None else None
        resolved_url = final_url or item.url
        attributes: dict[str, object] = {
            "url_canonica": resolved_url,
            "descoberta_de": item.discovered_from,
            "profundidade": item.depth,
            "formato": document_suffix(resolved_url) or None,
            "texto_extraido": False,
        }
        content_hash: str | None = None
        summary = "Arquivo público descoberto e catalogado para pesquisa no acervo de Suzano."
        if result is not None:
            content_hash = hashlib.sha256(result.content).hexdigest()
            attributes["content_type"] = result.content_type
            attributes["tamanho_bytes"] = len(result.content)
            if len(result.content) <= max_document_bytes:
                try:
                    text = extract_document_text(
                        result.content,
                        resolved_url,
                        content_type=result.content_type,
                        max_chars=document_text_chars,
                    )
                except Exception:
                    text = None
                if text:
                    attributes["texto"] = text
                    attributes["texto_extraido"] = True
                    summary = text[:1200]
            else:
                attributes["extracao_omitida"] = "arquivo acima do limite de bytes por item"

        return PublicRecord(
            id=_record_id("file", resolved_url),
            kind="arquivo",
            title=_document_title(resolved_url, item.label),
            summary=summary,
            attributes=attributes,
            source=SourceRef(
                name=f"Arquivo público — {urlsplit(resolved_url).netloc}",
                url=resolved_url,
                content_sha256=content_hash,
            ),
        )

    def _origin(self, url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}"

    def _host_allowed(self, url: str, hosts: set[str]) -> bool:
        return _host_key(urlsplit(url).netloc) in hosts

    def _robots_allowed(self, url: str) -> bool:
        origin = self._origin(url)
        if origin not in self._robots:
            robots_url = f"{origin}/robots.txt"
            parser = RobotFileParser()
            try:
                result = self.http.get(robots_url, attempts=1)
                parser.set_url(robots_url)
                parser.parse(result.text.splitlines())
                self._robots[origin] = parser
            except Exception:
                self._robots[origin] = None
        cached_parser = self._robots[origin]
        return True if cached_parser is None else cached_parser.can_fetch(DEFAULT_USER_AGENT, url)

    def _sitemap_candidates(self, origin: str, *, max_urls: int) -> list[str]:
        candidates: list[str] = []
        sitemap_urls: list[str] = []
        robots_url = f"{origin}/robots.txt"
        try:
            result = self.http.get(robots_url, attempts=1)
            for line in result.text.splitlines():
                if line.casefold().startswith("sitemap:"):
                    value = line.split(":", 1)[1].strip()
                    if value:
                        sitemap_urls.append(value)
        except Exception:
            pass
        if not sitemap_urls:
            sitemap_urls.append(f"{origin}/sitemap.xml")

        queue = deque(sitemap_urls[:20])
        while queue and len(candidates) < max_urls:
            sitemap_url = queue.popleft()
            if sitemap_url in self._sitemaps_seen:
                continue
            self._sitemaps_seen.add(sitemap_url)
            try:
                result = self.http.get(sitemap_url, attempts=1)
                root = ElementTree.fromstring(result.content)
            except Exception:
                continue

            tag = root.tag.rsplit("}", 1)[-1].casefold()
            locations = [
                (node.text or "").strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1].casefold() == "loc" and node.text
            ]
            if tag == "sitemapindex":
                queue.extend(locations[:100])
                continue
            for location in locations:
                normalized = normalize_url(location)
                if normalized is not None:
                    candidates.append(normalized)
                    if len(candidates) >= max_urls:
                        break
        return candidates

    def _title(self, soup: BeautifulSoup, url: str) -> str:
        h1 = soup.find("h1")
        if h1 is not None:
            value = " ".join(h1.get_text(" ", strip=True).split())
            if value:
                return value[:500]
        title = soup.find("title")
        if title is not None:
            value = " ".join(title.get_text(" ", strip=True).split())
            if value:
                return value[:500]
        return url

    def _date(self, soup: BeautifulSoup) -> tuple[str | None, int | None]:
        node = soup.find("time")
        if not isinstance(node, Tag):
            return None, None
        value = str(node.get("datetime") or node.get_text(" ", strip=True)).strip()
        match = re.search(r"\b(19|20)\d{2}\b", value)
        return value or None, int(match.group(0)) if match else None

    def _links(
        self,
        soup: BeautifulSoup,
        base_url: str,
        hosts: set[str],
        *,
        depth: int,
    ) -> tuple[list[str], list[DocumentLink]]:
        page_links: list[str] = []
        documents: list[DocumentLink] = []
        for anchor in soup.find_all("a", href=True):
            if not isinstance(anchor, Tag):
                continue
            href = str(anchor.get("href") or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            normalized = normalize_url(urljoin(base_url, href))
            if normalized is None or not self._host_allowed(normalized, hosts):
                continue
            if _is_document_candidate(normalized):
                label = " ".join(anchor.get_text(" ", strip=True).split()) or None
                documents.append(DocumentLink(normalized, label, base_url, depth + 1))
                continue
            if _is_asset(normalized):
                continue
            page_links.append(normalized)

        unique_pages = list(dict.fromkeys(page_links))
        unique_documents: dict[str, DocumentLink] = {}
        for item in documents:
            unique_documents.setdefault(item.url, item)
        return unique_pages, list(unique_documents.values())

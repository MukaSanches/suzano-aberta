from __future__ import annotations

import hashlib
import re
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from .http import DEFAULT_USER_AGENT, PoliteHttpClient
from .models import PublicRecord, SourceRef


SKIP_SUFFIXES = {
    ".7z",
    ".avi",
    ".bmp",
    ".css",
    ".doc",
    ".docx",
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
    ".ppt",
    ".pptx",
    ".rar",
    ".svg",
    ".tar",
    ".tgz",
    ".ttf",
    ".wav",
    ".webp",
    ".woff",
    ".woff2",
    ".xls",
    ".xlsx",
    ".zip",
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
)


@dataclass(slots=True)
class DiscoveryStats:
    fetched: int = 0
    indexed: int = 0
    skipped: int = 0
    failed: int = 0


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


def _is_html_candidate(url: str) -> bool:
    path = urlsplit(url).path.casefold()
    return not any(path.endswith(suffix) for suffix in SKIP_SUFFIXES)


def _record_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}:{digest}"


class WebDiscovery:
    """Descobre e indexa páginas públicas sem depender de um catálogo manual exaustivo."""

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
        if include_sitemaps:
            for origin in dict.fromkeys(self._origin(url) for url in seeds):
                for url in self._sitemap_candidates(origin, max_urls=max_pages * 4):
                    if self._host_allowed(url, hosts):
                        frontier.append((url, 0, origin))

        records: dict[str, PublicRecord] = {}
        seen: set[str] = set()
        while frontier and self.stats.fetched < max_pages:
            url, depth, discovered_from = frontier.popleft()
            if url in seen:
                continue
            seen.add(url)
            if not self._host_allowed(url, hosts) or not _is_html_candidate(url):
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
            if "html" not in content_type and not result.text.lstrip().lower().startswith(
                ("<!doctype html", "<html")
            ):
                self.stats.skipped += 1
                continue

            soup = BeautifulSoup(result.text, "html.parser")
            for node in soup(["script", "style", "noscript", "template"]):
                node.decompose()

            text = " ".join(soup.get_text(" ", strip=True).split())
            if len(text) < 40:
                self.stats.skipped += 1
                continue

            final_url = normalize_url(result.url) or url
            title = self._title(soup, final_url)
            date, year = self._date(soup)
            links = self._links(soup, final_url, hosts)
            content_sha = hashlib.sha256(result.content).hexdigest()
            record = PublicRecord(
                id=_record_id("web", final_url),
                kind="pagina_web",
                title=title,
                summary=text[:1200],
                date=date,
                year=year,
                attributes={
                    "texto": text[:60000],
                    "url_canonica": final_url,
                    "descoberta_de": discovered_from,
                    "profundidade": depth,
                    "links_descobertos": len(links),
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

            if depth < max_depth:
                for link in links:
                    if link not in seen:
                        frontier.append((link, depth + 1, final_url))

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
        parser = self._robots[origin]
        return True if parser is None else parser.can_fetch(DEFAULT_USER_AGENT, url)

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

        queue = deque(sitemap_urls[:10])
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
                queue.extend(locations[:50])
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
        if node is None:
            return None, None
        value = str(node.get("datetime") or node.get_text(" ", strip=True)).strip()
        match = re.search(r"\b(19|20)\d{2}\b", value)
        return value or None, int(match.group(0)) if match else None

    def _links(self, soup: BeautifulSoup, base_url: str, hosts: set[str]) -> list[str]:
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            normalized = normalize_url(urljoin(base_url, href))
            if normalized is None or not self._host_allowed(normalized, hosts):
                continue
            if not _is_html_candidate(normalized):
                continue
            links.append(normalized)
        return list(dict.fromkeys(links))

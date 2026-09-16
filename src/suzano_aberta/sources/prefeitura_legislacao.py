from __future__ import annotations

import re
import unicodedata
from hashlib import sha256
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from ..models import PublicRecord, RecordKind, SourceRef
from ..parsing import clean_text, parse_br_date
from .base import BaseSource, SourceDefinition


ROOT = "https://suzano.sp.gov.br/leis-e-decretos/"
SOURCE_NAME = "Leis, Decretos e Resoluções — Prefeitura de Suzano"

_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_ACT_RE = re.compile(
    r"\b(lei\s+complementar|lei|decreto|resolu[cç][aã]o)\s*"
    r"(?:n\s*[º°o.]?\s*)?([0-9][0-9.]*)\b",
    re.I,
)
_LONG_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+de\s+"
    r"(janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
    r"\s+de\s+(\d{4})\b",
    re.I,
)


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _long_date(value: str) -> str | None:
    folded = _fold(value)
    match = _LONG_DATE_RE.search(folded)
    if match is None:
        return None
    day = int(match.group(1))
    month = _MONTHS.get(match.group(2).replace("ç", "c"))
    year = int(match.group(3))
    if month is None:
        return None
    try:
        from datetime import date

        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _page_url(page: int) -> str:
    return ROOT if page <= 1 else urljoin(ROOT, f"page/{page}/")


class PrefeituraLegislationSource(BaseSource):
    """Atos publicados na coleção oficial atual da Prefeitura de Suzano.

    A Câmara continua sendo a fonte consolidada histórica das leis municipais.
    Este adaptador complementa o acervo com a publicação contemporânea da
    Prefeitura, em especial decretos e atos ainda não refletidos no índice
    consolidado da Câmara.
    """

    definition = SourceDefinition(
        key="prefeitura_legislacao",
        name=SOURCE_NAME,
        url=ROOT,
        authority="Poder Executivo municipal",
        category="executivo",
        notes=(
            "Coleção oficial de Leis, Decretos e Resoluções da Prefeitura de Suzano. "
            "Cada registro preserva a página oficial do ato e, quando disponível, "
            "o texto publicado e o documento anexado."
        ),
    )

    def collect(self, *, year: int) -> list[PublicRecord]:
        return self.collect_range(from_year=year, to_year=year)

    def collect_range(
        self,
        *,
        from_year: int,
        to_year: int,
        max_pages: int = 80,
        max_records: int = 1200,
    ) -> list[PublicRecord]:
        if from_year > to_year:
            raise ValueError("from_year não pode ser posterior a to_year")

        records: dict[str, PublicRecord] = {}
        seen_urls: set[str] = set()
        oldest_seen: int | None = None

        for page_number in range(1, max_pages + 1):
            listing_url = _page_url(page_number)
            page = self.http.get(listing_url)
            soup = BeautifulSoup(page.text, "html.parser")
            candidates = self._listing_candidates(soup, listing_url)
            if not candidates:
                break

            page_years: list[int] = []
            page_added = 0
            for detail_url, listing_title, listing_context in candidates:
                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)
                record = self._detail_record(
                    detail_url=detail_url,
                    listing_title=listing_title,
                    listing_context=listing_context,
                )
                if record is None:
                    continue
                if record.year is not None:
                    page_years.append(record.year)
                    oldest_seen = record.year if oldest_seen is None else min(oldest_seen, record.year)
                if record.year is None or not (from_year <= record.year <= to_year):
                    continue
                records[record.id] = record
                page_added += 1
                if len(records) >= max_records:
                    return self._sorted(records.values())

            # A listagem oficial é cronológica. Depois que uma página inteira já
            # está abaixo da faixa desejada, páginas seguintes não podem voltar a
            # conter atos mais novos.
            if page_years and max(page_years) < from_year and page_added == 0:
                break
            if oldest_seen is not None and oldest_seen < from_year - 1 and page_added == 0:
                break

        return self._sorted(records.values())

    @staticmethod
    def _listing_candidates(soup: BeautifulSoup, listing_url: str) -> list[tuple[str, str, str]]:
        candidates: list[tuple[str, str, str]] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", "")).strip()
            url = urljoin(listing_url, href)
            parsed = urlsplit(url)
            if parsed.hostname not in {"suzano.sp.gov.br", "www.suzano.sp.gov.br"}:
                continue
            path = parsed.path.rstrip("/") + "/"
            if "/leis-e-decretos/" not in path:
                continue
            if path.rstrip("/") == urlsplit(ROOT).path.rstrip("/"):
                continue
            if re.search(r"/leis-e-decretos/page/\d+/?$", path, re.I):
                continue
            if url in seen:
                continue

            title = clean_text(anchor.get_text(" ", strip=True))
            container = anchor.find_parent(["article", "li", "div"])
            context = clean_text(container.get_text(" ", strip=True) if isinstance(container, Tag) else title)
            signal = clean_text(f"{title} {context}")
            if _ACT_RE.search(signal) is None:
                continue
            seen.add(url)
            candidates.append((url, title, context))
        return candidates

    def _detail_record(
        self,
        *,
        detail_url: str,
        listing_title: str,
        listing_context: str,
    ) -> PublicRecord | None:
        try:
            page = self.http.get(detail_url)
            soup = BeautifulSoup(page.text, "html.parser")
        except Exception:
            soup = BeautifulSoup("", "html.parser")

        heading = ""
        for selector in ("h1", "article h2", ".entry-title", ".elementor-heading-title"):
            node = soup.select_one(selector)
            if node is None:
                continue
            candidate = clean_text(node.get_text(" ", strip=True))
            if _ACT_RE.search(candidate):
                heading = candidate
                break
        title = heading or listing_title

        body = self._main_text(soup)
        combined = clean_text(f"{title} {listing_context} {body}")
        act = _ACT_RE.search(combined)
        if act is None:
            return None

        raw_type = _fold(act.group(1))
        number_display = act.group(2).strip(".")
        number_key = re.sub(r"\D", "", number_display) or sha256(detail_url.encode()).hexdigest()[:10]
        if raw_type.startswith("lei complementar"):
            kind: RecordKind = "lei"
            norm_type = "lei complementar"
        elif raw_type == "lei":
            kind = "lei"
            norm_type = "lei"
        elif raw_type == "decreto":
            kind = "decreto"
            norm_type = "decreto"
        else:
            kind = "ato_oficial"
            norm_type = "resolução"

        date = _long_date(combined) or parse_br_date(combined)
        published = _long_date(listing_context) or parse_br_date(listing_context)
        year: int | None = None
        if date:
            year = int(date[:4])
        elif published:
            year = int(published[:4])
        else:
            year_match = re.search(r"\b(20\d{2})\b", combined)
            if year_match:
                year = int(year_match.group(1))

        effective_date = date or published
        if effective_date and year is None:
            year = int(effective_date[:4])
        if year is None:
            return None

        attachment = self._document_link(soup, detail_url)
        label = {
            "lei complementar": "Lei Complementar",
            "lei": "Lei",
            "decreto": "Decreto",
            "resolução": "Resolução",
        }[norm_type]
        canonical_title = title if title and _ACT_RE.search(title) else f"{label} nº {number_display}"

        summary = self._summary(body, canonical_title)
        stable = f"{year}:{number_key}"
        return PublicRecord(
            id=f"prefeitura:{kind}:{stable}",
            kind=kind,
            title=canonical_title,
            summary=summary or None,
            date=effective_date,
            year=year,
            attributes={
                "numero": number_display,
                "norma_tipo": norm_type,
                "pagina_oficial": detail_url,
                "document_url": attachment or detail_url,
                "data_publicacao_portal": published,
                "date_source": "texto_do_ato" if date else "publicacao_portal",
                "texto_integral": body[:20000] if body else "",
            },
            source=SourceRef(
                name=SOURCE_NAME,
                url=detail_url,
                authority="Poder Executivo municipal",
                category="executivo",
                retrieval_method="html",
                media_type="text/html",
            ),
        )

    @staticmethod
    def _main_text(soup: BeautifulSoup) -> str:
        for selector in (
            ".entry-content",
            ".elementor-widget-theme-post-content",
            "article .elementor-widget-container",
            "article",
            "main",
        ):
            node = soup.select_one(selector)
            if node is None:
                continue
            text = clean_text(node.get_text(" ", strip=True))
            if len(text) >= 40:
                return text
        return ""

    @staticmethod
    def _document_link(soup: BeautifulSoup, detail_url: str) -> str | None:
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            clean = href.lower().split("?", 1)[0]
            if clean.endswith((".pdf", ".doc", ".docx", ".odt", ".rtf")):
                return urljoin(detail_url, href)
        return None

    @staticmethod
    def _summary(body: str, title: str) -> str:
        text = clean_text(body)
        if not text:
            return ""
        if title and text.casefold().startswith(title.casefold()):
            text = clean_text(text[len(title):])
        return text[:4000]

    @staticmethod
    def _sorted(records: object) -> list[PublicRecord]:
        values = list(records)  # type: ignore[arg-type]
        values.sort(key=lambda record: (record.date or "", record.id), reverse=True)
        return values

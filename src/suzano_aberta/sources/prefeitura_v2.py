from __future__ import annotations

import re
from hashlib import sha256
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import PublicRecord, SourceRef
from ..parsing import absolute_url, clean_text, parse_br_date
from .base import SourceDefinition
from .prefeitura import (
    LICITACOES_URL,
    PREFEITURA,
    PrefeituraSource as BasePrefeituraSource,
)

NOTICIAS_URL_V2 = f"{PREFEITURA}/categorias/noticias/"

_PROCUREMENT_RE = re.compile(
    r"\b(preg[aã]o|concorr[eê]ncia|chamada\s+p[uú]blica|leil[aã]o|"
    r"credenciamento|dispensa|inexigibilidade|tomada\s+de\s+pre[cç]os|edital)\b",
    re.I,
)
_IDENTIFIER_RE = re.compile(r"\b(\d{1,4}/(?:[A-Z]{2,12}/)?20\d{2})\b", re.I)
_PROCESS_RE = re.compile(
    r"\bprocesso(?:\s+(?:administrativo|de\s+compra))?\s*(?:n[º°.]?|:)?\s*"
    r"(\d{1,6}/(?:[A-Z]{2,12}/)?20\d{2})\b",
    re.I,
)
_COMPRAS_GOV_RE = re.compile(
    r"\bcompras\.?gov(?:\.br)?\s*(?:n[º°.]?|:)?\s*([0-9A-Z./-]{3,40})",
    re.I,
)
_DOC_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".odt", ".ods", ".xls", ".xlsx",
    ".csv", ".zip", ".rar", ".7z", ".txt", ".rtf",
)


class EnhancedPrefeituraSource(BasePrefeituraSource):
    """Coleta municipal enriquecida, com paginação e leitura das páginas de detalhe."""

    definition = SourceDefinition(
        key="prefeitura",
        name="Prefeitura Municipal de Suzano",
        url=PREFEITURA,
        authority="Poder Executivo municipal",
        category="executivo",
        notes=(
            "Licitações, secretarias, contas públicas, orçamento, atos oficiais e notícias. "
            "A coleta de compras percorre páginas de índice e detalhes para preservar processo, "
            "modalidade, objeto, situação e anexos publicados."
        ),
    )

    def tenders(self, *, year: int) -> list[PublicRecord]:
        candidates: dict[str, tuple[str, str, str | None]] = {}
        empty_pages = 0

        for page_number in range(1, 41):
            page_url = (
                LICITACOES_URL
                if page_number == 1
                else urljoin(LICITACOES_URL, f"page/{page_number}/")
            )
            try:
                page = self.http.get(page_url, attempts=2)
            except Exception:
                if page_number == 1:
                    raise
                break

            soup = BeautifulSoup(page.text, "html.parser")
            page_hits = 0
            page_years: set[int] = set()

            for anchor in soup.find_all("a", href=True):
                href = str(anchor.get("href", ""))
                detail_url = absolute_url(page_url, href)
                title = clean_text(anchor.get_text(" ", strip=True))
                if (
                    not title
                    or detail_url.rstrip("/") == LICITACOES_URL.rstrip("/")
                    or not detail_url.startswith(PREFEITURA)
                    or not _PROCUREMENT_RE.search(title)
                ):
                    continue

                context = clean_text(
                    anchor.parent.parent.get_text(" ", strip=True)
                    if anchor.parent and anchor.parent.parent
                    else title
                )
                date = parse_br_date(context)
                for value in re.findall(r"\b20\d{2}\b", f"{title} {context} {detail_url}"):
                    page_years.add(int(value))

                belongs = bool(
                    (date and date.startswith(str(year)))
                    or re.search(rf"\b{year}\b", f"{title} {context} {detail_url}")
                )
                if not belongs:
                    continue

                candidates.setdefault(detail_url, (title, context, date))
                page_hits += 1

            if page_hits == 0:
                empty_pages += 1
            else:
                empty_pages = 0

            if page_number > 2 and empty_pages >= 2 and page_years and max(page_years) < year:
                break
            if page_number > 4 and empty_pages >= 3:
                break

        records: list[PublicRecord] = []
        for detail_url, (listing_title, listing_context, listing_date) in candidates.items():
            record = self._tender_detail(
                detail_url=detail_url,
                listing_title=listing_title,
                listing_context=listing_context,
                listing_date=listing_date,
                year=year,
            )
            if record is not None:
                records.append(record)

        records.sort(key=lambda item: (item.date or "", item.id), reverse=True)
        return records

    def news(self, *, year: int, limit: int = 100) -> list[PublicRecord]:
        records: list[PublicRecord] = []
        seen: set[str] = set()

        for page_number in range(1, 11):
            page_url = (
                NOTICIAS_URL_V2
                if page_number == 1
                else urljoin(NOTICIAS_URL_V2, f"page/{page_number}/")
            )
            try:
                page = self.http.get(page_url, attempts=2)
            except Exception:
                if page_number == 1:
                    raise
                break

            soup = BeautifulSoup(page.text, "html.parser")
            page_added = 0
            for anchor in soup.find_all("a", href=True):
                url = absolute_url(page_url, str(anchor.get("href", "")))
                title = clean_text(anchor.get_text(" ", strip=True))
                if not title or url in seen or not url.startswith(PREFEITURA):
                    continue
                if any(part in url for part in ("/editais-licitacoes/", "/transparencia/", "/imprensa-oficial/")):
                    continue

                context = clean_text(
                    anchor.parent.parent.get_text(" ", strip=True)
                    if anchor.parent and anchor.parent.parent
                    else title
                )
                date = parse_br_date(context)
                if date is None or not date.startswith(str(year)):
                    continue
                if len(title) < 12:
                    continue

                seen.add(url)
                records.append(
                    PublicRecord(
                        id=f"prefeitura:noticia:{sha256(url.encode()).hexdigest()[:16]}",
                        kind="noticia",
                        title=title[:500],
                        summary=context[:1600] if context and context != title else None,
                        date=date,
                        year=year,
                        attributes={"url_canonica": url, "categoria": "noticias"},
                        source=SourceRef(name=self.definition.name, url=url),
                    )
                )
                page_added += 1
                if len(records) >= limit:
                    return records

            if page_number > 2 and page_added == 0:
                break

        return records

    def _tender_detail(
        self,
        *,
        detail_url: str,
        listing_title: str,
        listing_context: str,
        listing_date: str | None,
        year: int,
    ) -> PublicRecord | None:
        try:
            page = self.http.get(detail_url, attempts=2)
            soup = BeautifulSoup(page.text, "html.parser")
            for node in soup(["script", "style", "noscript", "template"]):
                node.decompose()
            raw_text = soup.get_text("\n", strip=True)
            lines = [clean_text(line) for line in raw_text.splitlines() if clean_text(line)]
            text = clean_text(" ".join(lines))
        except Exception:
            soup = None
            lines = []
            text = listing_context

        date = parse_br_date(text) or listing_date
        combined = f"{listing_title} {listing_context} {text} {detail_url}"
        if not (
            (date and date.startswith(str(year)))
            or re.search(rf"\b{year}\b", combined)
        ):
            return None

        title = listing_title
        if soup is not None:
            heading = soup.find("h1")
            if heading is not None:
                candidate = clean_text(heading.get_text(" ", strip=True))
                if candidate:
                    title = candidate

        identifier_match = _IDENTIFIER_RE.search(f"{title} {text}")
        identifier = identifier_match.group(1).upper() if identifier_match else None
        process_match = _PROCESS_RE.search(text)
        process_number = process_match.group(1).upper() if process_match else None
        compras_match = _COMPRAS_GOV_RE.search(text)
        compras_gov = compras_match.group(1).upper() if compras_match else None
        modality = self._procurement_modality(f"{title} {text}")
        status = self._procurement_status(f"{title} {text}")
        object_text = self._line_value(lines, ("objeto",))
        if not object_text:
            object_text = listing_context if listing_context != listing_title else None

        documents: list[dict[str, str]] = []
        if soup is not None:
            seen_docs: set[str] = set()
            for anchor in soup.find_all("a", href=True):
                url = absolute_url(detail_url, str(anchor.get("href", "")))
                path = url.lower().split("?", 1)[0]
                if not path.endswith(_DOC_EXTENSIONS) or url in seen_docs:
                    continue
                seen_docs.add(url)
                label = clean_text(anchor.get_text(" ", strip=True)) or url.rsplit("/", 1)[-1]
                documents.append({"title": label[:300], "url": url})
                if len(documents) >= 80:
                    break

        stable_identifier = identifier or sha256(detail_url.encode()).hexdigest()[:12]
        attributes = {
            "identifier": stable_identifier,
            "modalidade": modality,
            "situacao": status,
            "processo": process_number,
            "compras_gov": compras_gov,
            "objeto": object_text,
            "documentos": documents,
            "documentos_total": len(documents),
            "texto_publicacao": text[:50_000],
            "url_canonica": detail_url,
        }
        return PublicRecord(
            id=f"prefeitura:licitacao:{stable_identifier}",
            kind="licitacao",
            title=title[:500],
            summary=(object_text or listing_context or text)[:4000] or None,
            date=date,
            year=year,
            attributes=attributes,
            source=SourceRef(name="Editais e Licitações — Prefeitura de Suzano", url=detail_url),
        )

    @staticmethod
    def _line_value(lines: list[str], labels: tuple[str, ...]) -> str | None:
        for line in lines:
            folded = line.casefold()
            for label in labels:
                match = re.match(rf"^{re.escape(label)}\s*[:\-–—]\s*(.+)$", line, re.I)
                if match:
                    return clean_text(match.group(1))[:4000]
                if folded.startswith(f"{label.casefold()} "):
                    value = clean_text(line[len(label):].lstrip(" :–—-"))
                    if value:
                        return value[:4000]
        return None

    @staticmethod
    def _procurement_modality(text: str) -> str | None:
        folded = text.casefold()
        choices = (
            ("pregão eletrônico", "pregão eletrônico"),
            ("concorrência eletrônica", "concorrência eletrônica"),
            ("chamada pública", "chamada pública"),
            ("leilão", "leilão"),
            ("credenciamento", "credenciamento"),
            ("dispensa", "dispensa"),
            ("inexigibilidade", "inexigibilidade"),
            ("tomada de preços", "tomada de preços"),
        )
        return next((label for token, label in choices if token in folded), None)

    @staticmethod
    def _procurement_status(text: str) -> str | None:
        folded = text.casefold()
        for token, label in (
            ("suspens", "suspensa"),
            ("anulad", "anulada"),
            ("revogad", "revogada"),
            ("homologad", "homologada"),
            ("encerrad", "encerrada"),
            ("fracassad", "fracassada"),
            ("desert", "deserta"),
            ("reabert", "reaberta"),
            ("abert", "aberta"),
        ):
            if token in folded:
                return label
        return None

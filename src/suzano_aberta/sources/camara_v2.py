from __future__ import annotations

import re
from hashlib import sha256

from bs4 import BeautifulSoup

from ..models import PublicRecord, SourceRef
from ..parsing import absolute_url, clean_text, parse_br_date
from .camara import CAMARA, CamaraSource as BaseCamaraSource

LICITACOES_ABERTAS_URL = f"{CAMARA}/category/licitacoes/licitacoes-2/"
DISPENSAS_YEAR_URL = f"{CAMARA}/dispensas-de-licitacoes-{{year}}/"

_PROCUREMENT_RE = re.compile(
    r"\b(preg[aã]o|concorr[eê]ncia|dispensa|inexigibilidade|chamada\s+p[uú]blica|leil[aã]o)\b",
    re.I,
)
_IDENTIFIER_RE = re.compile(r"\b(\d{1,4}/20\d{2})\b", re.I)
_PROCESS_RE = re.compile(
    r"\bprocesso(?:\s+(?:administrativo|de\s+compra))?\s*(?:n[º°.]?|:)?\s*(\d{1,6}/20\d{2})\b",
    re.I,
)
_DOC_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".odt", ".ods", ".xls", ".xlsx",
    ".csv", ".zip", ".rar", ".7z", ".txt", ".rtf",
)


class EnhancedCamaraSource(BaseCamaraSource):
    """Amplia a fonte legislativa com certames e dispensas da transparência da Câmara."""

    def contracts(self, *, year: int) -> list[PublicRecord]:
        contracts = super().contracts(year=year)
        try:
            procurements = self.procurements(year=year)
        except Exception:
            procurements = []
        return [*contracts, *procurements]

    def procurements(self, *, year: int) -> list[PublicRecord]:
        candidates: dict[str, tuple[str, str, str | None]] = {}
        for index_url in (LICITACOES_ABERTAS_URL, DISPENSAS_YEAR_URL.format(year=year)):
            try:
                page = self.http.get(index_url, attempts=2)
            except Exception:
                continue
            soup = BeautifulSoup(page.text, "html.parser")
            for anchor in soup.find_all("a", href=True):
                url = absolute_url(index_url, str(anchor.get("href", "")))
                if not url.startswith(CAMARA) or url.rstrip("/") == index_url.rstrip("/"):
                    continue
                title = clean_text(anchor.get_text(" ", strip=True))
                context = clean_text(
                    anchor.parent.parent.get_text(" ", strip=True)
                    if anchor.parent and anchor.parent.parent
                    else title
                )
                combined = f"{title} {context} {url}"
                if not _PROCUREMENT_RE.search(combined) and not re.search(rf"\b\d{{1,4}}/{year}\b", combined):
                    continue
                date = parse_br_date(context)
                if not re.search(rf"\b{year}\b", combined) and not (date and date.startswith(str(year))):
                    continue
                candidates.setdefault(url, (title or context, context, date))

        records: list[PublicRecord] = []
        for url, (listing_title, listing_context, listing_date) in candidates.items():
            record = self._procurement_detail(url, listing_title, listing_context, listing_date, year)
            if record is not None:
                records.append(record)
        records.sort(key=lambda item: (item.date or "", item.id), reverse=True)
        return records

    def _procurement_detail(
        self,
        url: str,
        listing_title: str,
        listing_context: str,
        listing_date: str | None,
        year: int,
    ) -> PublicRecord | None:
        try:
            page = self.http.get(url, attempts=2)
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
        combined = f"{listing_title} {listing_context} {text} {url}"
        if not re.search(rf"\b{year}\b", combined) and not (date and date.startswith(str(year))):
            return None

        title = listing_title
        if soup is not None:
            heading = soup.find("h1")
            if heading is not None:
                value = clean_text(heading.get_text(" ", strip=True))
                if value:
                    title = value

        identifier_match = _IDENTIFIER_RE.search(f"{title} {text}")
        identifier = identifier_match.group(1).upper() if identifier_match else None
        process_match = _PROCESS_RE.search(text)
        process_number = process_match.group(1).upper() if process_match else None
        modality = self._modality(f"{title} {text}")
        status = self._status(f"{listing_context} {text}")
        object_text = self._line_value(lines, ("objeto",))
        legal_basis = self._line_value(lines, ("amparo legal",))

        documents: list[dict[str, str]] = []
        if soup is not None:
            seen: set[str] = set()
            for anchor in soup.find_all("a", href=True):
                doc_url = absolute_url(url, str(anchor.get("href", "")))
                if doc_url in seen or not doc_url.lower().split("?", 1)[0].endswith(_DOC_EXTENSIONS):
                    continue
                seen.add(doc_url)
                label = clean_text(anchor.get_text(" ", strip=True)) or doc_url.rsplit("/", 1)[-1]
                documents.append({"title": label[:300], "url": doc_url})
                if len(documents) >= 80:
                    break

        stable = sha256(url.encode()).hexdigest()[:16]
        return PublicRecord(
            id=f"camara:licitacao:{stable}",
            kind="licitacao",
            title=title[:500],
            summary=(object_text or listing_context or text)[:4000] or None,
            date=date,
            year=year,
            attributes={
                "identifier": identifier,
                "modalidade": modality,
                "situacao": status,
                "processo": process_number,
                "amparo_legal": legal_basis,
                "objeto": object_text,
                "documentos": documents,
                "documentos_total": len(documents),
                "texto_publicacao": text[:50_000],
                "url_canonica": url,
            },
            source=SourceRef(name="Licitações e Contratos — Câmara Municipal de Suzano", url=url),
        )

    @staticmethod
    def _line_value(lines: list[str], labels: tuple[str, ...]) -> str | None:
        for line in lines:
            for label in labels:
                match = re.match(rf"^{re.escape(label)}\s*[:\-–—]\s*(.+)$", line, re.I)
                if match:
                    return clean_text(match.group(1))[:4000]
        return None

    @staticmethod
    def _modality(text: str) -> str | None:
        folded = text.casefold()
        for token, label in (
            ("pregão eletrônico", "pregão eletrônico"),
            ("concorrência", "concorrência"),
            ("dispensa", "dispensa"),
            ("inexigibilidade", "inexigibilidade"),
            ("chamada pública", "chamada pública"),
            ("leilão", "leilão"),
        ):
            if token in folded:
                return label
        return None

    @staticmethod
    def _status(text: str) -> str | None:
        folded = text.casefold()
        for token, label in (
            ("parcialmente homolog", "parcialmente homologada"),
            ("homolog", "homologada"),
            ("suspens", "suspensa"),
            ("anulad", "anulada"),
            ("revogad", "revogada"),
            ("encerrad", "encerrada"),
            ("fracassad", "fracassada"),
            ("com disputa", "com disputa"),
            ("nova", "nova"),
        ):
            if token in folded:
                return label
        return None

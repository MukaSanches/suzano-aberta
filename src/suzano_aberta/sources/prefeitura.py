from __future__ import annotations

import re
from collections.abc import Callable
from hashlib import sha256

from bs4 import BeautifulSoup

from ..models import PublicRecord, RecordKind, SourceRef
from ..parsing import absolute_url, clean_text, dict_rows, normalize_key, parse_br_date
from .base import BaseSource, SourceDefinition


PREFEITURA = "https://suzano.sp.gov.br"
LICITACOES_URL = f"{PREFEITURA}/editais-licitacoes/"
SECRETARIAS_URL = f"{PREFEITURA}/secretarias/"
CONTAS_URL = f"{PREFEITURA}/transparencia/contas-publicas/"
ORCAMENTO_URL = f"{PREFEITURA}/transparencia/leis-orcamentarias/"
IMPRENSA_URL = f"{PREFEITURA}/imprensa-oficial/"
LEIS_DECRETOS_URL = f"{PREFEITURA}/transparencia/leis-e-decretos/"
NOTICIAS_URL = f"{PREFEITURA}/noticias/"


class PrefeituraSource(BaseSource):
    definition = SourceDefinition(
        key="prefeitura",
        name="Prefeitura Municipal de Suzano",
        url=PREFEITURA,
        authority="Poder Executivo municipal",
        category="executivo",
        notes="Licitações, secretarias, contas públicas, orçamento, atos oficiais e notícias institucionais.",
    )

    def collect(self, *, year: int) -> list[PublicRecord]:
        records: list[PublicRecord] = []
        collectors: tuple[Callable[[], list[PublicRecord]], ...] = (
            lambda: self.tenders(year=year),
            self.secretariats,
            lambda: self.fiscal_documents(year=year, limit=400),
            lambda: self.budget_documents(year=year, limit=250),
            lambda: self.official_gazette(year=year, limit=300),
            lambda: self.legal_acts(year=year, limit=500),
            lambda: self.news(year=year, limit=100),
        )
        for collector in collectors:
            try:
                records.extend(collector())
            except Exception:
                continue
        return records

    def tenders(self, *, year: int) -> list[PublicRecord]:
        page = self.http.get(LICITACOES_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        records: list[PublicRecord] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            url = absolute_url(LICITACOES_URL, href)
            if "/editais-licitacoes/" not in url or url.rstrip("/") == LICITACOES_URL.rstrip("/"):
                continue
            title = clean_text(anchor.get_text(" ", strip=True))
            if not title or title.casefold() in {"editais e licitações", "editais e licitacoes"}:
                continue
            if url in seen:
                continue
            context = clean_text(anchor.parent.parent.get_text(" ", strip=True) if anchor.parent and anchor.parent.parent else title)
            date = parse_br_date(context)
            combined = f"{title} {context} {url}"
            if not self._belongs_to_year(combined, date, year):
                continue
            seen.add(url)
            identifier = self._extract_identifier(title) or sha256(url.encode()).hexdigest()[:12]
            records.append(
                PublicRecord(
                    id=f"prefeitura:licitacao:{identifier}",
                    kind="licitacao",
                    title=title,
                    date=date,
                    year=year,
                    attributes={"identifier": identifier},
                    source=SourceRef(name=self.definition.name, url=url),
                )
            )
        return records

    def secretariats(self) -> list[PublicRecord]:
        page = self.http.get(SECRETARIAS_URL)
        records: list[PublicRecord] = []
        for row in dict_rows(page.text):
            name = row.get("secretaria", "")
            if not name:
                continue
            records.append(
                PublicRecord(
                    id=f"prefeitura:secretaria:{self._slug(name)}",
                    kind="secretaria",
                    title=name,
                    attributes=row,
                    source=SourceRef(name=self.definition.name, url=SECRETARIAS_URL),
                )
            )
        return records

    def fiscal_documents(self, *, year: int, limit: int = 400) -> list[PublicRecord]:
        return self._document_index(
            url=CONTAS_URL,
            year=year,
            kind="documento_fiscal",
            id_prefix="prefeitura:fiscal",
            limit=limit,
            source_name="Contas Públicas — Prefeitura de Suzano",
        )

    def budget_documents(self, *, year: int, limit: int = 250) -> list[PublicRecord]:
        return self._document_index(
            url=ORCAMENTO_URL,
            year=year,
            kind="documento_orcamentario",
            id_prefix="prefeitura:orcamento",
            limit=limit,
            source_name="Leis Orçamentárias — Prefeitura de Suzano",
        )

    def official_gazette(self, *, year: int, limit: int = 300) -> list[PublicRecord]:
        """Indexa as edições da Imprensa Oficial pelo URL canônico de cada edição."""
        page = self.http.get(IMPRENSA_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        records: list[PublicRecord] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            title = clean_text(anchor.get_text(" ", strip=True))
            if not title.casefold().startswith("edição") and not title.casefold().startswith("edicao"):
                continue
            edition_url = absolute_url(IMPRENSA_URL, str(anchor.get("href", "")))
            if edition_url.rstrip("/") == IMPRENSA_URL.rstrip("/") or edition_url in seen:
                continue
            context = clean_text(anchor.parent.parent.get_text(" ", strip=True) if anchor.parent and anchor.parent.parent else title)
            date = parse_br_date(f"{title} {context}")
            if not self._belongs_to_year(f"{title} {context} {edition_url}", date, year):
                continue
            seen.add(edition_url)
            number_match = re.search(r"edi(?:ç|c)[aã]o\s+(?:extra\s+)?([0-9]+(?:\.[0-9]+)?)", title, re.I)
            number = number_match.group(1) if number_match else sha256(edition_url.encode()).hexdigest()[:10]
            records.append(
                PublicRecord(
                    id=f"prefeitura:diario:{year}:{number}",
                    kind="ato_oficial",
                    title=title,
                    summary=context if context != title else None,
                    date=date,
                    year=year,
                    attributes={"edicao": number, "edition_url": edition_url},
                    source=SourceRef(name="Imprensa Oficial do Município de Suzano", url=edition_url),
                )
            )
            if len(records) >= limit:
                break
        return records

    def legal_acts(self, *, year: int, limit: int = 500) -> list[PublicRecord]:
        """Lê a página oficial de Leis e Decretos e preserva o tipo jurídico."""
        page = self.http.get(LEIS_DECRETOS_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        records: list[PublicRecord] = []
        seen: set[str] = set()
        extensions = (".pdf", ".doc", ".docx", ".odt", ".rtf")
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            document_url = absolute_url(LEIS_DECRETOS_URL, href)
            if not document_url.lower().split("?", 1)[0].endswith(extensions) or document_url in seen:
                continue
            title = clean_text(anchor.get_text(" ", strip=True))
            context = clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else title)
            combined = clean_text(f"{title} {context}")
            date = parse_br_date(f"{combined} {document_url}")
            if not self._belongs_to_year(f"{combined} {document_url}", date, year):
                continue

            folded = combined.casefold()
            kind: RecordKind
            norm_type = "ato oficial"
            if re.search(r"\blei\s+complementar\b", folded):
                kind = "lei"
                norm_type = "lei complementar"
            elif re.search(r"\blei\b", folded):
                kind = "lei"
                norm_type = "lei"
            elif re.search(r"\bdecreto\b", folded):
                kind = "decreto"
                norm_type = "decreto"
            else:
                kind = "ato_oficial"

            identifier = self._extract_identifier(combined)
            stable = identifier or sha256(document_url.encode()).hexdigest()[:16]
            seen.add(document_url)
            records.append(
                PublicRecord(
                    id=f"prefeitura:{kind}:{stable}",
                    kind=kind,
                    title=title or combined or f"{norm_type.title()} de {year}",
                    summary=context if context and context != title else None,
                    date=date,
                    year=year,
                    attributes={
                        "document_url": document_url,
                        "norma_tipo": norm_type,
                        "identifier": identifier,
                    },
                    source=SourceRef(name="Leis e Decretos — Prefeitura de Suzano", url=document_url),
                )
            )
            if len(records) >= limit:
                break
        return records

    def news(self, *, year: int, limit: int = 100) -> list[PublicRecord]:
        page = self.http.get(NOTICIAS_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        records: list[PublicRecord] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            url = absolute_url(NOTICIAS_URL, str(anchor.get("href", "")))
            title = clean_text(anchor.get_text(" ", strip=True))
            if not title or url in seen or not url.startswith(PREFEITURA):
                continue
            context = clean_text(anchor.parent.parent.get_text(" ", strip=True) if anchor.parent and anchor.parent.parent else title)
            date = parse_br_date(context)
            if date is None or not date.startswith(str(year)):
                continue
            if "/editais-licitacoes/" in url or "/transparencia/" in url or "/imprensa-oficial/" in url:
                continue
            seen.add(url)
            records.append(
                PublicRecord(
                    id=f"prefeitura:noticia:{sha256(url.encode()).hexdigest()[:16]}",
                    kind="noticia",
                    title=title,
                    date=date,
                    year=year,
                    source=SourceRef(name=self.definition.name, url=url),
                )
            )
            if len(records) >= limit:
                break
        return records

    def _document_index(
        self,
        *,
        url: str,
        year: int,
        kind: RecordKind,
        id_prefix: str,
        limit: int,
        source_name: str,
    ) -> list[PublicRecord]:
        page = self.http.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        records: list[PublicRecord] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            document_url = absolute_url(url, href)
            title = clean_text(anchor.get_text(" ", strip=True))
            if not title or document_url in seen:
                continue
            is_document = any(
                document_url.lower().split("?", 1)[0].endswith(ext)
                for ext in (".pdf", ".csv", ".xls", ".xlsx", ".ods", ".doc", ".docx", ".zip")
            )
            if not is_document:
                continue
            context = clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else title)
            combined = f"{title} {context} {document_url}"
            date = parse_br_date(combined)
            if not self._belongs_to_year(combined, date, year):
                continue
            seen.add(document_url)
            stable = sha256(document_url.encode()).hexdigest()[:16]
            records.append(
                PublicRecord(
                    id=f"{id_prefix}:{stable}",
                    kind=kind,
                    title=title,
                    summary=context if context != title else None,
                    date=date,
                    year=year,
                    attributes={"document_url": document_url},
                    source=SourceRef(name=source_name, url=document_url),
                )
            )
            if len(records) >= limit:
                break
        return records

    @staticmethod
    def _belongs_to_year(text: str, date: str | None, year: int) -> bool:
        if date is not None:
            return date.startswith(str(year))
        years = {int(value) for value in re.findall(r"\b20\d{2}\b", text)}
        return year in years

    @staticmethod
    def _extract_identifier(title: str) -> str | None:
        match = re.search(r"(?:N[º°.\s:]*)?(\d{1,4}/(?:[A-Z]+/)?\d{4})", title, re.I)
        if match:
            return re.sub(r"\s+", "", match.group(1)).upper()
        return None

    @staticmethod
    def _slug(value: str) -> str:
        return normalize_key(value).replace("_", "-")

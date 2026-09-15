from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag

from ..models import PublicRecord, SourceRef
from ..parsing import clean_text, parse_br_date
from .base import BaseSource, SourceDefinition


ROOT = "https://leis.camarasuzano.sp.gov.br/szn/legislacao/"
ORDINARY_YEAR = urljoin(ROOT, "leis/IndAno.php?Ano={year}")
COMPLEMENTARY_YEAR = urljoin(ROOT, "leis/IndAnoLc.php?Ano={year}")

_LAW_NUMBER = re.compile(r"\bN\s*(?:º|°|\.)?\s*L?(\d{1,6})\b", re.I)
_HREF_NUMBER = re.compile(r"/(Lc|L)(\d{1,6})\.htm(?:$|[?#])", re.I)


class LegislacaoSource(BaseSource):
    """Índices consolidados de legislação mantidos pela Câmara Municipal de Suzano."""

    definition = SourceDefinition(
        key="legislacao_camara",
        name="Legislação Municipal Consolidada — Câmara Municipal de Suzano",
        url=ROOT,
        authority="Poder Legislativo municipal",
        category="legislativo",
        notes=(
            "Leis municipais e leis complementares indexadas pelo sistema oficial de legislação "
            "da Câmara, com número, data, ementa e página individual da norma."
        ),
    )

    def collect(self, *, year: int) -> list[PublicRecord]:
        records = [*self.ordinary_laws(year=year), *self.complementary_laws(year=year)]
        return list({record.id: record for record in records}.values())

    def ordinary_laws(self, *, year: int) -> list[PublicRecord]:
        return self._year_index(
            url=ORDINARY_YEAR.format(year=year),
            year=year,
            law_class="ordinaria",
        )

    def complementary_laws(self, *, year: int) -> list[PublicRecord]:
        return self._year_index(
            url=COMPLEMENTARY_YEAR.format(year=year),
            year=year,
            law_class="complementar",
        )

    def _year_index(self, *, url: str, year: int, law_class: str) -> list[PublicRecord]:
        page = self.http.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        records: list[PublicRecord] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            detail_url = urljoin(url, href)
            href_match = _HREF_NUMBER.search(detail_url)
            if href_match is None or detail_url in seen:
                continue

            raw_title = clean_text(anchor.get_text(" ", strip=True))
            folded = raw_title.casefold()
            if law_class == "complementar":
                if "lei complementar" not in folded:
                    continue
            elif "lei municipal" not in folded or "complementar" in folded:
                continue

            date = parse_br_date(raw_title)
            if date is None or not date.startswith(str(year)):
                continue

            number_match = _LAW_NUMBER.search(raw_title)
            number = number_match.group(1).lstrip("0") if number_match else href_match.group(2).lstrip("0")
            number = number or "0"
            summary = self._summary_after(anchor)
            seen.add(detail_url)

            label = "Lei Complementar" if law_class == "complementar" else "Lei Municipal"
            records.append(
                PublicRecord(
                    id=f"camara:lei:{law_class}:{year}:{number}",
                    kind="lei",
                    title=f"{label} nº {number}, de {self._display_date(date)}",
                    summary=summary or None,
                    date=date,
                    year=year,
                    attributes={
                        "numero": number,
                        "norma_tipo": "lei complementar" if law_class == "complementar" else "lei municipal",
                        "classe": law_class,
                        "catalog_url": url,
                        "document_url": detail_url,
                    },
                    source=SourceRef(name=self.definition.name, url=detail_url),
                )
            )

        records.sort(key=lambda record: (record.date or "", record.id), reverse=True)
        return records

    @staticmethod
    def _summary_after(anchor: Tag) -> str:
        pieces: list[str] = []
        for node in anchor.next_elements:
            if node is anchor:
                continue
            if isinstance(node, Tag) and node.name == "a":
                break
            if isinstance(node, NavigableString):
                text = clean_text(str(node))
                if not text:
                    continue
                # O título pode reaparecer por causa do HTML legado/malformado do índice.
                if text.casefold() == clean_text(anchor.get_text(" ", strip=True)).casefold():
                    continue
                pieces.append(text)
        summary = clean_text(" ".join(pieces))
        # Remove resíduos de navegação que eventualmente aparecem antes da ementa.
        summary = re.sub(r"^\s*(?:\xa0|&nbsp;)+", "", summary)
        return summary[:4000]

    @staticmethod
    def _display_date(value: str) -> str:
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value)
        if match is None:
            return value
        year, month, day = match.groups()
        return f"{day}/{month}/{year}"


def supported_years(start: int = 1949, end: int = 2100) -> Iterable[int]:
    """Faixa conservadora para jobs históricos; índices inexistentes retornam lista vazia."""
    return range(start, end + 1)

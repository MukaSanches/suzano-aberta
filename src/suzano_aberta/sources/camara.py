from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from hashlib import sha256
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..models import PublicRecord, SourceRef
from ..parsing import absolute_url, clean_text, csv_dicts, dict_rows, normalize_key, parse_br_date
from .base import BaseSource, SourceDefinition


CAMARA = "https://www.camarasuzano.sp.gov.br"
SESSOES_URL = f"{CAMARA}/ordinarias/sessoes_ordinarias.php"
CONTRATOS_DADOS_URL = f"{CAMARA}/dados-estruturados/"
COMISSOES_URL = f"{CAMARA}/pauta-das-reunioes-das-comissoes-permanentes-v2/"
DIARIO_URL = f"{CAMARA}/doel/index.php?all=1"
VEREADORES_URL = f"{CAMARA}/vereadores-19a-legislatura-2/"

PROPOSITION_RE = re.compile(
    r"(?P<tipo>PROJETO DE LEI COMPLEMENTAR|PROJETO DE LEI|PROJETO DE RESOLUÇÃO|"
    r"PROJETO DE DECRETO LEGISLATIVO|PROJETO DE EMENDA À L\.O\.M\.|"
    r"EMENDA SUBSTITUTIVA|EMENDA ADITIVA|EMENDA SUPRESSIVA|SUBSTITUTIVO|"
    r"REQUERIMENTO|INDICAÇÃO|MOÇÃO|VETO)\s*-\s*"
    r"(?P<numero>\d{1,4}/\d{4})\s*-\s*",
    re.IGNORECASE,
)


class CamaraSource(BaseSource):
    definition = SourceDefinition(
        key="camara",
        name="Câmara Municipal de Suzano",
        url=CAMARA,
        authority="Poder Legislativo municipal",
        category="legislativo",
        notes="Sessões, proposições, contratos, comissões, presenças e Diário Oficial do Legislativo.",
    )

    def collect(self, *, year: int) -> list[PublicRecord]:
        records: list[PublicRecord] = []
        sessions: list[PublicRecord] | None = None
        try:
            records.extend(self.councilors())
        except Exception:
            pass
        try:
            sessions = self.sessions(year=year)
            records.extend(sessions)
        except Exception:
            sessions = None
        if sessions is not None:
            try:
                records.extend(self.propositions(year=year, sessions=sessions))
            except Exception:
                pass
        collectors: tuple[Callable[[], list[PublicRecord]], ...] = (
            lambda: self.contracts(year=year),
            self.committees,
            lambda: self.attendance(year=year),
            lambda: self.diary(year=year, limit=250),
        )
        for collector in collectors:
            try:
                records.extend(collector())
            except Exception:
                continue
        return records

    def councilors(self) -> list[PublicRecord]:
        """Lê a relação oficial da 19ª Legislatura."""
        page = self.http.get(VEREADORES_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        pattern = re.compile(
            r"^(?P<nome>[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][^()]{2,100}?)\s*"
            r"\((?P<partido>[A-Za-zÀ-ÿ0-9 .-]{2,30})\)"
            r"(?:\s*[–—-]\s*(?P<complemento>.*))?$",
            re.IGNORECASE,
        )
        records: list[PublicRecord] = []
        seen: set[str] = set()
        for raw in soup.stripped_strings:
            line = clean_text(str(raw))
            match = pattern.match(line)
            if not match:
                continue
            name = clean_text(match.group("nome"))
            party = clean_text(match.group("partido")).upper()
            complement = clean_text(match.group("complemento") or "")
            if len(name.split()) < 2:
                continue
            slug = normalize_key(name).replace("_", "-")
            if slug in seen:
                continue
            seen.add(slug)
            licensed = complement.casefold() == "licenciado"
            records.append(
                PublicRecord(
                    id=f"camara:vereador:{slug}",
                    kind="vereador",
                    title=name,
                    attributes={
                        "partido": party,
                        "nome_publico": None if licensed or not complement else complement,
                        "licenciado": licensed,
                        "legislatura": 19,
                    },
                    source=SourceRef(name=self.definition.name, url=VEREADORES_URL),
                )
            )
        return records

    def sessions(self, *, year: int) -> list[PublicRecord]:
        result = self.http.get(f"{SESSOES_URL}?ano={year}")
        soup = BeautifulSoup(result.text, "html.parser")
        records: list[PublicRecord] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            if "sessao_ordinaria.php?sid=" not in href:
                continue
            url = absolute_url(SESSOES_URL, href)
            sid = parse_qs(urlparse(url).query).get("sid", [""])[0]
            if not sid or sid in seen:
                continue
            seen.add(sid)
            context = clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else anchor.get_text(" "))
            title = clean_text(anchor.get_text(" ", strip=True)) or f"Sessão ordinária {sid}"
            date = parse_br_date(context)
            records.append(
                PublicRecord(
                    id=f"camara:sessao:{sid}",
                    kind="sessao",
                    title=title,
                    summary=context or None,
                    date=date,
                    year=year,
                    attributes={"sid": sid, "session_url": url},
                    source=SourceRef(name=self.definition.name, url=url),
                )
            )
        return records

    def propositions(self, *, year: int, sessions: list[PublicRecord] | None = None) -> list[PublicRecord]:
        session_records = sessions if sessions is not None else self.sessions(year=year)
        records: dict[str, PublicRecord] = {}
        for session in session_records:
            sid = str(session.attributes.get("sid", ""))
            if not sid:
                continue
            url = f"{CAMARA}/ordinarias/sessao_projetos.php?sid={sid}"
            try:
                page = self.http.get(url)
            except Exception:
                continue
            soup = BeautifulSoup(page.text, "html.parser")
            text = soup.get_text("\n", strip=True)
            matches = list(PROPOSITION_RE.finditer(text))
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                block = text[match.end() : end]
                lines = [clean_text(line) for line in block.splitlines() if clean_text(line)]
                if not lines:
                    continue
                author = lines[-1] if len(lines) > 1 else ""
                summary = clean_text(" ".join(lines[:-1] if len(lines) > 1 else lines))
                type_name = clean_text(match.group("tipo")).upper()
                number = match.group("numero")
                stable_type = re.sub(r"\W+", "-", type_name.casefold(), flags=re.UNICODE).strip("-")
                record_id = f"camara:proposicao:{stable_type}:{number}"
                existing = records.get(record_id)
                session_info = {"sid": sid, "session_title": session.title, "session_date": session.date}
                if existing:
                    sessions_seen = list(existing.attributes.get("sessions", []))
                    if session_info not in sessions_seen:
                        sessions_seen.append(session_info)
                        existing.attributes["sessions"] = sessions_seen
                    continue
                records[record_id] = PublicRecord(
                    id=record_id,
                    kind="proposicao",
                    title=f"{type_name.title()} {number}",
                    summary=summary or None,
                    year=year,
                    attributes={"type": type_name, "number": number, "author": author, "sessions": [session_info]},
                    source=SourceRef(name=self.definition.name, url=url),
                )
        return list(records.values())

    def contracts(self, *, year: int) -> list[PublicRecord]:
        page = self.http.get(CONTRATOS_DADOS_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        csv_url: str | None = None
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            text = clean_text(anchor.get_text(" ", strip=True))
            if href.lower().endswith(".csv") and (str(year) in href or str(year) in text):
                csv_url = absolute_url(CONTRATOS_DADOS_URL, href)
                break
        if csv_url is None:
            report_url = f"{CAMARA}/relatorio-de-contratos-vigentes-{year}/"
            try:
                return self._contracts_from_html(report_url, year)
            except Exception:
                return []
        data = self.http.get(csv_url)
        records: list[PublicRecord] = []
        for row in csv_dicts(data.content):
            number = row.get("n") or row.get("numero") or row.get("n_o") or row.get("n_0") or ""
            if not number:
                number = sha256(repr(sorted(row.items())).encode()).hexdigest()[:12]
            contractor = row.get("contratada", "")
            records.append(
                PublicRecord(
                    id=f"camara:contrato:{year}:{number}",
                    kind="contrato",
                    title=f"Contrato {number}",
                    summary=row.get("objeto") or None,
                    date=parse_br_date(row.get("data", "")),
                    year=year,
                    attributes={**row, "contractor": contractor},
                    source=SourceRef(name=self.definition.name, url=csv_url),
                )
            )
        return records

    def _contracts_from_html(self, url: str, year: int) -> list[PublicRecord]:
        page = self.http.get(url)
        rows = dict_rows(page.text)
        records: list[PublicRecord] = []
        for row in rows:
            number = row.get("n") or row.get("n_o") or row.get("numero") or ""
            if not number:
                continue
            records.append(
                PublicRecord(
                    id=f"camara:contrato:{year}:{number}",
                    kind="contrato",
                    title=f"Contrato {number}",
                    summary=row.get("objeto") or None,
                    date=parse_br_date(row.get("data", "")),
                    year=year,
                    attributes=row,
                    source=SourceRef(name=self.definition.name, url=url),
                )
            )
        return records

    def committees(self) -> list[PublicRecord]:
        page = self.http.get(COMISSOES_URL)
        records: list[PublicRecord] = []
        for index, row in enumerate(dict_rows(page.text), start=1):
            date_raw = row.get("data", "")
            meeting = row.get("reuniao", "")
            committee = row.get("comissao_permanente", "")
            subject = row.get("assunto", "")
            stable = sha256(f"{date_raw}|{meeting}|{committee}|{subject}".encode()).hexdigest()[:16]
            records.append(
                PublicRecord(
                    id=f"camara:comissao:{stable}",
                    kind="comissao",
                    title=f"{committee or 'Comissão'} — reunião {meeting or index}",
                    summary=subject or None,
                    date=parse_br_date(date_raw),
                    attributes=row,
                    source=SourceRef(name=self.definition.name, url=COMISSOES_URL),
                )
            )
        return records

    def attendance(self, *, year: int) -> list[PublicRecord]:
        url = f"{CAMARA}/presencas-nas-sessoes-ordinarias-de-{year}/"
        try:
            page = self.http.get(url)
        except Exception:
            return []
        soup = BeautifulSoup(page.text, "html.parser")
        records: list[PublicRecord] = []
        aggregate: dict[str, Counter[str]] = {}
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue
                name = cells[0]
                if not name or "nome do vereador" in name.casefold():
                    continue
                counts = aggregate.setdefault(name, Counter())
                for value in cells[1:]:
                    token = value.strip().upper()
                    if token in {"P", "A", "L"}:
                        counts[token] += 1
        for name, counts in sorted(aggregate.items()):
            records.append(
                PublicRecord(
                    id=f"camara:presenca:{year}:{self._slug(name)}",
                    kind="presenca",
                    title=f"Presenças de {name} em {year}",
                    year=year,
                    attributes={"vereador": name, "presente": counts.get("P", 0), "ausente": counts.get("A", 0), "licenciado": counts.get("L", 0)},
                    source=SourceRef(name=self.definition.name, url=url),
                )
            )
        return records

    def diary(self, *, year: int, limit: int = 250) -> list[PublicRecord]:
        page = self.http.get(DIARIO_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        records: list[PublicRecord] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            if "/doel/edicoes/" not in href or not href.lower().endswith(".pdf"):
                continue
            url = absolute_url(DIARIO_URL, href)
            if f"/{year}/" not in url or url in seen:
                continue
            seen.add(url)
            label = clean_text(anchor.get_text(" ", strip=True))
            context = clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else label)
            number_match = re.search(r"(\d{1,4})/\d{4}|ed[_-]?(\d+)", f"{label} {href}", re.I)
            number = next((g for g in number_match.groups() if g), "") if number_match else ""
            records.append(
                PublicRecord(
                    id=f"camara:diario:{year}:{number or sha256(url.encode()).hexdigest()[:10]}",
                    kind="diario",
                    title=f"Diário Oficial do Legislativo {number}/{year}" if number else label or "Diário Oficial do Legislativo",
                    summary=context or None,
                    date=parse_br_date(context),
                    year=year,
                    attributes={"pdf_url": url, "number": number},
                    source=SourceRef(name="Diário Oficial Eletrônico do Legislativo", url=url),
                )
            )
            if len(records) >= limit:
                break
        return records

    @staticmethod
    def _slug(value: str) -> str:
        return normalize_key(value).replace("_", "-")

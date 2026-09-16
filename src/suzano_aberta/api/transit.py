from __future__ import annotations

import copy
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, Response

from .settings import ApiSettings

TZ = ZoneInfo("America/Sao_Paulo")
LINE = "Linha 11-Coral"
STATIONS = ("Calmon Viana", "Suzano", "Jundiapeba", "Estudantes")
CPTM_STATUS_URLS = (
    "https://www.cptm.sp.gov.br/cptm",
    "https://www.cptm.sp.gov.br/Pages/Home.aspx?origem=menu",
)
CPTM_OCCURRENCE_DOWNLOAD_URL = "https://api.cptm.sp.gov.br/AppCPTM/v1/Ocorrencias/Baixar"
ARTESP_DOCS_URL = "https://ccm.artesp.sp.gov.br/metroferroviario/api/docs/"
ARTESP_STATUS_URL = "https://ccm.artesp.sp.gov.br/metroferroviario/api/status/"
ARTESP_OCCURRENCES_URL = "https://ccm.artesp.sp.gov.br/metroferroviario/api/ocorrencias/"
ARTESP_PUBLIC_STATUS_URL = "https://ccm.artesp.sp.gov.br/metroferroviario/status-linhas/"
STATUSES = (
    "Operação Normal",
    "Operação Parcial",
    "Operação Especial",
    "Operação Diferenciada",
    "Operação Transitória",
    "Operação com Impacto Pontual",
    "Impacto Pontual",
    "Velocidade Reduzida",
    "Maiores Intervalos",
    "Operação Paralisada",
    "Paralisada",
    "Atividade Programada",
    "Circulação de Trens",
    "Dados Indisponíveis",
    "Dados/Status Indisponíveis",
    "Status Desconhecido",
    "Status não disponível",
    "Operação Encerrada",
)
STATUS_RE = "|".join(sorted(map(re.escape, STATUSES), key=len, reverse=True))
LINE_RE = re.compile(
    rf"(?:Linha\s*11\s*[-–—]?\s*Coral|CORAL)\s*(?:[:\-–—]\s*)?({STATUS_RE})",
    re.I,
)
UPDATED_RE = re.compile(
    r"Atualizado\s+em\s*:?\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)",
    re.I,
)
SEGMENT_RE = re.compile(
    r"entre\s+(?:as\s+)?esta(?:ç|c)[õo]es?\s+([A-Za-zÀ-ÿ0-9 .'\-–—]+?)\s+e\s+([A-Za-zÀ-ÿ0-9 .'\-–—]+?)(?=\s*(?:,|\.|devido|por|com|$))",
    re.I,
)


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def _now() -> datetime:
    return datetime.now(TZ)


def _dt(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None

    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=TZ)
            return parsed.astimezone(TZ)
        except ValueError:
            pass

    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=TZ)
        except ValueError:
            pass
    return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value else None


def _normal(status: str) -> bool:
    return _fold(status) == "operacao normal"


def _source(
    source_id: str,
    name: str,
    url: str,
    role: str,
    *,
    structured: bool,
    requires_key: bool = False,
    live: bool = True,
    note: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": source_id,
        "name": name,
        "url": url,
        "role": role,
        "structured": structured,
        "requires_api_key": requires_key,
        "eligible_for_live_status": live,
        "verified_official": True,
    }
    if note:
        data["note"] = note
    return data


VERIFIED_SOURCES = (
    _source(
        "cptm-status",
        "CPTM — Situação das Linhas",
        CPTM_STATUS_URLS[0],
        "status_operacional",
        structured=False,
        note="Aceito somente quando a Linha 11/CORAL e um estado reconhecido aparecem explicitamente.",
    ),
    _source(
        "artesp-api-trilhos",
        "ARTESP — API Trilhos",
        ARTESP_DOCS_URL,
        "status_regulatorio",
        structured=True,
        requires_key=True,
        note="Desde 03/09/2026 a documentação declara escopo somente para linhas sob regulação direta da ARTESP.",
    ),
    _source(
        "artesp-status-publico",
        "ARTESP — Status das Linhas",
        ARTESP_PUBLIC_STATUS_URL,
        "status_regulatorio_fallback",
        structured=False,
        note="Aceito somente se a Linha 11 aparecer explicitamente.",
    ),
    _source(
        "cptm-ocorrencias-pdf",
        "CPTM — Comunicado de Ocorrência",
        CPTM_OCCURRENCE_DOWNLOAD_URL,
        "historico_documental",
        structured=False,
        live=False,
        note="Download oficial para ID já conhecido; não é usado como feed ao vivo porque não foi localizada documentação oficial de listagem pública.",
    ),
)


class TransitSourceUnavailable(RuntimeError):
    pass


def _line11(payload: Any) -> tuple[dict[str, Any], str | None] | None:
    if isinstance(payload, dict):
        companies = payload.get("empresas")
        if isinstance(companies, list):
            for company in companies:
                if not isinstance(company, dict):
                    continue
                for line in company.get("linhas") or []:
                    if not isinstance(line, dict):
                        continue
                    code = str(line.get("codigo") or "")
                    name = line.get("nome") or line.get("linha")
                    if code == "11" or "linha 11" in _fold(name):
                        return line, str(company.get("nome") or "").strip() or None

        for key, value in payload.items():
            if key in {"meta", "status", "classificacao"}:
                continue
            found = _line11(value)
            if found:
                return found

    elif isinstance(payload, list):
        for item in payload:
            found = _line11(item)
            if found:
                return found
    return None


def _occurrences(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        line = payload.get("linha")
        code = (
            str(line.get("codigo") or "")
            if isinstance(line, dict)
            else str(payload.get("linha_codigo") or "")
        )
        name = (
            str(line.get("nome") or "")
            if isinstance(line, dict)
            else str(line or payload.get("linha_nome") or "")
        )
        has_occurrence_shape = any(
            key in payload for key in ("descricao", "situacao", "data_hora", "timestamp")
        )
        if (
            code == "11" or "linha 11" in _fold(name) or "11-coral" in _fold(name)
        ) and has_occurrence_shape:
            found.append(payload)

        for value in payload.values():
            found.extend(_occurrences(value))

    elif isinstance(payload, list):
        for item in payload:
            found.extend(_occurrences(item))
    return found


def _segment(text: str) -> str | None:
    match = SEGMENT_RE.search(text or "")
    if not match:
        return None

    a, b = (
        re.sub(r"\s+", " ", value).strip(" .,-–—")
        for value in match.groups()
    )
    if not a or not b:
        return None
    if not any(_fold(station) in _fold(f"{a} {b}") for station in STATIONS):
        return None
    return f"{a} – {b}"


@dataclass(slots=True)
class _Cache:
    value: dict[str, Any]
    at: float


class Line11StatusService:
    def __init__(
        self,
        settings: ApiSettings,
        *,
        transport: httpx.BaseTransport | None = None,
        clock: Any = time.monotonic,
    ) -> None:
        self.settings = settings
        self.transport = transport
        self.clock = clock
        self.lock = threading.Lock()
        self.refresh_lock = threading.Lock()
        self.fresh: _Cache | None = None
        self.last_good: _Cache | None = None
        self.artesp: _Cache | None = None

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=httpx.Timeout(
                self.settings.transit_timeout_seconds,
                connect=min(5.0, self.settings.transit_timeout_seconds),
            ),
            follow_redirects=True,
            transport=self.transport,
            headers={
                "User-Agent": "SuzanoAberta/1.0 (+https://github.com/MukaSanches/suzano-aberta)",
                "Accept": "text/html,application/json;q=0.95,*/*;q=0.7",
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        )

    def get(self) -> dict[str, Any]:
        now = float(self.clock())
        with self.lock:
            if self.fresh and now - self.fresh.at < self.settings.transit_cache_seconds:
                out = copy.deepcopy(self.fresh.value)
                out["cache"] = {
                    "state": "hit",
                    "age_seconds": int(now - self.fresh.at),
                }
                return out

        with self.refresh_lock:
            now = float(self.clock())
            with self.lock:
                if self.fresh and now - self.fresh.at < self.settings.transit_cache_seconds:
                    out = copy.deepcopy(self.fresh.value)
                    out["cache"] = {
                        "state": "hit",
                        "age_seconds": int(now - self.fresh.at),
                    }
                    return out
            return self._refresh(now)

    def _refresh(self, now: float) -> dict[str, Any]:
        errors: list[dict[str, str]] = []
        current: dict[str, Any] | None = None

        try:
            current = self._cptm()
        except Exception as exc:
            errors.append({"source": "CPTM", "error": f"{type(exc).__name__}: {exc}"})

        if current is None or current.get("_source_stale") or not current.get("operation_normal", False):
            try:
                artesp = self._artesp(now)
                if current is None or (artesp and self._prefer_artesp(current, artesp)):
                    current = artesp
                elif artesp and artesp.get("occurrence"):
                    current = {
                        **current,
                        "occurrence": artesp["occurrence"],
                        "affected_segment": artesp.get("affected_segment"),
                        "reason": artesp.get("reason"),
                        "secondary_source": artesp.get("source"),
                    }
            except Exception as exc:
                errors.append({"source": "ARTESP", "error": f"{type(exc).__name__}: {exc}"})

        if current is not None:
            out = copy.deepcopy(current)
            source_stale = bool(out.pop("_source_stale", False))
            out.update(
                {
                    "availability": "stale" if source_stale else "available",
                    "stale": source_stale,
                    "focus_stations": list(STATIONS),
                    "checked_at": _iso(_now()),
                    "source_errors": errors,
                    "verified_sources": copy.deepcopy(list(VERIFIED_SOURCES)),
                    "cache": {"state": "miss", "age_seconds": 0},
                }
            )
            cached = _Cache(copy.deepcopy(out), now)
            with self.lock:
                self.fresh = cached
                if not source_stale:
                    self.last_good = cached
            return out

        with self.lock:
            stale = self.last_good
        if stale and now - stale.at <= self.settings.transit_stale_seconds:
            out = copy.deepcopy(stale.value)
            out.update(
                {
                    "availability": "stale",
                    "stale": True,
                    "checked_at": _iso(_now()),
                    "source_errors": errors,
                    "cache": {"state": "stale", "age_seconds": int(now - stale.at)},
                }
            )
            return out

        return {
            "line": LINE,
            "availability": "unavailable",
            "stale": False,
            "status": "Dados em tempo real indisponíveis",
            "classification": "indisponivel",
            "operation_normal": False,
            "occurrence": None,
            "affected_segment": None,
            "reason": None,
            "source_updated_at": None,
            "checked_at": _iso(_now()),
            "operator": None,
            "focus_stations": list(STATIONS),
            "source": None,
            "source_errors": errors,
            "verified_sources": copy.deepcopy(list(VERIFIED_SOURCES)),
            "cache": {"state": "empty", "age_seconds": 0},
        }

    @staticmethod
    def _prefer_artesp(cptm: dict[str, Any], artesp: dict[str, Any]) -> bool:
        a = _dt(artesp.get("source_updated_at"))
        c = _dt(cptm.get("source_updated_at"))
        return a is not None and (c is None or a > c)

    def _cptm(self) -> dict[str, Any]:
        failures: list[str] = []
        with self._client() as client:
            for url in CPTM_STATUS_URLS:
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    parsed = self._html(
                        response.text,
                        "CPTM — Situação das Linhas",
                        str(response.url),
                        "cptm-status",
                    )
                    if parsed:
                        return parsed
                    failures.append(f"{url}: Linha 11 sem status reconhecível")
                except (httpx.HTTPError, ValueError) as exc:
                    failures.append(f"{url}: {type(exc).__name__}")
        raise TransitSourceUnavailable(
            "; ".join(failures) or "CPTM não retornou estado utilizável"
        )

    def _artesp(self, now: float) -> dict[str, Any] | None:
        with self.lock:
            cached = self.artesp
        if cached and now - cached.at < self.settings.artesp_cache_seconds:
            return copy.deepcopy(cached.value)

        value = self._artesp_api() if self.settings.artesp_api_key else self._artesp_public()
        if value:
            with self.lock:
                self.artesp = _Cache(copy.deepcopy(value), now)
        return value

    def _artesp_public(self) -> dict[str, Any]:
        with self._client() as client:
            response = client.get(ARTESP_PUBLIC_STATUS_URL)
            response.raise_for_status()
        parsed = self._html(
            response.text,
            "ARTESP — Status das Linhas",
            str(response.url),
            "artesp-status-publico",
        )
        if not parsed:
            raise TransitSourceUnavailable(
                "A página pública da ARTESP não expôs a Linha 11 no conteúdo retornado."
            )
        return parsed

    def _artesp_api(self) -> dict[str, Any]:
        assert self.settings.artesp_api_key
        headers = {"Authorization": f"Api-Key {self.settings.artesp_api_key}"}
        with self._client() as client:
            response = client.get(ARTESP_STATUS_URL, headers=headers)
            response.raise_for_status()
            found = _line11(response.json())
            if not found:
                raise TransitSourceUnavailable(
                    "A API Trilhos respondeu, mas a Linha 11 não integra o escopo retornado."
                )

            line, operator = found
            raw_status = line.get("status")
            status_obj: dict[str, Any] = (
                cast(dict[str, Any], raw_status) if isinstance(raw_status, dict) else {}
            )
            status = str(status_obj.get("situacao") or line.get("situacao") or "").strip()
            if not status:
                raise TransitSourceUnavailable("A Linha 11 veio sem situação operacional.")

            out: dict[str, Any] = {
                "line": str(line.get("nome") or LINE),
                "status": status,
                "classification": str(status_obj.get("classificacao") or "").strip() or None,
                "operation_normal": (
                    bool(status_obj.get("operacao_normal"))
                    if "operacao_normal" in status_obj
                    else _normal(status)
                ),
                "occurrence": None,
                "affected_segment": None,
                "reason": None,
                "source_updated_at": _iso(_dt(status_obj.get("atualizado_em"))),
                "operator": operator,
                "source": _source(
                    "artesp-api-trilhos",
                    "ARTESP — API Trilhos",
                    ARTESP_STATUS_URL,
                    "status_regulatorio",
                    structured=True,
                    requires_key=True,
                ),
            }

            if not out["operation_normal"]:
                today = _now().date().isoformat()
                occurrence = client.get(
                    ARTESP_OCCURRENCES_URL,
                    headers=headers,
                    params={"data_inicio": today, "data_fim": today},
                )
                occurrence.raise_for_status()
                extra = self._latest_occurrence(occurrence.json())
                if extra:
                    out.update(extra)
            return out

    @staticmethod
    def _latest_occurrence(payload: Any) -> dict[str, Any] | None:
        items = _occurrences(payload)
        if not items:
            return None

        def stamp(item: dict[str, Any]) -> float:
            parsed = _dt(
                item.get("data_hora")
                or item.get("timestamp")
                or item.get("atualizado_em")
            )
            return parsed.timestamp() if parsed else 0.0

        item = max(items, key=stamp)
        description = str(item.get("descricao") or item.get("situacao") or "").strip()
        return {
            "occurrence": {
                "description": description or None,
                "occurred_at": _iso(_dt(item.get("data_hora") or item.get("timestamp"))),
                "status": str(item.get("situacao") or "").strip() or None,
            },
            "affected_segment": _segment(description),
            "reason": description or None,
        }

    def _html(
        self,
        html: str,
        source_name: str,
        source_url: str,
        source_id: str,
    ) -> dict[str, Any] | None:
        text = re.sub(
            r"\s+",
            " ",
            BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True),
        )
        match = LINE_RE.search(text)
        if not match:
            return None

        status = re.sub(r"\s+", " ", match.group(1)).strip()
        updated_match = UPDATED_RE.search(text)
        updated = _dt(updated_match.group(1)) if updated_match else None
        stale = bool(
            updated
            and max(0.0, (_now() - updated).total_seconds())
            > self.settings.transit_stale_seconds
        )
        return {
            "line": LINE,
            "status": status,
            "classification": "operacional" if _normal(status) else "alteracao",
            "operation_normal": _normal(status),
            "occurrence": None,
            "affected_segment": None,
            "reason": None,
            "source_updated_at": _iso(updated),
            "operator": None,
            "_source_stale": stale,
            "source": _source(
                source_id,
                source_name,
                source_url,
                "status_operacional"
                if source_id.startswith("cptm")
                else "status_regulatorio_fallback",
                structured=False,
            ),
        }


def install_transit_routes(app: FastAPI, settings: ApiSettings) -> None:
    service = Line11StatusService(settings)
    app.state.line11_status_service = service

    @app.get("/v1/transit/line-11", tags=["mobilidade"])
    def line_11_status(response: Response) -> dict[str, Any]:
        payload = service.get()
        if payload.get("availability") == "available":
            response.headers["Cache-Control"] = (
                f"public, max-age={min(settings.transit_cache_seconds, 120)}, "
                "stale-while-revalidate=300"
            )
        else:
            response.headers["Cache-Control"] = (
                "public, max-age=30, stale-while-revalidate=120"
            )
        return payload

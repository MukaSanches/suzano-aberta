from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from suzano_aberta.discovery import WebDiscovery
from suzano_aberta.http import PoliteHttpClient

LINE = "Linha 11–Coral"
FOCUS_STATIONS = ("Calmon Viana", "Suzano", "Jundiapeba", "Estudantes")
NEWS_QUERIES = (
    '"Linha 11-Coral" CPTM',
    '"Linha 11" Coral CPTM',
    '"Linha 11-Coral" Suzano',
    '"Estação Suzano" CPTM',
    '"Calmon Viana" CPTM',
    '"Jundiapeba" CPTM',
    '"Estudantes" CPTM "Linha 11"',
)

LOOKBACK_HOURS = 72
EVIDENCE_DAYS = 7

RECOVERY_PHRASES = (
    "volta ao normal",
    "voltou ao normal",
    "voltam ao normal",
    "normaliza",
    "normalizada",
    "normalizado",
    "normalmente",
    "operacao normal",
    "circulacao normal",
    "retomada",
    "retomado",
    "retoma",
    "restabelecida",
    "restabelecido",
    "resolvida",
    "resolvido",
)

DISRUPTION_PHRASES = (
    "sem circulacao",
    "circulacao interrompida",
    "interrompe",
    "interrompida",
    "interrompido",
    "paralisada",
    "paralisado",
    "pane",
    "falha",
    "problema",
    "incendio",
    "queda de energia",
    "falta de energia",
    "evacuacao",
    "evacuados",
    "suspensa",
    "suspenso",
)

ATTENTION_PHRASES = (
    "velocidade reduzida",
    "maiores intervalos",
    "operacao parcial",
    "restricao",
    "restricoes",
    "lentidao",
    "atraso",
    "atrasos",
    "manutencao",
    "alteracao",
    "alteracoes",
)

CONTEXT_PHRASES = (
    "ressarc",
    "indeniz",
    "contrato",
    "concessao",
    "licitacao",
    "investimento",
    "audiencia",
    "processo",
    "gestao",
    "privatiz",
)

REASON_LABELS = (
    ("energia", ("queda de energia", "falta de energia", "subestacao", "energia")),
    ("incêndio", ("incendio", "fogo")),
    ("falha técnica", ("falha", "pane", "problema tecnico")),
    ("clima", ("chuva", "temporal", "raio", "descarga atmosferica", "vento", "arvore")),
    ("manutenção", ("manutencao", "obra")),
    ("operação", ("intervalo", "velocidade reduzida", "circulacao", "operacao parcial")),
)


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


def parse_datetime(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    candidate = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        try:
            parsed = datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def clean_title(value: object) -> str:
    title = str(value or "").strip()
    return re.sub(r"\s+-\s+[^-]{2,100}$", "", title).strip()


def relevant(title: str) -> bool:
    text = normalize(title)
    if "linha 11" in text or "11 coral" in text:
        return True
    station_hit = any(normalize(station) in text for station in FOCUS_STATIONS)
    return station_hit and ("cptm" in text or "trem" in text or "estacao" in text)


def classify_title(title: str) -> str:
    text = normalize(title)
    recovery = any(phrase in text for phrase in RECOVERY_PHRASES)
    disruption = any(phrase in text for phrase in DISRUPTION_PHRASES)
    attention = any(phrase in text for phrase in ATTENTION_PHRASES)
    context = any(phrase in text for phrase in CONTEXT_PHRASES)

    # Manchetes de normalização frequentemente também citam o problema anterior.
    if recovery:
        return "normal"
    if context and not (disruption or attention):
        return "context"
    if context and not any(
        marker in text
        for marker in (
            "hoje",
            "agora",
            "nesta",
            "neste",
            "tem falha",
            "apresenta falha",
            "sem circulacao",
            "interrompe",
        )
    ):
        return "context"
    if disruption:
        return "disruption"
    if attention:
        return "attention"
    return "context"


def reason_for(title: str) -> str | None:
    text = normalize(title)
    for label, phrases in REASON_LABELS:
        if any(phrase in text for phrase in phrases):
            return label
    return None


def segment_for(title: str) -> str | None:
    text = normalize(title)
    mentioned = [station for station in FOCUS_STATIONS if normalize(station) in text]
    if len(mentioned) >= 2:
        return f"{mentioned[0]} – {mentioned[-1]}"
    if len(mentioned) == 1:
        return f"Região de {mentioned[0]}"
    if "linha 11" in text or "11 coral" in text:
        return "Linha 11–Coral (trecho exato não identificado pela manchete)"
    return None


def record_to_item(record: Any) -> dict[str, Any] | None:
    title = clean_title(getattr(record, "title", ""))
    if not title or not relevant(title):
        return None
    attributes = getattr(record, "attributes", {}) or {}
    source = getattr(record, "source", None)
    publisher = str(attributes.get("publicador") or getattr(source, "name", None) or "Fonte jornalística")
    url = str(getattr(source, "url", "") or "")
    published_at = getattr(record, "date", None)
    signal = classify_title(title)
    return {
        "title": title,
        "url": url,
        "publisher": publisher,
        "published_at": published_at,
        "signal": signal,
        "reason": reason_for(title),
        "affected_segment": segment_for(title),
        "query": str(attributes.get("consulta_descoberta") or ""),
    }


def deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in sorted(
        items,
        key=lambda value: parse_datetime(value.get("published_at")) or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        key = normalize(item.get("title"))
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def decide_status(items: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    cutoff = now.timestamp() - LOOKBACK_HOURS * 3600
    recent_operational = [
        item
        for item in items
        if item.get("signal") != "context"
        and (published := parse_datetime(item.get("published_at"))) is not None
        and published.timestamp() >= cutoff
    ]

    if not recent_operational:
        return {
            "level": "normal",
            "color": "green",
            "status": "Sem alerta recente nas notícias",
            "summary": (
                f"Nenhuma manchete operacional recente sobre a {LINE} ou o trecho de Suzano "
                f"indicou interrupção nas últimas {LOOKBACK_HOURS} horas."
            ),
            "confidence": "baixa",
            "affected_segment": None,
            "reason": None,
        }

    latest = recent_operational[0]
    published = parse_datetime(latest.get("published_at"))
    age_hours = max(0.0, (now - published).total_seconds() / 3600) if published else 10_000.0
    signal = str(latest.get("signal"))

    if signal == "normal":
        return {
            "level": "normal",
            "color": "green",
            "status": "Última notícia indica normalização",
            "summary": str(latest.get("title") or ""),
            "confidence": "média",
            "affected_segment": latest.get("affected_segment"),
            "reason": latest.get("reason"),
        }

    if signal == "disruption":
        if age_hours <= 6:
            level, color, status, confidence = (
                "problem",
                "red",
                "Possível problema recente",
                "alta",
            )
        elif age_hours <= 24:
            level, color, status, confidence = (
                "attention",
                "yellow",
                "Ocorrência recente; situação atual incerta",
                "média",
            )
        else:
            level, color, status, confidence = (
                "attention",
                "yellow",
                "Ocorrência noticiada sem confirmação recente de normalização",
                "baixa",
            )
        return {
            "level": level,
            "color": color,
            "status": status,
            "summary": str(latest.get("title") or ""),
            "confidence": confidence,
            "affected_segment": latest.get("affected_segment"),
            "reason": latest.get("reason"),
        }

    return {
        "level": "attention",
        "color": "yellow",
        "status": "Atenção: alteração recente noticiada",
        "summary": str(latest.get("title") or ""),
        "confidence": "média",
        "affected_segment": latest.get("affected_segment"),
        "reason": latest.get("reason"),
    }


def build(output: Path) -> dict[str, Any]:
    now = datetime.now(UTC)
    errors: list[str] = []
    records: list[Any] = []

    try:
        with PoliteHttpClient(timeout=15.0, min_interval=0.12) as http:
            discovery = WebDiscovery(http)
            records = discovery.discover_news(NEWS_QUERIES, per_query=20)
            failed_requests = discovery.stats.failed
    except Exception as exc:
        failed_requests = len(NEWS_QUERIES)
        errors.append(f"{type(exc).__name__}: {exc}")

    candidates = [item for record in records if (item := record_to_item(record)) is not None]
    items = deduplicate(candidates)

    evidence_cutoff = now.timestamp() - EVIDENCE_DAYS * 86400
    evidence = [
        item
        for item in items
        if (published := parse_datetime(item.get("published_at"))) is not None
        and published.timestamp() >= evidence_cutoff
    ][:6]

    if not records and failed_requests:
        decision = {
            "level": "unavailable",
            "color": "gray",
            "status": "Notícias indisponíveis no momento",
            "summary": "A busca de notícias não respondeu; o Suzano Aberta não estimou a operação.",
            "confidence": "indisponível",
            "affected_segment": None,
            "reason": None,
        }
        availability = "unavailable"
    else:
        decision = decide_status(items, now)
        availability = "available"

    publishers = sorted({str(item.get("publisher") or "") for item in evidence if item.get("publisher")})
    latest_news = next(
        (
            str(item.get("published_at"))
            for item in evidence
            if item.get("published_at")
        ),
        None,
    )
    payload: dict[str, Any] = {
        "schema": 1,
        "generated_at": now.isoformat(),
        "refresh_minutes": 30,
        "stale_after_minutes": 90,
        "method": "news-headline-estimate",
        "line": LINE,
        "focus_stations": list(FOCUS_STATIONS),
        "availability": availability,
        **decision,
        "latest_news_at": latest_news,
        "evidence": evidence,
        "publishers": publishers,
        "query_count": len(NEWS_QUERIES),
        "records_scanned": len(records),
        "relevant_items": len(items),
        "failed_requests": failed_requests,
        "errors": errors,
        "disclaimer": (
            "Estimativa automática baseada em manchetes recentes. Não é telemetria da CPTM, "
            "não confirma a circulação em tempo real e não substitui os canais oficiais."
        ),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera uma estimativa jornalística da Linha 11-Coral sem depender de API operacional."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("web/data/line11-news-status.json"),
    )
    args = parser.parse_args()
    payload = build(args.output)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "color": payload["color"],
                "confidence": payload["confidence"],
                "evidence": len(payload["evidence"]),
                "generated_at": payload["generated_at"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

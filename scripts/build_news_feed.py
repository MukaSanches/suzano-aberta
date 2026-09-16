from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from suzano_aberta.discovery import WebDiscovery
from suzano_aberta.http import PoliteHttpClient
from suzano_aberta.sources import PrefeituraSource

NEWS_QUERIES = (
    '"Suzano" SP',
    '"Prefeitura de Suzano"',
    '"Câmara de Suzano"',
    '"Suzano" transporte OR CPTM',
    '"Suzano" saúde OR educação',
    '"Suzano" emprego OR concurso',
    '"Suzano" obras OR infraestrutura',
    '"Suzano" cultura OR esporte',
)

TOPICS: dict[str, tuple[str, ...]] = {
    "Mobilidade": ("transporte", "onibus", "ônibus", "trem", "cptm", "mobilidade", "trânsito", "transito"),
    "Saúde": ("saude", "saúde", "ubs", "hospital", "vacina", "medic"),
    "Educação": ("educacao", "educação", "escola", "creche", "aluno", "professor", "ensino"),
    "Obras": ("obra", "recape", "pavimenta", "requalifica", "infraestrutura", "drenagem"),
    "Emprego": ("emprego", "vaga", "trabalho", "concurso", "estagio", "estágio"),
    "Segurança": ("seguranca", "segurança", "gcm", "guarda civil", "policia", "polícia"),
    "Cultura": ("cultura", "exposicao", "exposição", "teatro", "musica", "música", "livro"),
    "Esporte": ("esporte", "volei", "vôlei", "futebol", "campeonato", "atleta"),
    "Meio ambiente": ("meio ambiente", "ambiental", "residuo", "resíduo", "parque", "sustent"),
    "Administração": ("prefeitura", "camara", "câmara", "secretaria", "decreto", "lei", "licitacao", "licitação", "contrato"),
}

TARGET_ITEMS = 9
MIN_ITEMS = 5
MAX_PER_PUBLISHER = 2


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


def timestamp(value: str | None) -> float:
    if not value:
        return 0.0
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.timestamp()
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=UTC).timestamp()
        except ValueError:
            return 0.0


def clean_news_title(value: str) -> str:
    return re.sub(r"\s+-\s+[^-]{2,80}$", "", str(value or "").strip()).strip()


def topic_for(value: str) -> str:
    haystack = value.casefold()
    scores = {topic: sum(token.casefold() in haystack for token in tokens) for topic, tokens in TOPICS.items()}
    topic, score = max(scores.items(), key=lambda item: item[1])
    return topic if score else "Cidade"


def item_from_record(record: Any, origin: str) -> dict[str, Any]:
    attributes = getattr(record, "attributes", {}) or {}
    publisher = (
        attributes.get("publicador")
        or getattr(getattr(record, "source", None), "name", None)
        or "Fonte pública"
    )
    title = clean_news_title(getattr(record, "title", ""))
    summary = (getattr(record, "summary", None) or "")[:700]
    return {
        "title": title,
        "url": getattr(getattr(record, "source", None), "url", ""),
        "published_at": getattr(record, "date", None),
        "publisher": str(publisher),
        "origin": origin,
        "summary": summary,
        "topic": topic_for(f"{title} {summary}"),
    }


def item_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    source = payload.get("source") or {}
    attributes = payload.get("attributes") or {}
    title = clean_news_title(str(payload.get("title") or ""))
    summary = str(payload.get("summary") or "")[:700]
    url = str(source.get("url") or "")
    if not title or not url:
        return None
    publisher = attributes.get("publicador") or source.get("name") or "Fonte pública"
    origin = "prefeitura" if "suzano.sp.gov.br" in url.casefold() else "snapshot"
    return {
        "title": title,
        "url": url,
        "published_at": payload.get("date"),
        "publisher": str(publisher),
        "origin": origin,
        "summary": summary,
        "topic": topic_for(f"{title} {summary}"),
    }


def supplement_from_database(database: Path | None, candidates: list[dict[str, Any]]) -> int:
    if database is None or not database.exists():
        return 0
    conn = sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT payload_json FROM records WHERE active=1 "
            "AND (kind='pagina_web' OR kind='noticia') ORDER BY last_seen DESC LIMIT 350"
        ).fetchall()
    except sqlite3.DatabaseError:
        rows = []
    finally:
        conn.close()
    before = len(candidates)
    for (raw,) in rows:
        try:
            payload = json.loads(str(raw))
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        item = item_from_payload(payload)
        if item is None:
            continue
        haystack = normalize(f"{item['title']} {item['summary']} {item['publisher']}")
        if "suzano" in haystack:
            candidates.append(item)
    return len(candidates) - before


def title_tokens(item: dict[str, Any]) -> set[str]:
    return {token for token in normalize(str(item.get("title") or "")).split() if len(token) >= 3}


def near_duplicate(left: dict[str, Any], right: dict[str, Any]) -> bool:
    a = title_tokens(left)
    b = title_tokens(right)
    if not a or not b:
        return False
    overlap = len(a & b)
    union = len(a | b)
    return overlap >= 4 and union > 0 and (overlap / union) >= 0.58


def editorial_score(item: dict[str, Any], now_ts: float) -> float:
    published = timestamp(item.get("published_at"))
    age_hours = max(0.0, (now_ts - published) / 3600) if published else 10_000.0
    recency = max(0.0, 240.0 - min(age_hours, 240.0))
    official_bonus = 22.0 if item.get("origin") == "prefeitura" else 0.0
    relevance = 20.0 if "suzano" in normalize(f"{item.get('title')} {item.get('summary')}") else 0.0
    summary_bonus = min(8.0, len(str(item.get("summary") or "")) / 80.0)
    return recency + official_bonus + relevance + summary_bonus


def select_editorial(candidates: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    valid = [
        item for item in candidates
        if len(normalize(str(item.get("title") or ""))) >= 8
        and str(item.get("url") or "").startswith(("http://", "https://"))
    ]
    valid.sort(
        key=lambda item: (
            editorial_score(item, now.timestamp()),
            timestamp(item.get("published_at")),
            normalize(str(item.get("title") or "")),
        ),
        reverse=True,
    )

    selected: list[dict[str, Any]] = []
    publisher_counts: Counter[str] = Counter()
    for item in valid:
        publisher_key = normalize(str(item.get("publisher") or "fonte publica"))
        if publisher_counts[publisher_key] >= MAX_PER_PUBLISHER:
            continue
        if any(near_duplicate(item, existing) for existing in selected):
            continue
        selected.append(item)
        publisher_counts[publisher_key] += 1
        if len(selected) >= TARGET_ITEMS:
            break

    if len(selected) < MIN_ITEMS:
        for item in valid:
            if item in selected or any(near_duplicate(item, existing) for existing in selected):
                continue
            selected.append(item)
            if len(selected) >= MIN_ITEMS:
                break
    return selected[:TARGET_ITEMS]


def build(output: Path, database: Path | None = None) -> dict[str, Any]:
    now = datetime.now(UTC)
    candidates: list[dict[str, Any]] = []
    errors: list[str] = []

    with PoliteHttpClient(timeout=18.0, min_interval=0.12) as http:
        prefeitura = PrefeituraSource(http)
        try:
            for record in prefeitura.news(year=now.year, limit=60):
                candidates.append(item_from_record(record, "prefeitura"))
        except Exception as exc:
            errors.append(f"Prefeitura: {type(exc).__name__}: {exc}")

        discovery = WebDiscovery(http)
        try:
            for record in discovery.discover_news(NEWS_QUERIES, per_query=24):
                item = item_from_record(record, "web")
                haystack = normalize(f"{item['title']} {item['summary']} {item['publisher']}")
                if "suzano" in haystack:
                    candidates.append(item)
        except Exception as exc:
            errors.append(f"Web: {type(exc).__name__}: {exc}")

    snapshot_supplement = supplement_from_database(database, candidates)
    items = select_editorial(candidates, now)
    if len(items) < MIN_ITEMS:
        raise RuntimeError(
            f"O feed precisa publicar pelo menos {MIN_ITEMS} notícias; apenas {len(items)} foram encontradas. "
            + (" | ".join(errors) if errors else "")
        )

    publishers = {normalize(str(item.get("publisher") or "")) for item in items if item.get("publisher")}
    topics = sorted({str(item.get("topic") or "Cidade") for item in items})
    official_count = sum(item.get("origin") == "prefeitura" for item in items)
    payload = {
        "schema": 2,
        "generated_at": now.isoformat(),
        "refresh_minutes": 30,
        "count": len(items),
        "publisher_count": len(publishers),
        "official_count": official_count,
        "topics": topics,
        "snapshot_supplement": snapshot_supplement,
        "degraded": bool(errors),
        "items": items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica um digest autônomo, diverso e verificável sobre Suzano.")
    parser.add_argument("--output", type=Path, default=Path("web/data/news.json"))
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    result = build(args.output, args.database)
    print(json.dumps({
        "count": result["count"],
        "publishers": result["publisher_count"],
        "topics": len(result["topics"]),
        "generated_at": result["generated_at"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

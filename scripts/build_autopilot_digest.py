from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

LEGISLATION_KINDS = {"lei", "decreto", "proposicao"}
PROCUREMENT_KINDS = {"licitacao", "contrato", "ata"}
NEWS_KINDS = {"noticia", "pagina_web"}

TOPICS: dict[str, tuple[str, ...]] = {
    "Mobilidade": ("transporte", "onibus", "ônibus", "trem", "cptm", "mobilidade", "trânsito", "transito", "viaria", "viária"),
    "Saúde": ("saude", "saúde", "ubs", "hospital", "vacina", "medic", "vigilancia sanitaria", "vigilância sanitária"),
    "Educação": ("educacao", "educação", "escola", "creche", "aluno", "professor", "ensino"),
    "Obras": ("obra", "recape", "pavimenta", "requalifica", "infraestrutura", "drenagem"),
    "Emprego": ("emprego", "vaga", "trabalho", "concurso", "estagio", "estágio"),
    "Segurança": ("seguranca", "segurança", "gcm", "guarda civil", "policia", "polícia"),
    "Cultura": ("cultura", "exposicao", "exposição", "teatro", "musica", "música", "livro"),
    "Esporte": ("esporte", "volei", "vôlei", "futebol", "campeonato", "atleta"),
    "Meio ambiente": ("meio ambiente", "ambiental", "residuo", "resíduo", "parque", "arvore", "árvore", "sustent"),
    "Administração": ("prefeitura", "camara", "câmara", "secretaria", "decreto", "lei", "licitacao", "licitação", "contrato"),
}


def parse_date(value: Any, year: Any = None) -> datetime | None:
    raw = str(value or "").strip().replace("Z", "+00:00")
    if raw:
        try:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            try:
                return datetime.strptime(raw[:10], "%Y-%m-%d").replace(tzinfo=UTC)
            except ValueError:
                pass
    try:
        y = int(year)
    except (TypeError, ValueError):
        return None
    if 1900 <= y <= 2200:
        return datetime(y, 1, 1, tzinfo=UTC)
    return None


def topic_for(*parts: Any) -> str:
    haystack = " ".join(str(part or "") for part in parts).casefold()
    scores = {
        topic: sum(1 for token in tokens if token.casefold() in haystack)
        for topic, tokens in TOPICS.items()
    }
    topic, score = max(scores.items(), key=lambda item: item[1])
    return topic if score else "Cidade"


def compact(record: dict[str, Any]) -> dict[str, Any]:
    source = record.get("source") or {}
    kind = str(record.get("kind") or "registro")
    title = str(record.get("title") or "Registro público")
    record_id = str(record.get("id") or "")
    date = record.get("date") or (str(record.get("year")) if record.get("year") else None)
    if kind in PROCUREMENT_KINDS:
        href = f"./contratacoes.html?id={record_id}"
    elif kind in LEGISLATION_KINDS:
        href = f"./norma.html?id={record_id}"
    else:
        href = str(source.get("url") or "")
    return {
        "id": record_id,
        "kind": kind,
        "title": title,
        "date": date,
        "source": str(source.get("name") or "Fonte pública"),
        "href": href,
        "topic": topic_for(title, record.get("summary"), record.get("attributes")),
    }


def select_latest(records: list[dict[str, Any]], kinds: set[str] | None, limit: int) -> list[dict[str, Any]]:
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for record in records:
        kind = str(record.get("kind") or "")
        if kinds is not None and kind not in kinds:
            continue
        when = parse_date(record.get("date"), record.get("year"))
        if when is None:
            continue
        candidates.append((when, record))
    candidates.sort(key=lambda item: (item[0], str(item[1].get("id") or "")), reverse=True)
    return [compact(record) for _, record in candidates[:limit]]


def build(database: Path, output: Path, news_path: Path | None = None) -> dict[str, Any]:
    now = datetime.now(UTC)
    conn = sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT payload_json FROM records WHERE active=1").fetchall()
    finally:
        conn.close()

    records: list[dict[str, Any]] = []
    for (payload_json,) in rows:
        try:
            payload = json.loads(str(payload_json))
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            records.append(payload)

    dated: list[tuple[datetime, dict[str, Any]]] = []
    for record in records:
        when = parse_date(record.get("date"), record.get("year"))
        if when is not None:
            dated.append((when, record))

    last_7 = now - timedelta(days=7)
    last_30 = now - timedelta(days=30)
    recent_7 = sum(when >= last_7 for when, _ in dated)
    recent_30 = sum(when >= last_30 for when, _ in dated)
    recent_legislation = sum(when >= last_30 and str(record.get("kind") or "") in LEGISLATION_KINDS for when, record in dated)
    recent_procurements = sum(when >= last_30 and str(record.get("kind") or "") in PROCUREMENT_KINDS for when, record in dated)

    source_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    for record in records:
        source = record.get("source") or {}
        source_name = str(source.get("name") or "").strip()
        if source_name:
            source_counter[source_name] += 1
        topic_counter[topic_for(record.get("title"), record.get("summary"), record.get("attributes"))] += 1

    news_payload: dict[str, Any] = {}
    if news_path and news_path.exists():
        try:
            raw = json.loads(news_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                news_payload = raw
        except (OSError, json.JSONDecodeError):
            news_payload = {}

    latest_source_date = max((when for when, _ in dated), default=None)
    freshness_hours = None
    if latest_source_date is not None:
        freshness_hours = max(0, round((now - latest_source_date).total_seconds() / 3600, 1))

    payload = {
        "schema": 1,
        "generated_at": now.isoformat(),
        "mode": "deterministic-autopilot",
        "refresh": {
            "news_minutes": 30,
            "portal_minutes": 30,
            "incremental_hours": 4,
            "full_index_hours": 24,
        },
        "pulse": {
            "records": len(records),
            "sources": len(source_counter),
            "dated_last_7_days": recent_7,
            "dated_last_30_days": recent_30,
            "legislation_last_30_days": recent_legislation,
            "procurements_last_30_days": recent_procurements,
            "latest_record_at": latest_source_date.isoformat() if latest_source_date else None,
            "latest_record_age_hours": freshness_hours,
            "news_publishers": int(news_payload.get("publisher_count") or 0),
            "news_topics": len(news_payload.get("topics") or []),
        },
        "briefing": [
            {
                "label": "Últimos 7 dias",
                "value": recent_7,
                "text": "registros do acervo possuem data neste período",
            },
            {
                "label": "Legislação · 30 dias",
                "value": recent_legislation,
                "text": "leis, decretos ou proposições datados no período",
            },
            {
                "label": "Contratações · 30 dias",
                "value": recent_procurements,
                "text": "licitações, contratos ou atas datados no período",
            },
            {
                "label": "Cobertura",
                "value": len(source_counter),
                "text": "fontes distintas aparecem no índice atual",
            },
        ],
        "latest": select_latest(records, None, 8),
        "legislation": select_latest(records, LEGISLATION_KINDS, 6),
        "procurements": select_latest(records, PROCUREMENT_KINDS, 6),
        "top_sources": [
            {"name": name, "records": count}
            for name, count in source_counter.most_common(8)
        ],
        "top_topics": [
            {"name": name, "records": count}
            for name, count in topic_counter.most_common(8)
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o briefing autônomo e determinístico do portal.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("web/data/autopilot.json"))
    parser.add_argument("--news", type=Path, default=Path("web/data/news.json"))
    args = parser.parse_args()
    payload = build(args.database, args.output, args.news)
    print(json.dumps({"records": payload["pulse"]["records"], "sources": payload["pulse"]["sources"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

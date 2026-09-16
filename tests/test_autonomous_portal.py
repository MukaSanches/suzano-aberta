from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.build_autopilot_digest import build as build_autopilot
from scripts.build_news_feed import near_duplicate, select_editorial, topic_for


def _record(
    record_id: str,
    kind: str,
    title: str,
    date: str,
    source: str,
    url: str,
) -> dict[str, object]:
    return {
        "id": record_id,
        "kind": kind,
        "title": title,
        "date": date,
        "year": int(date[:4]),
        "summary": f"Registro público de Suzano sobre {title}",
        "source": {"name": source, "url": url},
        "attributes": {},
    }


def test_autopilot_builds_briefing_and_radars(tmp_path: Path) -> None:
    database = tmp_path / "portal.sqlite3"
    conn = sqlite3.connect(database)
    conn.execute("CREATE TABLE records (payload_json TEXT NOT NULL, active INTEGER NOT NULL)")
    now = datetime.now(UTC)
    records = [
        _record("lei:1", "lei", "Lei 100 sobre educação", now.date().isoformat(), "Câmara", "https://example.test/lei"),
        _record("prop:1", "proposicao", "Proposição sobre transporte", (now - timedelta(days=2)).date().isoformat(), "Câmara", "https://example.test/prop"),
        _record("pncp:1", "contrato", "Contrato de manutenção de escola", (now - timedelta(days=1)).date().isoformat(), "PNCP", "https://pncp.gov.br/app/contratos/1"),
        _record("arquivo:1", "arquivo", "Documento de saúde", (now - timedelta(days=4)).date().isoformat(), "Prefeitura", "https://example.test/doc"),
    ]
    conn.executemany(
        "INSERT INTO records(payload_json, active) VALUES (?, 1)",
        [(json.dumps(record, ensure_ascii=False),) for record in records],
    )
    conn.commit()
    conn.close()

    news = tmp_path / "news.json"
    news.write_text(
        json.dumps({"publisher_count": 3, "topics": ["Educação", "Mobilidade"]}),
        encoding="utf-8",
    )
    output = tmp_path / "autopilot.json"
    payload = build_autopilot(database, output, news)

    assert payload["mode"] == "deterministic-autopilot"
    assert payload["pulse"]["records"] == 4
    assert payload["pulse"]["sources"] == 3
    assert payload["pulse"]["news_publishers"] == 3
    assert len(payload["briefing"]) == 4
    assert payload["legislation"]
    assert payload["procurements"]
    assert output.exists()


def test_editorial_selection_deduplicates_and_limits_publishers() -> None:
    now = datetime.now(UTC)
    candidates = [
        {
            "title": "Suzano amplia atendimento de saúde nas unidades municipais",
            "url": "https://example.test/a1",
            "published_at": now.isoformat(),
            "publisher": "Fonte A",
            "origin": "web",
            "summary": "Suzano amplia atendimento de saúde.",
            "topic": "Saúde",
        },
        {
            "title": "Suzano amplia atendimento de saúde em unidades municipais",
            "url": "https://example.test/a2",
            "published_at": (now - timedelta(minutes=1)).isoformat(),
            "publisher": "Fonte B",
            "origin": "web",
            "summary": "Mesma pauta publicada por outra fonte.",
            "topic": "Saúde",
        },
    ]
    distinct = [
        ("Fonte A", "Suzano anuncia mudanças no transporte coletivo municipal", "Mobilidade"),
        ("Fonte A", "Escolas de Suzano recebem nova programação pedagógica", "Educação"),
        ("Fonte B", "Suzano divulga novas vagas de emprego para moradores", "Emprego"),
        ("Fonte C", "Obras de drenagem avançam em bairro de Suzano", "Obras"),
        ("Fonte D", "Agenda cultural de Suzano ganha exposição neste fim de semana", "Cultura"),
        ("Fonte E", "Projeto ambiental amplia plantio de árvores em Suzano", "Meio ambiente"),
    ]
    for index, (publisher, title, topic) in enumerate(distinct, start=1):
        candidates.append(
            {
                "title": title,
                "url": f"https://example.test/{index}",
                "published_at": (now - timedelta(minutes=index + 2)).isoformat(),
                "publisher": publisher,
                "origin": "web",
                "summary": f"Informação pública distinta sobre {topic} em Suzano.",
                "topic": topic,
            }
        )

    selected = select_editorial(candidates, now)
    assert len(selected) == 5
    assert sum(item["publisher"] == "Fonte A" for item in selected) <= 2
    assert not (
        any(item["url"] == "https://example.test/a1" for item in selected)
        and any(item["url"] == "https://example.test/a2" for item in selected)
    )


def test_near_duplicate_and_topic_classifier() -> None:
    left = {"title": "Suzano abre novas vagas de emprego nesta semana"}
    right = {"title": "Suzano abre novas vagas de emprego durante esta semana"}
    assert near_duplicate(left, right)
    assert topic_for("Prefeitura amplia vacinação nas UBS de Suzano") == "Saúde"
    assert topic_for("CPTM e transporte em Suzano") == "Mobilidade"

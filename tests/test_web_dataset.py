from __future__ import annotations

import gzip
import json
import sqlite3
from pathlib import Path

from scripts.build_web_dataset import build


def make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE records (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
          source_name TEXT NOT NULL, source_url TEXT NOT NULL,
          first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
          content_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1
        );
        """
    )
    payloads = [
        {
            "id": "proposicao:1",
            "kind": "proposicao",
            "title": "Educação em Suzano",
            "summary": "Transporte escolar",
            "date": "2026-05-10",
            "year": 2026,
            "attributes": {"tema": "educação pública", "ementa": "Política municipal de transporte escolar"},
            "source": {"name": "Fonte de teste", "url": "https://example.test/proposicao"},
        },
        {
            "id": "lei:1",
            "kind": "lei",
            "title": "Lei de educação",
            "summary": "Norma municipal",
            "date": "2026-09-15",
            "year": 2026,
            "attributes": {"document_url": "https://example.test/lei.pdf"},
            "source": {"name": "Fonte de teste", "url": "https://example.test/lei.pdf"},
        },
        {
            "id": "arquivo:1",
            "kind": "arquivo",
            "title": "Planilha de contratos",
            "summary": "Arquivo de dados",
            "date": "2025-02-01",
            "year": 2025,
            "attributes": {"document_url": "https://example.test/contratos.xlsx"},
            "source": {"name": "Fonte de teste", "url": "https://example.test/contratos.xlsx"},
        },
    ]
    for payload in payloads:
        conn.execute(
            "INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,1)",
            (
                payload["id"],
                payload["kind"],
                payload["title"],
                payload["source"]["name"],
                payload["source"]["url"],
                "2026-09-15T10:00:00+00:00",
                "2026-09-15T10:00:00+00:00",
                payload["id"],
                json.dumps(payload, ensure_ascii=False),
            ),
        )
    conn.commit()
    conn.close()


def read_gzip_json(path: Path) -> object:
    return json.loads(gzip.decompress(path.read_bytes()))


def test_build_web_dataset(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    make_db(database)
    output = tmp_path / "web" / "data"

    manifest = build(database, output, max_tokens_per_record=100)

    assert manifest["records"] == 3
    assert manifest["documents"] == 2
    assert manifest["legislation"] == 2
    assert manifest["years_covered"] == 2
    assert manifest["schema"] == 2
    assert manifest["default_sort"] == "date_desc"
    assert manifest["record_fields"][-1] == "search_context"

    lexicon = read_gzip_json(output / "lexicon.json.gz")
    assert "educacao" in lexicon
    assert (output / "records.json.gz").exists()
    assert len(list((output / "index").glob("*.json.gz"))) == 32

    records = read_gzip_json(output / "records.json.gz")
    assert [row[0] for row in records] == ["lei:1", "proposicao:1", "arquivo:1"]
    assert records[0][9] == "2026-09-15"
    assert records[0][10] == "record"
    assert len(records[1]) == 12
    assert "transporte escolar" in records[1][11].casefold()
    assert "educação pública" in records[1][11].casefold()

    api_root = output.parent / "api"
    ready = json.loads((api_root / "health" / "ready.json").read_text(encoding="utf-8"))
    assert ready["ready"] is True
    assert ready["documents"] == 2
    assert ready["legislation"] == 2

    document_api = read_gzip_json(api_root / "v1" / "documentos.json.gz")
    assert [item["id"] for item in document_api["items"]] == ["lei:1", "arquivo:1"]

    legislation_api = read_gzip_json(api_root / "v1" / "legislacao.json.gz")
    assert [item["id"] for item in legislation_api["items"]] == ["lei:1", "proposicao:1"]

    day_api = read_gzip_json(api_root / "v1" / "by-date" / "2026" / "09" / "15.json.gz")
    assert day_api["count"] == 1
    assert day_api["items"][0]["id"] == "lei:1"

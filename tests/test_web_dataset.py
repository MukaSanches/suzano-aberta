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
    payload = {
        "id": "proposicao:1",
        "kind": "proposicao",
        "title": "Educação em Suzano",
        "summary": "Transporte escolar",
        "date": "2026-09-15",
        "year": 2026,
        "attributes": {"tema": "educação pública"},
        "source": {"name": "Fonte de teste", "url": "https://example.test/item"},
    }
    conn.execute(
        "INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,1)",
        (
            "proposicao:1",
            "proposicao",
            "Educação em Suzano",
            "Fonte de teste",
            "https://example.test/item",
            "2026-09-15",
            "2026-09-15",
            "abc",
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def test_build_web_dataset(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    make_db(database)
    output = tmp_path / "data"

    manifest = build(database, output, max_tokens_per_record=100)

    assert manifest["records"] == 1
    assert manifest["years_covered"] == 1
    lexicon = json.loads(gzip.decompress((output / "lexicon.json.gz").read_bytes()))
    assert "educacao" in lexicon
    assert (output / "records.json.gz").exists()
    assert len(list((output / "index").glob("*.json.gz"))) == 32

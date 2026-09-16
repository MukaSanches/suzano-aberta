from __future__ import annotations

import gzip
import json
from pathlib import Path

from scripts.build_browser_legislation import build


def _write_source(path: Path) -> None:
    payload = {
        "meta": {"generated_at": "2026-09-16T12:00:00Z"},
        "items": [
            {
                "id": "lei-2",
                "kind": "lei",
                "title": "Lei 2/2026",
                "summary": "Dispõe sobre transporte escolar",
                "effective_date": "2026-09-10",
                "year": 2026,
                "source": {"name": "Câmara Municipal - Legislação", "url": "https://example.test/lei-2"},
                "attributes": {"heavy": "must-not-leak-to-browser-feed"},
            },
            {
                "id": "lei-1",
                "kind": "lei",
                "title": "Lei 1/2026",
                "summary": "Dispõe sobre saúde",
                "effective_date": "2026-08-01",
                "year": 2026,
                "source": {"name": "Câmara Municipal - Legislação", "url": "https://example.test/lei-1"},
                "attributes": {"heavy": "must-not-leak-to-browser-feed"},
            },
            {
                "id": "dec-1",
                "kind": "decreto",
                "title": "Decreto 1/2026",
                "summary": "Regulamentação",
                "effective_date": "2026-09-11",
                "year": 2026,
                "source": {"name": "Prefeitura de Suzano", "url": "https://example.test/dec-1"},
            },
            {
                "id": "prop-1",
                "kind": "proposicao",
                "title": "Projeto de Lei 1/2026",
                "summary": "Proposição de teste",
                "effective_date": "2026-09-12",
                "year": 2026,
                "source": {"name": "Câmara Municipal", "url": "https://example.test/prop-1"},
            },
        ],
    }
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


def test_builder_emits_small_sorted_category_shards(tmp_path: Path) -> None:
    source = tmp_path / "legislacao.json.gz"
    output = tmp_path / "legislation.json"
    _write_source(source)

    meta = build(source, output)

    assert meta["schema"] == 2
    assert meta["counts_by_kind"] == {"decreto": 1, "lei": 2, "proposicao": 1}
    assert meta["shards"] == {
        "lei": "legislation-lei.json",
        "decreto": "legislation-decreto.json",
        "proposicao": "legislation-proposicao.json",
    }

    index = json.loads((tmp_path / "legislation-index.json").read_text(encoding="utf-8"))
    assert "items" not in index
    assert index["meta"]["total"] == 4

    laws = json.loads((tmp_path / "legislation-lei.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in laws["items"]] == ["lei-2", "lei-1"]
    assert laws["meta"]["scope_kind"] == "lei"
    assert laws["meta"]["scope_total"] == 2
    assert all("attributes" not in item for item in laws["items"])

    decrees = json.loads((tmp_path / "legislation-decreto.json").read_text(encoding="utf-8"))
    proposals = json.loads((tmp_path / "legislation-proposicao.json").read_text(encoding="utf-8"))
    assert len(decrees["items"]) == 1
    assert len(proposals["items"]) == 1


def test_page_uses_worker_fast_path() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "web" / "legislacao.html").read_text(encoding="utf-8")
    client = (root / "web" / "assets" / "legislation-v9.js").read_text(encoding="utf-8")
    worker = (root / "web" / "assets" / "legislation-worker-v9.js").read_text(encoding="utf-8")
    service_worker = (root / "web" / "sw.js").read_text(encoding="utf-8")

    assert "legislation-v9.js" in html
    assert "legislation-v8.js" not in html
    assert 'new Worker("./assets/legislation-worker-v9.js"' in client
    assert "legislation-index.json" in worker
    assert "legislation-${kind}.json" in worker
    assert "legislation-v9.js" in service_worker
    assert "legislation-worker-v9.js" in service_worker

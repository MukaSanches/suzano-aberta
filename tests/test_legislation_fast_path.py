from __future__ import annotations

import gzip
import json
from pathlib import Path

from scripts.build_browser_legislation import build


def _write_source(path: Path) -> None:
    payload = {
        "meta": {"generated_at": "2026-09-16T12:00:00Z"},
        "items": [
            {"id":"lei-2","kind":"lei","title":"Lei 2/2026","summary":"Dispõe sobre transporte escolar","effective_date":"2026-09-10","year":2026,"source":{"name":"Câmara Municipal - Legislação","url":"https://example.test/lei-2"},"attributes":{"heavy":"must-not-leak-to-browser-feed"}},
            {"id":"lei-1","kind":"lei","title":"Lei 1/2026","summary":"Dispõe sobre saúde","effective_date":"2026-08-01","year":2026,"source":{"name":"Câmara Municipal - Legislação","url":"https://example.test/lei-1"},"attributes":{"heavy":"must-not-leak-to-browser-feed"}},
            {"id":"dec-1","kind":"decreto","title":"Decreto 1/2026","summary":"Regulamentação","effective_date":"2026-09-11","year":2026,"source":{"name":"Prefeitura de Suzano","url":"https://example.test/dec-1"}},
            {"id":"prop-1","kind":"proposicao","title":"Projeto de Lei 1/2026","summary":"Proposição de teste","effective_date":"2026-09-12","year":2026,"source":{"name":"Câmara Municipal","url":"https://example.test/prop-1"}},
        ],
    }
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


def test_builder_emits_sorted_shards_and_zero_roundtrip_bootstrap(tmp_path: Path) -> None:
    source = tmp_path / "legislacao.json.gz"
    output = tmp_path / "legislation.json"
    page = tmp_path / "legislacao.html"
    page.write_text('<html><head><script defer src="./assets/legislation-v9.js"></script></head><body><p class="result-count" data-result-count>Carregando…</p><div data-results aria-live="polite"><p class="loading">Preparando índice legislativo rápido…</p></div></body></html>', encoding="utf-8")
    _write_source(source)
    meta = build(source, output, page=page)
    assert meta["schema"] == 3
    assert meta["counts_by_kind"] == {"decreto": 1, "lei": 2, "proposicao": 1}
    laws = json.loads((tmp_path / "legislation-lei.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in laws["items"]] == ["lei-2", "lei-1"]
    assert all("attributes" not in item for item in laws["items"])
    bootstrap = json.loads((tmp_path / "legislation-bootstrap.json").read_text(encoding="utf-8"))
    assert bootstrap["kind"] == "lei"
    assert [item["id"] for item in bootstrap["items"]] == ["lei-2", "lei-1"]
    built_page = page.read_text(encoding="utf-8")
    assert 'id="legislation-bootstrap"' in built_page
    assert 'data-bootstrap-results="true"' in built_page
    assert "Lei 2/2026" in built_page
    assert "Preparando índice legislativo rápido" not in built_page


def test_browser_keeps_bootstrap_visible_and_warms_worker() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "web" / "legislacao.html").read_text(encoding="utf-8")
    client = (root / "web" / "assets" / "legislation-v9.js").read_text(encoding="utf-8")
    worker = (root / "web" / "assets" / "legislation-worker-v9.js").read_text(encoding="utf-8")
    service_worker = (root / "web" / "sw.js").read_text(encoding="utf-8")
    assert "legislation-v9.js" in html
    assert 'new Worker("./assets/legislation-worker-v9.js"' in client
    assert 'data-bootstrap-results' in client
    assert 'requestIdleCallback' in client
    assert 'postMessage({ type: "warm"' in client
    assert 'target.innerHTML = `<p class="loading"' not in client
    assert '{ cache: "default" }' in worker
    assert 'cache: "no-cache"' not in worker
    assert 'type === "warm"' in worker
    assert "legislation-v9.js" in service_worker
    assert "legislation-worker-v9.js" in service_worker

from __future__ import annotations

from pathlib import Path

from scripts.inject_line11_module import inject_homepage


def test_home_injection_is_idempotent_and_loads_shared_widget(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text('<html><head></head><body><main><section class="section" aria-labelledby="servicos-title"></section></main></body></html>', encoding="utf-8")
    assert inject_homepage(page) is True
    assert inject_homepage(page) is False
    text = page.read_text(encoding="utf-8")
    assert text.count("line11-module:start") == 1
    assert './assets/line11.css' in text
    assert './assets/line11.js' in text
    assert 'data-line11-widget' in text
    assert './linha-11.html' in text


def test_line11_page_and_client_preserve_unavailable_and_stale_states() -> None:
    root = Path(__file__).resolve().parents[1]
    page = (root / "web" / "linha-11.html").read_text(encoding="utf-8")
    client = (root / "web" / "assets" / "line11.js").read_text(encoding="utf-8")
    sw = (root / "web" / "sw.js").read_text(encoding="utf-8")
    for station in ("Calmon Viana", "Suzano", "Jundiapeba", "Estudantes"):
        assert station in page or station in client
    assert 'data-line11-widget' in page
    assert '/v1/transit/line-11' in client
    assert 'availability==="unavailable"' in client
    assert 'availability:"stale"' in client
    assert 'source_updated_at' in client and 'checked_at' in client
    assert "linha-11.html" in sw
    assert "line11.js" in sw and "line11.css" in sw

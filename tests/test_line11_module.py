from __future__ import annotations

from pathlib import Path

from scripts.inject_line11_module import inject_homepage


def test_home_injection_is_idempotent_and_loads_shared_widget(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text(
        '<html><head></head><body><main><section class="section" aria-labelledby="servicos-title"></section></main></body></html>',
        encoding="utf-8",
    )
    assert inject_homepage(page) is True
    assert inject_homepage(page) is False
    text = page.read_text(encoding="utf-8")
    assert text.count("line11-module:start") == 1
    assert './assets/line11.css' in text
    assert './assets/line11.js' in text
    assert 'data-line11-widget' in text
    assert './linha-11.html' in text
    assert 'Mobilidade por notícias' in text
    assert 'Estimativa automática baseada nas notícias mais recentes' in text


def test_line11_page_and_client_use_news_estimate_not_operational_api() -> None:
    root = Path(__file__).resolve().parents[1]
    page = (root / "web" / "linha-11.html").read_text(encoding="utf-8")
    client = (root / "web" / "assets" / "line11.js").read_text(encoding="utf-8")
    sw = (root / "web" / "sw.js").read_text(encoding="utf-8")

    for station in ("Calmon Viana", "Suzano", "Jundiapeba", "Estudantes"):
        assert station in page or station in client

    assert 'data-line11-widget' in page
    assert 'estimativa automática baseada em notícias recentes' in page.casefold()
    assert 'line11-news-status.json' in client
    assert 'news-headline-estimate' in client
    assert '/v1/transit/line-11' not in client
    assert 'api_base' not in client
    assert 'payload.color === "red"' in client
    assert 'payload.color === "yellow"' in client
    assert 'payload.color === "green"' in client
    assert 'Não é telemetria da CPTM' in page
    assert "linha-11.html" in sw
    assert "line11.js" in sw and "line11.css" in sw

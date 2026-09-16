from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v11_is_composed_after_preserved_v4_core() -> None:
    v4 = read("web/assets/portal-v4.css")
    v11 = read("web/assets/portal-v11.css")

    assert '@import url("./portal-v4-core.css");' in v4
    assert '@import url("./portal-v11.css");' in v4
    assert '@import url("./portal-v11-core.css");' in v11
    assert '@import url("./portal-v11-compat.css");' in v11

    for asset in (
        "web/assets/portal-v4-core.css",
        "web/assets/portal-v11-core.css",
        "web/assets/portal-v11-compat.css",
        "web/assets/portal-v11.js",
    ):
        path = ROOT / asset
        assert path.exists(), asset
        assert path.stat().st_size > 0, asset


def test_home_keeps_civic_independence_and_data_contracts() -> None:
    html = read("web/index.html")

    assert "Projeto cívico independente." in html
    assert "Não é um portal oficial da Prefeitura ou da Câmara de Suzano." in html
    assert 'data-search-form' in html
    assert 'data-search-home="true"' in html
    assert 'data-news-list' in html
    assert 'data-autopilot-briefing' in html
    assert 'data-autopilot-legislation' in html
    assert 'data-autopilot-procurements' in html
    assert 'data-network-status' in html
    assert 'data-a11y-popover' in html
    assert 'data-recent-searches' in html
    assert './assets/portal-v11.css' in html
    assert './assets/portal-v11.js' in html


def test_home_is_task_first_and_keeps_official_source_warning() -> None:
    html = read("web/index.html")

    expected_tasks = (
        "Consultar uma lei",
        "Ver uma contratação",
        "Achar um documento",
        "Ver o que é recente",
        "Conferir o sistema",
    )
    for task in expected_tasks:
        assert task in html

    assert "A publicação mantida pelo órgão responsável continua sendo a referência oficial." in html
    assert "Para efeitos oficiais, confirme a informação na fonte indicada em cada registro." in html


def test_local_first_enhancements_do_not_add_trackers() -> None:
    javascript = read("web/assets/portal-v11.js")
    combined = (read("web/index.html") + javascript).lower()

    assert "localstorage" in javascript.lower()
    assert "beforeinstallprompt" in javascript
    assert "navigator.onLine" in javascript
    assert "google-analytics" not in combined
    assert "googletagmanager" not in combined
    assert "facebook.com/tr" not in combined
    assert "document.cookie" not in javascript


def test_manifest_exposes_public_service_shortcuts() -> None:
    manifest = json.loads(read("web/manifest.webmanifest"))

    assert manifest["lang"] == "pt-BR"
    assert manifest["theme_color"] == "#081f33"
    shortcuts = {item["url"] for item in manifest.get("shortcuts", [])}
    assert {
        "./explorar.html",
        "./legislacao.html",
        "./contratacoes.html",
        "./status.html",
    }.issubset(shortcuts)


def test_service_worker_caches_entire_composed_civic_shell() -> None:
    sw = read("web/sw.js")

    assert 'const CACHE = "suzano-aberta-shell-v12"' in sw
    for asset in (
        "portal-v4-core.css",
        "portal-v11.css",
        "portal-v11-core.css",
        "portal-v11-compat.css",
        "portal-v11.js",
    ):
        assert asset in sw

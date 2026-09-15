from __future__ import annotations

import gzip
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path("web")
PAGES = [
    "index.html",
    "explorar.html",
    "legislacao.html",
    "norma.html",
    "contratacoes.html",
    "sobre.html",
    "desenvolvedores.html",
    "status.html",
    "acessibilidade.html",
    "404.html",
]


class Inspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.has_main = False
        self.has_h1 = False
        self.has_lang = False
        self.images_without_alt: list[str] = []
        self._html_seen = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "html":
            self._html_seen = True
            self.has_lang = bool(data.get("lang"))
        if tag == "main":
            self.has_main = True
        if tag == "h1":
            self.has_h1 = True
        if tag == "a" and data.get("href"):
            self.links.append(str(data["href"]))
        if tag == "img" and "alt" not in data:
            self.images_without_alt.append(str(data.get("src") or "<sem src>"))
        if data.get("id"):
            self.ids.add(str(data["id"]))


def fail(message: str) -> None:
    print(f"ERRO: {message}", file=sys.stderr)
    raise SystemExit(1)


def inspect_page(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    parser = Inspector()
    parser.feed(text)
    if not parser._html_seen or not parser.has_lang:
        fail(f"{path}: <html lang> ausente")
    if not parser.has_main:
        fail(f"{path}: elemento <main> ausente")
    if not parser.has_h1:
        fail(f"{path}: h1 ausente")
    if parser.images_without_alt:
        fail(f"{path}: imagens sem alt: {parser.images_without_alt}")
    if "javascript:" in text.casefold():
        fail(f"{path}: javascript: inline não permitido")
    if re.search(
        r"https?://(www\.)?(google-analytics|googletagmanager|facebook\.com/tr)",
        text,
        re.I,
    ):
        fail(f"{path}: rastreador externo detectado")
    for href in parser.links:
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        clean = href.split("?", 1)[0].split("#", 1)[0]
        if not clean:
            continue
        target = (path.parent / clean).resolve()
        if not target.exists():
            fail(f"{path}: link local quebrado {href}")


def validate_generated_data_api() -> None:
    api_root = ROOT / "api"
    if not api_root.exists():
        return
    required = [
        api_root / "health" / "ready.json",
        api_root / "v1" / "index.json",
        api_root / "v1" / "stats.json",
        api_root / "v1" / "records.json.gz",
        api_root / "v1" / "documentos.json.gz",
        api_root / "v1" / "legislacao.json.gz",
        api_root / "v1" / "contratacoes.json.gz",
    ]
    for path in required:
        if not path.exists() or path.stat().st_size == 0:
            fail(f"Data API ausente ou vazia: {path}")
    ready = json.loads(required[0].read_text(encoding="utf-8"))
    if not ready.get("ready"):
        fail("Data API não está pronta")
    if int(ready.get("documents", 0)) < 1:
        fail("Data API não pode ser publicada com zero documentos")
    if int(ready.get("legislation", 0)) < 1:
        fail("Data API não pode ser publicada sem leis, decretos ou proposições")

    with gzip.open(api_root / "v1" / "contratacoes.json.gz", "rt", encoding="utf-8") as handle:
        procurement = json.load(handle)
    if not isinstance(procurement.get("items"), list):
        fail("Coleção de contratações não possui lista de itens")


def validate_portal_v2_data() -> None:
    data_root = ROOT / "data"
    news = data_root / "news.json"
    enrichment = data_root / "enrichment.json"
    if not news.exists() or not enrichment.exists():
        return

    feed = json.loads(news.read_text(encoding="utf-8"))
    if feed.get("count") != 5 or len(feed.get("items", [])) != 5:
        fail("O feed público deve conter exatamente cinco notícias")

    summary = json.loads(enrichment.read_text(encoding="utf-8"))
    if summary.get("detail_shards") != 16 or summary.get("relation_shards") != 16:
        fail("Camada de detalhes e relações está incompleta")

    for folder in ("details", "relations"):
        for shard in "0123456789abcdef":
            path = data_root / folder / f"{shard}.json.gz"
            if not path.exists() or path.stat().st_size == 0:
                fail(f"Shard ausente: {path}")


def main() -> None:
    for name in PAGES:
        path = ROOT / name
        if not path.exists():
            fail(f"página ausente: {path}")
        inspect_page(path)

    manifest = ROOT / "data" / "manifest.json"
    if manifest.exists():
        json.loads(manifest.read_text(encoding="utf-8"))

    required_assets = [
        ROOT / "assets/styles.css",
        ROOT / "assets/portal-v2.css",
        ROOT / "assets/app.js",
        ROOT / "assets/portal-v2.js",
        ROOT / "assets/search-worker.js",
        ROOT / "manifest.webmanifest",
    ]
    for required in required_assets:
        if not required.exists():
            fail(f"asset ausente: {required}")

    validate_generated_data_api()
    validate_portal_v2_data()
    print("Portal estático, detalhes, relações e Data API validados.")


if __name__ == "__main__":
    main()

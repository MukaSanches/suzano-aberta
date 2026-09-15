from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path("web")
PAGES = [
    "index.html",
    "explorar.html",
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
        ROOT / "assets/app.js",
        ROOT / "assets/search-worker.js",
        ROOT / "manifest.webmanifest",
    ]
    for required in required_assets:
        if not required.exists():
            fail(f"asset ausente: {required}")

    print("Portal estático validado.")


if __name__ == "__main__":
    main()

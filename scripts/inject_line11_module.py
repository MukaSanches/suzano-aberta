from __future__ import annotations

import argparse
from pathlib import Path

START = "<!-- line11-module:start -->"
END = "<!-- line11-module:end -->"

HOME_SECTION = '''<section class="section line11-home-section" aria-labelledby="linha11-home-title">
  <div class="wrap">
    <div class="section-head">
      <div><span class="eyebrow">Mobilidade agora</span><h2 id="linha11-home-title">Linha 11–Coral em Suzano</h2></div>
      <p>Status operacional oficial com foco em Calmon Viana, Suzano, Jundiapeba e Estudantes. Quando a fonte não trouxer dado atual, o portal mostra isso explicitamente.</p>
    </div>
    <div class="line11-widget" data-line11-widget data-line11-compact="true" aria-live="polite"><div class="line11-loading" role="status">Consultando fontes oficiais…</div></div>
    <p class="search-help"><a href="./linha-11.html">Abrir painel completo da Linha 11–Coral</a></p>
  </div>
</section>'''


def inject_homepage(page: Path) -> bool:
    text = page.read_text(encoding="utf-8")
    if START in text and END in text:
        return False
    css = '<link rel="stylesheet" href="./assets/line11.css">'
    js = '<script defer src="./assets/line11.js"></script>'
    if css not in text:
        text = text.replace("</head>", f"  {css}\n</head>", 1)
    if js not in text:
        text = text.replace("</head>", f"  {js}\n</head>", 1)
    anchor = '<section class="section" aria-labelledby="servicos-title">'
    if anchor not in text:
        raise RuntimeError("âncora da página inicial para Linha 11 não encontrada")
    text = text.replace(anchor, f"{START}\n{HOME_SECTION}\n{END}\n\n{anchor}", 1)
    page.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Injeta o módulo da Linha 11 na home do portal.")
    parser.add_argument("--page", type=Path, default=Path("web/index.html"))
    args = parser.parse_args()
    print("updated" if inject_homepage(args.page) else "already-present")


if __name__ == "__main__":
    main()

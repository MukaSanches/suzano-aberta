from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("web")


def fail(message: str) -> None:
    print(f"ERRO AUTOPILOT: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    for asset in ("./assets/portal-v6.css", "./assets/portal-v6.js"):
        if asset not in homepage:
            fail(f"index.html não carrega {asset}")

    for asset in (ROOT / "assets" / "portal-v6.css", ROOT / "assets" / "portal-v6.js"):
        if not asset.exists() or asset.stat().st_size < 100:
            fail(f"asset v6 ausente ou vazio: {asset}")

    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    if "suzano-aberta-shell-v6" not in sw:
        fail("service worker ainda não usa shell v6")
    for name in ("portal-v6.css", "portal-v6.js"):
        if name not in sw:
            fail(f"service worker não inclui {name}")

    news_path = ROOT / "data" / "news.json"
    autopilot_path = ROOT / "data" / "autopilot.json"
    if not news_path.exists() or not autopilot_path.exists():
        fail("news.json ou autopilot.json ausente")

    news = json.loads(news_path.read_text(encoding="utf-8"))
    items = news.get("items") or []
    if int(news.get("count", 0)) < 5 or len(items) < 5:
        fail("feed possui menos de cinco notícias")
    if int(news.get("publisher_count", 0)) < 2:
        fail("feed não possui diversidade mínima de fontes")
    if not isinstance(news.get("topics"), list) or not news.get("topics"):
        fail("feed não possui classificação temática")

    autopilot = json.loads(autopilot_path.read_text(encoding="utf-8"))
    if autopilot.get("mode") != "deterministic-autopilot":
        fail("modo do briefing não é determinístico")
    pulse = autopilot.get("pulse") or {}
    if int(pulse.get("records", 0)) < 1:
        fail("briefing não possui registros")
    if int(pulse.get("sources", 0)) < 1:
        fail("briefing não possui fontes")
    if len(autopilot.get("briefing") or []) < 4:
        fail("briefing operacional incompleto")
    if not autopilot.get("legislation"):
        fail("radar legislativo vazio")
    if not autopilot.get("procurements"):
        fail("radar de contratações vazio")

    print(
        json.dumps(
            {
                "news": len(items),
                "publishers": news.get("publisher_count"),
                "topics": len(news.get("topics") or []),
                "records": pulse.get("records"),
                "sources": pulse.get("sources"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

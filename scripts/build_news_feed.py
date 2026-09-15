from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from suzano_aberta.discovery import WebDiscovery
from suzano_aberta.http import PoliteHttpClient
from suzano_aberta.sources import PrefeituraSource

NEWS_QUERIES = (
    '"Suzano" SP',
    '"Prefeitura de Suzano"',
    '"Câmara de Suzano"',
)


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text.casefold()).strip()
    return text


def timestamp(value: str | None) -> float:
    if not value:
        return 0.0
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.timestamp()
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=UTC).timestamp()
        except ValueError:
            return 0.0


def clean_news_title(value: str) -> str:
    return re.sub(r"\s+-\s+[^-]{2,80}$", "", str(value or "").strip()).strip()


def item_from_record(record: Any, origin: str) -> dict[str, Any]:
    attributes = getattr(record, "attributes", {}) or {}
    publisher = (
        attributes.get("publicador")
        or getattr(getattr(record, "source", None), "name", None)
        or "Fonte pública"
    )
    return {
        "title": clean_news_title(getattr(record, "title", "")),
        "url": getattr(getattr(record, "source", None), "url", ""),
        "published_at": getattr(record, "date", None),
        "publisher": str(publisher),
        "origin": origin,
        "summary": (getattr(record, "summary", None) or "")[:500],
    }


def build(output: Path) -> dict[str, Any]:
    now = datetime.now(UTC)
    candidates: list[dict[str, Any]] = []
    errors: list[str] = []

    with PoliteHttpClient(timeout=18.0, min_interval=0.12) as http:
        prefeitura = PrefeituraSource(http)
        try:
            for record in prefeitura.news(year=now.year, limit=40):
                candidates.append(item_from_record(record, "prefeitura"))
        except Exception as exc:
            errors.append(f"Prefeitura: {type(exc).__name__}: {exc}")

        discovery = WebDiscovery(http)
        try:
            for record in discovery.discover_news(NEWS_QUERIES, per_query=40):
                item = item_from_record(record, "web")
                haystack = normalize(f"{item['title']} {item['summary']} {item['publisher']}")
                if "suzano" in haystack:
                    candidates.append(item)
        except Exception as exc:
            errors.append(f"Web: {type(exc).__name__}: {exc}")

    unique: dict[str, dict[str, Any]] = {}
    for item in candidates:
        title_key = normalize(item.get("title") or "")
        if len(title_key) < 8 or not item.get("url"):
            continue
        previous = unique.get(title_key)
        if previous is None or timestamp(item.get("published_at")) > timestamp(previous.get("published_at")):
            unique[title_key] = item

    ordered = sorted(
        unique.values(),
        key=lambda item: (timestamp(item.get("published_at")), normalize(item.get("title") or "")),
        reverse=True,
    )
    items = ordered[:5]
    if len(items) != 5:
        raise RuntimeError(
            f"O feed precisa publicar exatamente 5 notícias; apenas {len(items)} foram encontradas. "
            + (" | ".join(errors) if errors else "")
        )

    payload = {
        "schema": 1,
        "generated_at": now.isoformat(),
        "refresh_minutes": 30,
        "count": 5,
        "items": items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica exatamente as cinco notícias mais recentes sobre Suzano.")
    parser.add_argument("--output", type=Path, default=Path("web/data/news.json"))
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({"count": result["count"], "generated_at": result["generated_at"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

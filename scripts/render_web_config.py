from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("web/config.json"))
    parser.add_argument("--api-base", default="")
    args = parser.parse_args()
    payload = {
        "api_base": args.api_base.strip().rstrip("/"),
        "static_api_base": "./api",
        "repository": "https://github.com/MukaSanches/suzano-aberta",
        "snapshot": "https://github.com/MukaSanches/suzano-aberta/releases/tag/data-latest",
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "app"
TARGET = ROOT / "mobile" / "android" / "app" / "src" / "main" / "assets" / "www"
FILES = ("index.html", "styles.css", "app.js", "icon.svg", "manifest.webmanifest", "sw.js")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza a shell web oficial com o fallback offline do APK.")
    parser.add_argument("--check-after-copy", action="store_true")
    args = parser.parse_args()
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = SOURCE / name
        if not src.is_file():
            raise SystemExit(f"arquivo obrigatório ausente: {src}")
        shutil.copy2(src, TARGET / name)
    if args.check_after_copy:
        drift = [name for name in FILES if not filecmp.cmp(SOURCE / name, TARGET / name, shallow=False)]
        if drift:
            raise SystemExit(f"fallback Android divergiu da shell web: {', '.join(drift)}")
    print(f"shell móvel sincronizada: {len(FILES)} arquivos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

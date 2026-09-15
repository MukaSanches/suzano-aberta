from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa a Suzano Aberta API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="suzano-aberta.sqlite3")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--sem-sync", action="store_true")
    args = parser.parse_args()
    if args.port < 1 or args.port > 65535:
        parser.error("--port deve estar entre 1 e 65535")
    if args.workers < 1:
        parser.error("--workers deve ser >= 1")
    if args.reload and args.workers != 1:
        parser.error("--reload não pode ser combinado com --workers > 1")
    os.environ["SUZANO_API_DATABASE"] = args.db
    if args.sem_sync:
        os.environ["SUZANO_API_AUTO_SYNC"] = "false"
    uvicorn.run(
        "suzano_aberta.api:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

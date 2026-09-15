from __future__ import annotations

import gzip
import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path

import httpx

from .http import DEFAULT_USER_AGENT


LATEST_SNAPSHOT_URL = (
    "https://github.com/MukaSanches/suzano-aberta/releases/download/"
    "data-latest/suzano-aberta.sqlite3.gz"
)


class SnapshotError(RuntimeError):
    pass


def _download(url: str, destination: Path, *, timeout: float) -> str:
    digest = hashlib.sha256()
    with httpx.stream(
        "GET",
        url,
        follow_redirects=True,
        timeout=httpx.Timeout(timeout, connect=min(timeout, 15.0)),
        headers={"User-Agent": DEFAULT_USER_AGENT},
    ) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                digest.update(chunk)
                handle.write(chunk)
    return digest.hexdigest()


def sync_latest_snapshot(
    destination: str | Path,
    *,
    url: str = LATEST_SNAPSHOT_URL,
    timeout: float = 120.0,
) -> int:
    """Baixa, valida e instala atomicamente o índice público mais recente."""
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=target.parent) as temp_dir:
        temp_root = Path(temp_dir)
        compressed = temp_root / "snapshot.sqlite3.gz"
        extracted = temp_root / "snapshot.sqlite3"
        checksum_file = temp_root / "snapshot.sha256"

        actual_checksum = _download(url, compressed, timeout=timeout)
        try:
            _download(f"{url}.sha256", checksum_file, timeout=timeout)
            expected_checksum = checksum_file.read_text(encoding="utf-8").strip().split()[0]
        except (httpx.HTTPError, OSError, IndexError):
            expected_checksum = ""

        if expected_checksum and actual_checksum.casefold() != expected_checksum.casefold():
            raise SnapshotError("Checksum do snapshot não confere; arquivo recusado.")

        try:
            with gzip.open(compressed, "rb") as source, extracted.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
        except (OSError, EOFError) as exc:
            raise SnapshotError("Snapshot compactado inválido.") from exc

        if extracted.read_bytes()[:16] != b"SQLite format 3\x00":
            raise SnapshotError("O snapshot baixado não é um banco SQLite válido.")

        try:
            connection = sqlite3.connect(f"file:{extracted}?mode=ro", uri=True)
            try:
                quick_check = connection.execute("PRAGMA quick_check").fetchone()
                if quick_check is None or str(quick_check[0]).casefold() != "ok":
                    raise SnapshotError("Falha no quick_check do snapshot.")
                row = connection.execute(
                    "SELECT COUNT(*) FROM records WHERE active=1"
                ).fetchone()
                count = int(row[0]) if row is not None else 0
            finally:
                connection.close()
        except sqlite3.DatabaseError as exc:
            raise SnapshotError("Estrutura SQLite do snapshot é inválida.") from exc

        install_path = temp_root / "install.sqlite3"
        os.replace(extracted, install_path)
        os.replace(install_path, target)
        return count

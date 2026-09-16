from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path

import httpx

from .content_store import SnapshotManifest, verify_manifest, write_manifest
from .contracts import DataContract, DEFAULT_CONTRACT, validate_database_contract
from .http import DEFAULT_USER_AGENT

LATEST_SNAPSHOT_URL = (
    "https://github.com/MukaSanches/suzano-aberta/releases/download/"
    "data-latest/suzano-aberta.sqlite3.gz"
)
LATEST_MANIFEST_URL = (
    "https://github.com/MukaSanches/suzano-aberta/releases/download/"
    "data-latest/suzano-aberta.manifest.json"
)


class SnapshotError(RuntimeError):
    pass


def snapshot_checksum_path(destination: str | Path) -> Path:
    return Path(f"{Path(destination)}.remote.sha256")


def snapshot_manifest_path(destination: str | Path) -> Path:
    return Path(f"{Path(destination)}.manifest.json")


def snapshot_lock_path(destination: str | Path) -> Path:
    return Path(f"{Path(destination)}.sync.lock")


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


def _fetch_remote_checksum(url: str, *, timeout: float) -> str | None:
    try:
        response = httpx.get(
            f"{url}.sha256",
            follow_redirects=True,
            timeout=httpx.Timeout(min(timeout, 30.0), connect=min(timeout, 15.0)),
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        response.raise_for_status()
        checksum = response.text.strip().split()[0]
    except (httpx.HTTPError, OSError, IndexError):
        return None
    return checksum if len(checksum) == 64 else None


def _fetch_remote_manifest(url: str, *, timeout: float) -> SnapshotManifest | None:
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=httpx.Timeout(min(timeout, 30.0), connect=min(timeout, 15.0)),
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return SnapshotManifest.model_validate(response.json())
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        return None


def _validate_database(
    path: Path,
    *,
    min_records: int = 1,
    contract: DataContract = DEFAULT_CONTRACT,
    previous_records: int | None = None,
) -> int:
    try:
        with path.open("rb") as handle:
            if handle.read(16) != b"SQLite format 3\x00":
                raise SnapshotError("O snapshot baixado não é um banco SQLite válido.")
    except OSError as exc:
        raise SnapshotError(f"Não foi possível ler o snapshot: {exc}") from exc

    try:
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
            if quick_check is None or str(quick_check[0]).casefold() != "ok":
                raise SnapshotError("Falha no quick_check do snapshot.")
            row = connection.execute("SELECT COUNT(*) FROM records WHERE active=1").fetchone()
            count = int(row[0]) if row is not None else 0
            if count < min_records:
                raise SnapshotError(
                    f"Snapshot recusado por cobertura insuficiente: {count} < {min_records}."
                )
            fts_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='records_fts'"
            ).fetchone()
            if fts_table is not None:
                fts_row = connection.execute("SELECT COUNT(*) FROM records_fts").fetchone()
                fts_count = int(fts_row[0]) if fts_row is not None else 0
                if fts_count != count:
                    raise SnapshotError(
                        f"Índice FTS inconsistente no snapshot: {fts_count} != {count}."
                    )
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        raise SnapshotError("Estrutura SQLite do snapshot é inválida.") from exc

    report = validate_database_contract(
        path,
        contract=contract.model_copy(update={"minimum_records": max(min_records, contract.minimum_records)}),
        previous_records=previous_records,
    )
    if not report.ok:
        codes = ", ".join(item.code for item in report.findings if item.severity == "error")
        raise SnapshotError(f"Snapshot recusado pelo contrato de dados: {codes or 'falha de qualidade'}.")
    return count


def _write_checksum_sidecar(path: Path, checksum: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(checksum + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _lock_is_stale(path: Path, *, stale_seconds: float) -> bool:
    try:
        return time.time() - path.stat().st_mtime > stale_seconds
    except OSError:
        return False


def _acquire_sync_lock(path: Path, *, stale_seconds: float) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if not _lock_is_stale(path, stale_seconds=stale_seconds):
                return False
            try:
                path.unlink()
            except OSError:
                return False
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()}\n")
        return True
    return False


def _release_sync_lock(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _wait_for_other_sync(
    target: Path,
    lock: Path,
    *,
    min_records: int,
    timeout: float,
    contract: DataContract,
) -> int:
    deadline = time.monotonic() + min(max(timeout, 1.0), 30.0)
    while lock.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    if target.exists():
        return _validate_database(target, min_records=min_records, contract=contract)
    raise SnapshotError("Outra sincronização está em andamento e o banco local ainda não está disponível.")


def _local_record_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            row = connection.execute("SELECT COUNT(*) FROM records WHERE active=1").fetchone()
        finally:
            connection.close()
    except sqlite3.Error:
        return None
    return int(row[0]) if row is not None else None


def sync_latest_snapshot(
    destination: str | Path,
    *,
    url: str = LATEST_SNAPSHOT_URL,
    manifest_url: str | None = None,
    timeout: float = 120.0,
    min_records: int = 1,
    contract: DataContract = DEFAULT_CONTRACT,
) -> int:
    """Baixa, valida e instala atomicamente o índice público mais recente."""
    if min_records < 1:
        raise ValueError("min_records deve ser maior ou igual a 1")

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    checksum_sidecar = snapshot_checksum_path(target)
    manifest_sidecar = snapshot_manifest_path(target)
    lock = snapshot_lock_path(target)
    stale_seconds = max(300.0, timeout * 2)
    previous_records = _local_record_count(target)

    if not _acquire_sync_lock(lock, stale_seconds=stale_seconds):
        return _wait_for_other_sync(
            target,
            lock,
            min_records=min_records,
            timeout=timeout,
            contract=contract,
        )

    try:
        remote_checksum = _fetch_remote_checksum(url, timeout=timeout)

        if remote_checksum is not None and target.exists() and checksum_sidecar.exists():
            try:
                local_checksum = checksum_sidecar.read_text(encoding="utf-8").strip().split()[0]
            except (OSError, IndexError):
                local_checksum = ""
            if local_checksum.casefold() == remote_checksum.casefold():
                try:
                    return _validate_database(
                        target,
                        min_records=min_records,
                        contract=contract,
                        previous_records=previous_records,
                    )
                except SnapshotError:
                    pass

        resolved_manifest_url = manifest_url
        if resolved_manifest_url is None:
            if url == LATEST_SNAPSHOT_URL:
                resolved_manifest_url = LATEST_MANIFEST_URL
            else:
                resolved_manifest_url = url.rsplit("/", 1)[0] + "/suzano-aberta.manifest.json"
        remote_manifest = _fetch_remote_manifest(resolved_manifest_url, timeout=timeout)

        with tempfile.TemporaryDirectory(dir=target.parent) as temp_dir:
            temp_root = Path(temp_dir)
            compressed = temp_root / "snapshot.sqlite3.gz"
            extracted = temp_root / "snapshot.sqlite3"

            try:
                actual_checksum = _download(url, compressed, timeout=timeout)
            except (httpx.HTTPError, OSError) as exc:
                raise SnapshotError(f"Não foi possível baixar o snapshot: {exc}") from exc

            expected_checksum = remote_checksum
            if expected_checksum is None:
                expected_checksum = _fetch_remote_checksum(url, timeout=timeout)
            if expected_checksum and actual_checksum.casefold() != expected_checksum.casefold():
                raise SnapshotError("Checksum do snapshot não confere; arquivo recusado.")

            try:
                with gzip.open(compressed, "rb") as source, extracted.open("wb") as output:
                    while chunk := source.read(1024 * 1024):
                        output.write(chunk)
            except (OSError, EOFError) as exc:
                raise SnapshotError("Snapshot compactado inválido.") from exc

            count = _validate_database(
                extracted,
                min_records=min_records,
                contract=contract,
                previous_records=previous_records,
            )
            if remote_manifest is not None:
                verification = verify_manifest(extracted, remote_manifest)
                if not verification.ok:
                    raise SnapshotError("Manifesto do release não corresponde ao SQLite extraído.")
                if remote_manifest.records != count:
                    raise SnapshotError("Manifesto do release declara quantidade de registros divergente.")

            install_path = temp_root / "install.sqlite3"
            os.replace(extracted, install_path)
            for suffix in ("-wal", "-shm"):
                sidecar = Path(f"{target}{suffix}")
                try:
                    sidecar.unlink()
                except FileNotFoundError:
                    pass
            os.replace(install_path, target)
            _write_checksum_sidecar(checksum_sidecar, actual_checksum)
            if remote_manifest is not None:
                write_manifest(manifest_sidecar, remote_manifest)
            return count
    finally:
        _release_sync_lock(lock)

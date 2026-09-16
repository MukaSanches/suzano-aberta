from __future__ import annotations

import hashlib
import importlib.metadata
import sqlite3
from pathlib import Path

from .content_store import (
    ManifestVerification,
    SnapshotManifest,
    load_manifest,
    verify_manifest,
    write_manifest,
)
from .contracts import ContractReport, DataContract, DEFAULT_CONTRACT, validate_database_contract


def manifest_path_for(database: str | Path) -> Path:
    return Path(f"{Path(database)}.manifest.json")


def _package_version() -> str:
    try:
        return importlib.metadata.version("suzano-aberta")
    except importlib.metadata.PackageNotFoundError:
        return "1.0.0"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_metadata(path: Path) -> tuple[int, int, str]:
    """Obtém metadados de release sem importar a camada HTTP/API.

    Esta função deliberadamente usa apenas sqlite3 para que a geração de
    manifestos permaneça uma primitive de armazenamento e não crie ciclos de
    import com o FastAPI.
    """
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT COUNT(*) AS records,
                   COUNT(DISTINCT source_name) AS sources,
                   MAX(last_seen) AS last_seen
            FROM records
            WHERE active=1
            """
        ).fetchone()
        if row is None:
            records = 0
            sources = 0
            last_seen = ""
        else:
            records = int(row["records"])
            sources = int(row["sources"])
            last_seen = str(row["last_seen"] or "")
    finally:
        connection.close()

    raw = "|".join((str(records), str(sources), last_seen, str(path.stat().st_size)))
    dataset_version = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return records, sources, dataset_version


def build_snapshot_manifest(
    database: str | Path,
    *,
    contract: DataContract = DEFAULT_CONTRACT,
    previous_manifest: str | Path | None = None,
    lineage_run_id: str | None = None,
) -> tuple[SnapshotManifest, ContractReport]:
    path = Path(database)
    report = validate_database_contract(path, contract=contract)
    if not report.ok:
        raise ValueError("O snapshot não atende ao contrato de dados e não pode receber manifesto de release.")

    records, sources, dataset_version = _snapshot_metadata(path)
    previous_sha: str | None = None
    if previous_manifest is not None and Path(previous_manifest).exists():
        previous_sha = load_manifest(previous_manifest).sha256()

    manifest = SnapshotManifest(
        software_version=_package_version(),
        dataset_version=dataset_version,
        database_sha256=_sha256_file(path),
        database_bytes=path.stat().st_size,
        records=records,
        sources=sources,
        contract_status=report.status,
        contract_sha256=report.contract_sha256,
        previous_manifest_sha256=previous_sha,
        lineage_run_id=lineage_run_id,
    )
    return manifest, report


def repository_sources(database: str | Path) -> list[str]:
    path = Path(database)
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = connection.execute(
            "SELECT DISTINCT source_name FROM records WHERE active=1 ORDER BY source_name"
        ).fetchall()
    finally:
        connection.close()
    return [str(row[0]) for row in rows]


def write_snapshot_manifest(
    database: str | Path,
    *,
    output: str | Path | None = None,
    contract: DataContract = DEFAULT_CONTRACT,
    previous_manifest: str | Path | None = None,
    lineage_run_id: str | None = None,
) -> tuple[SnapshotManifest, ContractReport, str]:
    manifest, report = build_snapshot_manifest(
        database,
        contract=contract,
        previous_manifest=previous_manifest,
        lineage_run_id=lineage_run_id,
    )
    target = Path(output) if output is not None else manifest_path_for(database)
    digest = write_manifest(target, manifest)
    return manifest, report, digest


def verify_snapshot_manifest(
    database: str | Path,
    manifest_path: str | Path | None = None,
) -> ManifestVerification:
    target = Path(manifest_path) if manifest_path is not None else manifest_path_for(database)
    return verify_manifest(database, load_manifest(target))

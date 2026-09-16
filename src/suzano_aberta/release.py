from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path

from .api.repository import ApiRepository
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

    with ApiRepository(path) as repository:
        stats = repository.stats()
        dataset_version = repository.dataset_version()
    previous_sha: str | None = None
    if previous_manifest is not None and Path(previous_manifest).exists():
        previous_sha = load_manifest(previous_manifest).sha256()

    manifest = SnapshotManifest(
        software_version=_package_version(),
        dataset_version=dataset_version,
        database_sha256=_sha256_file(path),
        database_bytes=path.stat().st_size,
        records=int(stats["records"]),
        sources=len(repository_sources(path)),
        contract_status=report.status,
        contract_sha256=report.contract_sha256,
        previous_manifest_sha256=previous_sha,
        lineage_run_id=lineage_run_id,
    )
    return manifest, report


def repository_sources(database: str | Path) -> list[str]:
    with ApiRepository(database) as repository:
        return [name for name, _ in repository.source_counts(limit=100_000)]


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

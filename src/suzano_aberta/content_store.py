from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from pydantic import BaseModel, Field


class ContentObject(BaseModel):
    sha256: str
    bytes: int = Field(ge=0)
    path: str


class SnapshotManifest(BaseModel):
    """Manifesto determinístico que descreve uma geração de dados."""

    schema: str = "suzano-aberta-manifest/v1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    software_version: str
    dataset_version: str
    database_sha256: str
    database_bytes: int = Field(ge=0)
    records: int = Field(ge=0)
    sources: int = Field(ge=0)
    contract_status: str
    contract_sha256: str
    previous_manifest_sha256: str | None = None
    lineage_run_id: str | None = None

    def canonical_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class ManifestVerification(BaseModel):
    ok: bool
    manifest_sha256: str
    database_sha256: str
    expected_database_sha256: str
    database_bytes: int = Field(ge=0)
    expected_database_bytes: int = Field(ge=0)


class ContentAddressedStore:
    """Armazena conteúdo pela identidade criptográfica SHA-256.

    Objetos são imutáveis: o mesmo conteúdo sempre resolve para o mesmo caminho.
    O layout de dois níveis evita diretórios gigantes e segue o padrão conceitual
    usado por sistemas de armazenamento endereçado por conteúdo.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)

    def path_for(self, digest: str) -> Path:
        normalized = digest.casefold()
        if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValueError("SHA-256 inválido")
        return self.objects / normalized[:2] / normalized[2:]

    def has(self, digest: str) -> bool:
        return self.path_for(digest).is_file()

    def put_bytes(self, payload: bytes) -> ContentObject:
        digest = hashlib.sha256(payload).hexdigest()
        target = self.path_for(digest)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
            temporary.write_bytes(payload)
            os.replace(temporary, target)
        return ContentObject(sha256=digest, bytes=len(payload), path=str(target))

    def put_text(self, payload: str, *, encoding: str = "utf-8") -> ContentObject:
        return self.put_bytes(payload.encode(encoding))

    def put_file(self, source: str | Path) -> ContentObject:
        path = Path(source)
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        hexdigest = digest.hexdigest()
        target = self.path_for(hexdigest)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
            with path.open("rb") as source_handle, temporary.open("wb") as output:
                _copy(source_handle, output)
            os.replace(temporary, target)
        return ContentObject(sha256=hexdigest, bytes=size, path=str(target))

    def verify(self, digest: str) -> bool:
        target = self.path_for(digest)
        if not target.exists():
            return False
        return _sha256_file(target) == digest.casefold()


def _copy(source: BinaryIO, destination: BinaryIO) -> None:
    while chunk := source.read(1024 * 1024):
        destination.write(chunk)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: str | Path, manifest: SnapshotManifest) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    canonical = manifest.canonical_json() + "\n"
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(canonical, encoding="utf-8")
    os.replace(temporary, target)
    return manifest.sha256()


def load_manifest(path: str | Path) -> SnapshotManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return SnapshotManifest.model_validate(payload)


def verify_manifest(database: str | Path, manifest: SnapshotManifest) -> ManifestVerification:
    db_path = Path(database)
    actual_digest = _sha256_file(db_path)
    actual_bytes = db_path.stat().st_size
    return ManifestVerification(
        ok=actual_digest == manifest.database_sha256 and actual_bytes == manifest.database_bytes,
        manifest_sha256=manifest.sha256(),
        database_sha256=actual_digest,
        expected_database_sha256=manifest.database_sha256,
        database_bytes=actual_bytes,
        expected_database_bytes=manifest.database_bytes,
    )

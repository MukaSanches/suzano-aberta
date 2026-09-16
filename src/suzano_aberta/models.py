from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, Field


RecordKind = Literal[
    "sessao",
    "vereador",
    "proposicao",
    "lei",
    "decreto",
    "contrato",
    "ata",
    "comissao",
    "presenca",
    "diario",
    "licitacao",
    "secretaria",
    "documento_fiscal",
    "documento_orcamentario",
    "ato_oficial",
    "noticia",
    "pagina_web",
    "arquivo",
    "arquivo_historico",
]


class SourceRef(BaseModel):
    name: str
    url: str
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_sha256: str | None = None
    authority: str | None = None
    category: str | None = None
    retrieval_method: str | None = None
    media_type: str | None = None


class PublicRecord(BaseModel):
    id: str
    kind: RecordKind
    title: str
    summary: str | None = None
    date: str | None = None
    year: int | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    source: SourceRef

    def canonical_payload(self) -> dict[str, Any]:
        """Payload estável usado para detectar alteração substantiva."""
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "summary": self.summary,
            "date": self.date,
            "year": self.year,
            "attributes": self.attributes,
            "source_name": self.source.name,
            "source_url": self.source.url,
        }

    def fingerprint(self) -> str:
        import json

        raw = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return sha256(raw).hexdigest()


class RecordVersion(BaseModel):
    record_id: str
    version: int = Field(ge=1)
    observed_at: datetime
    content_hash: str
    record: PublicRecord


class SourceStatus(BaseModel):
    source: str
    url: str
    ok: bool
    status_code: int | None = None
    elapsed_ms: int | None = None
    detail: str | None = None


class IntegrityFinding(BaseModel):
    check: Literal["dominio_externo_nao_reconhecido"]
    severity: Literal["attention"]
    source_url: str
    target_url: str
    host: str
    evidence: str | None = None
    message: str


class IntegrityReport(BaseModel):
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_url: str
    status_code: int
    elapsed_ms: int
    external_hosts: list[str] = Field(default_factory=list)
    findings: list[IntegrityFinding] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


class Change(BaseModel):
    record_id: str
    kind: str
    change_type: Literal["novo", "alterado", "ausente"]
    observed_at: datetime
    previous_hash: str | None = None
    current_hash: str | None = None


class TemporalDiff(BaseModel):
    from_time: datetime
    to_time: datetime
    total: int = Field(ge=0)
    new: int = Field(ge=0)
    changed: int = Field(ge=0)
    absent: int = Field(ge=0)
    items: list[Change] = Field(default_factory=list)


class CollectionReport(BaseModel):
    started_at: datetime
    finished_at: datetime
    records: int
    sources_ok: int
    sources_failed: int
    new_records: int
    changed_records: int
    errors: list[str] = Field(default_factory=list)


class RefreshReport(BaseModel):
    started_at: datetime
    finished_at: datetime
    years: list[int]
    official_records_seen: int
    discovered_records_seen: int
    new_records: int
    changed_records: int
    indexed_records: int
    sources_failed: int
    errors: list[str] = Field(default_factory=list)

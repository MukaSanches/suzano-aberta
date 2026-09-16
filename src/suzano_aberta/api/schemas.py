from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..content_store import ManifestVerification, SnapshotManifest
from ..contracts import ContractReport
from ..models import Change, PublicRecord, RecordVersion


class PageInfo(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    next_offset: int | None = Field(default=None, ge=0)
    previous_offset: int | None = Field(default=None, ge=0)
    returned: int = Field(default=0, ge=0)
    has_more: bool = False

    @model_validator(mode="after")
    def derive_navigation(self) -> PageInfo:
        remaining = max(0, self.total - self.offset)
        self.returned = min(self.limit, remaining)
        self.has_more = self.next_offset is not None
        self.previous_offset = max(0, self.offset - self.limit) if self.offset > 0 else None
        return self


class ResponseMeta(BaseModel):
    api_version: str
    schema_version: str
    dataset_version: str
    request_id: str | None = None


class RecordsResponse(BaseModel):
    query: str | None = None
    filters: dict[str, str | int | None] = Field(default_factory=dict)
    page: PageInfo
    items: list[PublicRecord]
    meta: ResponseMeta | None = None


class ChangesResponse(BaseModel):
    page: PageInfo
    items: list[Change]
    meta: ResponseMeta | None = None


class RecordHistoryResponse(BaseModel):
    record_id: str
    page: PageInfo
    items: list[RecordVersion]
    meta: ResponseMeta | None = None


class TemporalDiffResponse(BaseModel):
    from_time: str
    to_time: str
    total: int = Field(ge=0)
    new: int = Field(ge=0)
    changed: int = Field(ge=0)
    absent: int = Field(ge=0)
    page: PageInfo
    items: list[Change]
    meta: ResponseMeta | None = None


class QualityResponse(BaseModel):
    report: ContractReport
    meta: ResponseMeta | None = None


class ManifestResponse(BaseModel):
    manifest: SnapshotManifest
    verification: ManifestVerification
    meta: ResponseMeta | None = None


class SourceCount(BaseModel):
    name: str
    records: int = Field(ge=0)


class SourceSummary(BaseModel):
    name: str
    records: int = Field(ge=0)
    first_seen: str | None = None
    last_seen: str | None = None


class SourcesResponse(BaseModel):
    items: list[SourceSummary]
    total: int = Field(ge=0)
    meta: ResponseMeta | None = None


class StatsResponse(BaseModel):
    records: int = Field(ge=0)
    documents: int = Field(default=0, ge=0)
    legislation: int = Field(default=0, ge=0)
    procurements: int = Field(default=0, ge=0)
    first_seen: str | None = None
    last_seen: str | None = None
    fts_enabled: bool
    temporal_enabled: bool = False
    database_bytes: int = Field(ge=0)
    sqlite_version: str
    dataset_version: str
    kinds: dict[str, int]
    top_sources: list[SourceCount]


class HealthResponse(BaseModel):
    status: str
    ready: bool
    records: int = Field(default=0, ge=0)
    documents: int = Field(default=0, ge=0)
    legislation: int = Field(default=0, ge=0)
    procurements: int = Field(default=0, ge=0)
    dataset_version: str | None = None
    detail: str | None = None


class AutopilotResponse(BaseModel):
    database: str
    database_exists: bool
    records: int = Field(ge=0)
    due: bool
    fresh: bool
    locked: bool
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    last_error: str | None = None
    consecutive_failures: int = Field(ge=0)
    successful_checks: int = Field(ge=0)
    updates: int = Field(ge=0)
    remote_checksum: str | None = None
    database_modified_at: str | None = None
    next_check_at: str | None = None


class ServiceResponse(BaseModel):
    name: str
    api_version: str
    schema_version: str
    package_version: str
    description: str
    documentation: str
    openapi: str
    endpoints: dict[str, str]


class SnapshotResponse(BaseModel):
    database_url: str
    checksum_url: str
    metadata_url: str
    note: str


class CapabilitiesResponse(BaseModel):
    api_version: str
    schema_version: str
    read_only: bool
    formats: list[str]
    pagination: dict[str, int | str]
    sorting: list[str]
    date_modes: list[str]
    record_kinds: list[str]
    standards: list[str]
    endpoints: dict[str, str]


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str | None = None
    errors: list[dict[str, Any]] | None = None

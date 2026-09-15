from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import Change, PublicRecord


class PageInfo(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    next_offset: int | None = Field(default=None, ge=0)


class RecordsResponse(BaseModel):
    query: str | None = None
    filters: dict[str, str | int | None] = Field(default_factory=dict)
    page: PageInfo
    items: list[PublicRecord]


class ChangesResponse(BaseModel):
    page: PageInfo
    items: list[Change]


class SourceCount(BaseModel):
    name: str
    records: int = Field(ge=0)


class StatsResponse(BaseModel):
    records: int = Field(ge=0)
    documents: int = Field(default=0, ge=0)
    legislation: int = Field(default=0, ge=0)
    first_seen: str | None = None
    last_seen: str | None = None
    fts_enabled: bool
    database_bytes: int = Field(ge=0)
    sqlite_version: str
    kinds: dict[str, int]
    top_sources: list[SourceCount]


class HealthResponse(BaseModel):
    status: str
    ready: bool
    records: int = Field(default=0, ge=0)
    documents: int = Field(default=0, ge=0)
    legislation: int = Field(default=0, ge=0)
    detail: str | None = None


class ServiceResponse(BaseModel):
    name: str
    api_version: str
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

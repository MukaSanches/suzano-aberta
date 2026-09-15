from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .models import PublicRecord


class QualityReport(BaseModel):
    records: int = Field(ge=0)
    unique_ids: int = Field(ge=0)
    duplicate_ids: int = Field(ge=0)
    with_source_url: int = Field(ge=0)
    with_title: int = Field(ge=0)
    source_count: int = Field(ge=0)
    completeness: float = Field(ge=0, le=1)
    uniqueness: float = Field(ge=0, le=1)
    generated_at: datetime


def quality_report(records: list[PublicRecord]) -> QualityReport:
    total = len(records)
    ids = Counter(record.id for record in records)
    unique = len(ids)
    with_url = sum(bool(record.source.url.strip()) for record in records)
    with_title = sum(bool(record.title.strip()) for record in records)
    completeness = ((with_url + with_title) / (2 * total)) if total else 1.0
    uniqueness = (unique / total) if total else 1.0
    return QualityReport(
        records=total,
        unique_ids=unique,
        duplicate_ids=sum(count - 1 for count in ids.values() if count > 1),
        with_source_url=with_url,
        with_title=with_title,
        source_count=len({record.source.name for record in records}),
        completeness=round(completeness, 6),
        uniqueness=round(uniqueness, 6),
        generated_at=datetime.now(UTC),
    )

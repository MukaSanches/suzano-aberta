from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from suzano_aberta.index import SuzanoIndex
from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.release import write_snapshot_manifest
from suzano_aberta.store import Store


def _record(title: str) -> PublicRecord:
    return PublicRecord(
        id="lei:1",
        kind="lei",
        title=title,
        date="2026-09-16",
        year=2026,
        source=SourceRef(name="Fonte oficial", url="https://example.test/lei/1"),
    )


def test_local_index_exposes_temporal_quality_and_manifest(tmp_path: Path) -> None:
    database = tmp_path / "data.sqlite3"
    with Store(database) as store:
        store.upsert_many([_record("Lei original")])
        first = store.history("lei:1")[0]
        store.upsert_many([_record("Lei atualizada")])
    write_snapshot_manifest(database)

    with SuzanoIndex(database) as index:
        history, total = index.history("lei:1")
        historical = index.record_at("lei:1", first.observed_at)
        diff = index.diff(
            datetime.now(UTC) - timedelta(hours=1),
            datetime.now(UTC) + timedelta(hours=1),
        )
        quality = index.quality()
        manifest = index.manifest()
        stats = index.stats()

    assert total == 2
    assert len(history) == 2
    assert historical is not None and historical.title == "Lei original"
    assert diff.changed >= 1
    assert quality.ok
    assert manifest.verification.ok
    assert stats.temporal_enabled

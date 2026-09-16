from __future__ import annotations

import gzip
import hashlib
import sqlite3
from pathlib import Path

import httpx
import pytest
import respx

from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.snapshot import SnapshotError, snapshot_checksum_path, sync_latest_snapshot
from suzano_aberta.store import Store


def _database(path: Path, count: int) -> None:
    records = [
        PublicRecord(
            id=f"id:{index}",
            kind="pagina_web",
            title=f"Registro {index}",
            source=SourceRef(name="Fonte de teste", url="https://example.test/source"),
        )
        for index in range(count)
    ]
    with Store(path) as store:
        store.upsert_many(records)
        store.optimize()


def _count(path: Path) -> int:
    connection = sqlite3.connect(path)
    try:
        row = connection.execute("SELECT COUNT(*) FROM records WHERE active=1").fetchone()
    finally:
        connection.close()
    return int(row[0]) if row is not None else 0


def test_sync_skips_full_download_when_remote_checksum_is_unchanged(tmp_path: Path) -> None:
    database = tmp_path / "snapshot.sqlite3"
    _database(database, 4)
    checksum = "b" * 64
    snapshot_checksum_path(database).write_text(checksum + "\n", encoding="utf-8")
    url = "https://example.test/snapshot.sqlite3.gz"

    with respx.mock(assert_all_called=False) as router:
        checksum_route = router.get(f"{url}.sha256").mock(
            return_value=httpx.Response(200, text=f"{checksum}  snapshot.sqlite3.gz\n")
        )
        snapshot_route = router.get(url).mock(return_value=httpx.Response(200, content=b"unused"))
        count = sync_latest_snapshot(database, url=url, timeout=5)

    assert count == 4
    assert checksum_route.called
    assert not snapshot_route.called


def test_sync_rejects_candidate_with_abnormal_coverage_drop(tmp_path: Path) -> None:
    database = tmp_path / "snapshot.sqlite3"
    candidate = tmp_path / "candidate.sqlite3"
    _database(database, 10)
    _database(candidate, 3)
    compressed = gzip.compress(candidate.read_bytes(), mtime=0)
    checksum = hashlib.sha256(compressed).hexdigest()
    url = "https://example.test/snapshot.sqlite3.gz"

    with respx.mock(assert_all_called=True) as router:
        router.get(f"{url}.sha256").mock(
            return_value=httpx.Response(200, text=f"{checksum}  snapshot.sqlite3.gz\n")
        )
        router.get(url).mock(return_value=httpx.Response(200, content=compressed))
        with pytest.raises(SnapshotError, match="cobertura insuficiente"):
            sync_latest_snapshot(database, url=url, timeout=5, min_records=8)

    assert _count(database) == 10

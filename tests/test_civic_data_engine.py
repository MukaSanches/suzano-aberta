from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from suzano_aberta.api import create_app
from suzano_aberta.api.settings import ApiSettings
from suzano_aberta.content_store import ContentAddressedStore
from suzano_aberta.contracts import DataContract, validate_database_contract
from suzano_aberta.lineage import LineageDataset, LineageEvent, LineageJournal
from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.release import verify_snapshot_manifest, write_snapshot_manifest
from suzano_aberta.sources.registry import default_source_registry
from suzano_aberta.store import Store


def _record(title: str = "Contrato inicial") -> PublicRecord:
    return PublicRecord(
        id="contrato:temporal:1",
        kind="contrato",
        title=title,
        date="2026-09-16",
        year=2026,
        attributes={"valor": "100,00"},
        source=SourceRef(
            name="Fonte de teste",
            url="https://example.test/contrato/1",
            authority="Teste",
            category="contratos",
        ),
    )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "data.sqlite3"
    with Store(path) as store:
        store.upsert_many([_record()])
    return path


def test_store_preserves_complete_temporal_versions(tmp_path: Path) -> None:
    path = _database(tmp_path)
    with Store(path) as store:
        first = store.history("contrato:temporal:1")[0]
        store.upsert_many([_record("Contrato atualizado")])
        history = store.history("contrato:temporal:1")
        old = store.get_at("contrato:temporal:1", first.observed_at)
        latest = store.get("contrato:temporal:1")

    assert len(history) == 2
    assert history[0].version == 2
    assert history[1].version == 1
    assert old is not None and old.title == "Contrato inicial"
    assert latest is not None and latest.title == "Contrato atualizado"
    assert history[0].content_hash != history[1].content_hash


def test_temporal_diff_summarizes_changes(tmp_path: Path) -> None:
    path = _database(tmp_path)
    with Store(path) as store:
        start = datetime.now(UTC) - timedelta(minutes=1)
        store.upsert_many([_record("Contrato atualizado")])
        end = datetime.now(UTC) + timedelta(minutes=1)
        diff = store.diff(start, end)

    assert diff.total >= 2
    assert diff.new >= 1
    assert diff.changed >= 1
    assert any(item.record_id == "contrato:temporal:1" for item in diff.items)


def test_data_contract_passes_healthy_snapshot_and_blocks_regression(tmp_path: Path) -> None:
    path = _database(tmp_path)
    healthy = validate_database_contract(path)
    degraded = validate_database_contract(
        path,
        contract=DataContract(minimum_previous_ratio=0.9),
        previous_records=100,
    )

    assert healthy.ok
    assert healthy.score == 100
    assert degraded.ok is False
    assert any(item.code == "coverage_regression" for item in degraded.findings)


def test_manifest_round_trip_verifies_database(tmp_path: Path) -> None:
    path = _database(tmp_path)
    manifest, report, digest = write_snapshot_manifest(path)
    verification = verify_snapshot_manifest(path)

    assert report.ok
    assert len(digest) == 64
    assert manifest.database_sha256 == verification.database_sha256
    assert verification.ok


def test_content_addressed_store_deduplicates_identical_payload(tmp_path: Path) -> None:
    store = ContentAddressedStore(tmp_path / "cas")
    first = store.put_bytes(b"suzano-aberta")
    second = store.put_bytes(b"suzano-aberta")

    assert first.sha256 == second.sha256
    assert first.path == second.path
    assert store.verify(first.sha256)


def test_lineage_journal_emits_openlineage_compatible_event(tmp_path: Path) -> None:
    journal = LineageJournal(tmp_path / "lineage.jsonl")
    event = LineageEvent(
        event_type="COMPLETE",
        run_id="00000000-0000-0000-0000-000000000001",
        job_name="tests.pipeline",
        inputs=[LineageDataset(namespace="test", name="input")],
        outputs=[LineageDataset(namespace="test", name="output")],
    )
    journal.emit(event)
    payload = journal.tail(limit=1)[0]

    assert payload["eventType"] == "COMPLETE"
    assert payload["producer"] == "https://github.com/MukaSanches/suzano-aberta"
    assert payload["job"] == {"facets": {}, "name": "tests.pipeline", "namespace": "suzano-aberta"}


def test_default_source_registry_has_unique_builtin_sources() -> None:
    registrations = default_source_registry(include_plugins=False).registrations()
    keys = [item.definition.key for item in registrations]

    assert len(keys) >= 5
    assert len(keys) == len(set(keys))
    assert {"camara", "prefeitura"}.issubset(set(keys))


def test_civic_api_exposes_quality_history_diff_manifest_and_feed(tmp_path: Path) -> None:
    path = _database(tmp_path)
    with Store(path) as store:
        store.upsert_many([_record("Contrato atualizado")])
    write_snapshot_manifest(path)

    app = create_app(ApiSettings(database=path, auto_sync=False, metrics_enabled=False))
    with TestClient(app) as client:
        assert client.get("/v1/quality").status_code == 200
        history = client.get("/v1/records/contrato:temporal:1/history")
        assert history.status_code == 200
        assert history.json()["page"]["total"] == 2

        first_version = history.json()["items"][-1]["observed_at"]
        historical = client.get(
            "/v1/records/contrato:temporal:1/at",
            params={"at": first_version},
        )
        assert historical.status_code == 200
        assert historical.json()["title"] == "Contrato inicial"

        diff = client.get(
            "/v1/diff",
            params={
                "from": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
                "to": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
        )
        assert diff.status_code == 200
        assert diff.json()["total"] >= 2

        manifest = client.get("/v1/manifest")
        assert manifest.status_code == 200
        assert manifest.json()["verification"]["ok"] is True

        feed = client.get("/v1/feed/changes.atom")
        assert feed.status_code == 200
        assert "application/atom+xml" in feed.headers["content-type"]
        assert "Suzano Aberta" in feed.text

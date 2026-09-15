from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from suzano_aberta.api import ApiSettings, create_app
from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.store import Store


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "api.sqlite3"
    records = [
        PublicRecord(
            id="proposicao:1",
            kind="proposicao",
            title="Educação em Suzano",
            summary="Transporte escolar e atendimento aos estudantes.",
            date="2026-05-06",
            year=2026,
            attributes={"tema": "educação"},
            source=SourceRef(
                name="Câmara Municipal de Suzano",
                url="https://example.test/proposicao/1",
            ),
        ),
        PublicRecord(
            id="lei:1",
            kind="lei",
            title="Lei municipal de educação",
            summary="Norma municipal publicada em setembro.",
            date="2026-09-10",
            year=2026,
            attributes={"document_url": "https://example.test/lei.pdf"},
            source=SourceRef(
                name="Prefeitura Municipal de Suzano",
                url="https://example.test/lei.pdf",
            ),
        ),
        PublicRecord(
            id="arquivo:1",
            kind="arquivo",
            title="Contrato de obra pública",
            summary="Documento de contratação para obra municipal.",
            date="2025-02-01",
            year=2025,
            attributes={"extensao": ".pdf", "texto": "reforma de unidade de saúde"},
            source=SourceRef(
                name="Prefeitura Municipal de Suzano",
                url="https://example.test/contrato.pdf",
            ),
        ),
    ]
    with Store(path) as store:
        store.upsert_many(records)
    return path


def test_api_search_filters_and_stats(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["records"] == 3
        assert ready.json()["documents"] == 2
        assert ready.json()["legislation"] == 2

        result = client.get("/v1/search", params={"q": "educacao", "year": 2026})
        assert result.status_code == 200
        payload = result.json()
        assert payload["page"]["total"] == 2
        assert payload["items"][0]["id"] == "lei:1"
        assert payload["items"][1]["id"] == "proposicao:1"

        filtered = client.get("/v1/records", params={"kind": "arquivo"})
        assert filtered.status_code == 200
        assert filtered.json()["page"]["total"] == 1

        stats = client.get("/v1/stats")
        assert stats.status_code == 200
        assert stats.json()["records"] == 3
        assert stats.json()["documents"] == 2
        assert stats.json()["legislation"] == 2
        assert stats.json()["fts_enabled"] is True


def test_api_date_range_and_default_chronology(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        listing = client.get("/v1/records")
        assert listing.status_code == 200
        assert [item["id"] for item in listing.json()["items"]] == [
            "lei:1",
            "proposicao:1",
            "arquivo:1",
        ]

        may = client.get(
            "/v1/records",
            params={"date_from": "2026-05-01", "date_to": "2026-05-31"},
        )
        assert may.status_code == 200
        assert [item["id"] for item in may.json()["items"]] == ["proposicao:1"]

        oldest = client.get("/v1/records", params={"sort": "date_asc"})
        assert oldest.status_code == 200
        assert oldest.json()["items"][0]["id"] == "arquivo:1"

        invalid = client.get(
            "/v1/records",
            params={"date_from": "2026-06-01", "date_to": "2026-05-01"},
        )
        assert invalid.status_code == 422


def test_documents_and_legislation_collections(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        documents = client.get("/v1/documents")
        assert documents.status_code == 200
        assert [item["id"] for item in documents.json()["items"]] == ["lei:1", "arquivo:1"]

        found_document = client.get("/v1/documents", params={"q": "reforma"})
        assert found_document.status_code == 200
        assert found_document.json()["page"]["total"] == 1
        assert found_document.json()["items"][0]["id"] == "arquivo:1"

        legislation = client.get("/v1/legislation")
        assert legislation.status_code == 200
        assert [item["id"] for item in legislation.json()["items"]] == ["lei:1", "proposicao:1"]

        proposals = client.get("/v1/legislation", params={"kind": "proposicao"})
        assert proposals.status_code == 200
        assert proposals.json()["page"]["total"] == 1

        invalid_kind = client.get("/v1/legislation", params={"kind": "contrato"})
        assert invalid_kind.status_code == 422


def test_record_etag_and_not_modified(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        first = client.get("/v1/records/proposicao:1")
        assert first.status_code == 200
        etag = first.headers["etag"]

        second = client.get("/v1/records/proposicao:1", headers={"If-None-Match": etag})
        assert second.status_code == 304
        assert second.headers["etag"] == etag

        missing = client.get("/v1/records/nao-existe")
        assert missing.status_code == 404


def test_openapi_is_versioned_and_read_only(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert schema.json()["info"]["version"] == "1.1.0"
        assert "/v1/search" in schema.json()["paths"]
        assert "/v1/documents" in schema.json()["paths"]
        assert "/v1/legislation" in schema.json()["paths"]
        assert client.post("/v1/records").status_code == 405


def test_readiness_fails_without_index(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite3"
    app = create_app(ApiSettings(database=missing, auto_sync=False))
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["ready"] is False


def test_pagination_is_bounded(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        response = client.get("/v1/records", params={"limit": 1, "offset": 0})
        assert response.status_code == 200
        page = response.json()["page"]
        assert page["total"] == 3
        assert page["next_offset"] == 1

        invalid = client.get("/v1/records", params={"limit": 1000})
        assert invalid.status_code == 422

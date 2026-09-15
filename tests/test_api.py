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
            source=SourceRef(name="Câmara Municipal de Suzano", url="https://example.test/proposicao/1"),
        ),
        PublicRecord(
            id="lei:1",
            kind="lei",
            title="Lei municipal de educação",
            summary="Norma municipal publicada em setembro.",
            date="2026-09-10",
            year=2026,
            attributes={"document_url": "https://example.test/lei.pdf"},
            source=SourceRef(name="Prefeitura Municipal de Suzano", url="https://example.test/lei.pdf"),
        ),
        PublicRecord(
            id="arquivo:1",
            kind="arquivo",
            title="Contrato de obra pública",
            summary="Documento de contratação para obra municipal.",
            date="2025-02-01",
            year=2025,
            attributes={"extensao": ".pdf", "texto": "reforma de unidade de saúde"},
            source=SourceRef(name="Prefeitura Municipal de Suzano", url="https://example.test/contrato.pdf"),
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
        assert ready.json()["procurements"] == 0
        assert ready.json()["dataset_version"]

        result = client.get("/v1/search", params={"q": "educacao", "year": 2026})
        assert result.status_code == 200
        payload = result.json()
        assert payload["page"]["total"] == 2
        assert payload["items"][0]["id"] == "lei:1"
        assert payload["items"][1]["id"] == "proposicao:1"
        assert payload["meta"]["api_version"] == "1.2.0"
        assert payload["meta"]["dataset_version"]
        assert result.headers["x-api-version"] == "1.2.0"
        assert result.headers["x-schema-version"]
        assert result.headers["x-request-id"]

        filtered = client.get("/v1/records", params={"kind": "arquivo"})
        assert filtered.status_code == 200
        assert filtered.json()["page"]["total"] == 1

        stats = client.get("/v1/stats")
        assert stats.status_code == 200
        assert stats.json()["records"] == 3
        assert stats.json()["documents"] == 2
        assert stats.json()["legislation"] == 2
        assert stats.json()["procurements"] == 0
        assert stats.json()["dataset_version"]
        assert stats.json()["fts_enabled"] is True


def test_api_date_range_and_default_chronology(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        listing = client.get("/v1/records")
        assert listing.status_code == 200
        assert [item["id"] for item in listing.json()["items"]] == ["lei:1", "proposicao:1", "arquivo:1"]

        may = client.get("/v1/records", params={"date_from": "2026-05-01", "date_to": "2026-05-31"})
        assert may.status_code == 200
        assert [item["id"] for item in may.json()["items"]] == ["proposicao:1"]

        oldest = client.get("/v1/records", params={"sort": "date_asc"})
        assert oldest.status_code == 200
        assert oldest.json()["items"][0]["id"] == "arquivo:1"

        invalid = client.get("/v1/records", params={"date_from": "2026-06-01", "date_to": "2026-05-01"})
        assert invalid.status_code == 422
        assert invalid.headers["content-type"].startswith("application/problem+json")
        assert invalid.json()["status"] == 422
        assert invalid.json()["request_id"]


def test_documents_legislation_and_procurement_collections(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with Store(database) as store:
        store.upsert_many(
            [
                PublicRecord(
                    id="pncp:compra:1",
                    kind="licitacao",
                    title="Pregão de transporte escolar",
                    summary="Aquisição pública municipal.",
                    date="2026-09-12",
                    year=2026,
                    attributes={"numero_controle_pncp": "12345678000100-1-000001/2026"},
                    source=SourceRef(name="PNCP", url="https://pncp.gov.br/app/editais/1"),
                )
            ]
        )
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        documents = client.get("/v1/documents")
        assert documents.status_code == 200
        assert [item["id"] for item in documents.json()["items"]] == ["lei:1", "arquivo:1"]

        found_document = client.get("/v1/documents", params={"q": "reforma"})
        assert found_document.status_code == 200
        assert found_document.json()["page"]["total"] == 1

        legislation = client.get("/v1/legislation")
        assert legislation.status_code == 200
        assert [item["id"] for item in legislation.json()["items"]] == ["lei:1", "proposicao:1"]

        invalid_kind = client.get("/v1/legislation", params={"kind": "contrato"})
        assert invalid_kind.status_code == 422
        assert invalid_kind.headers["content-type"].startswith("application/problem+json")

        procurements = client.get("/v1/procurements", params={"q": "transporte"})
        assert procurements.status_code == 200
        assert procurements.json()["page"]["total"] == 1
        assert procurements.json()["items"][0]["id"] == "pncp:compra:1"


def test_record_etag_provenance_and_catalog(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False))
    with TestClient(app) as client:
        first = client.get("/v1/records/proposicao:1")
        assert first.status_code == 200
        etag = first.headers["etag"]
        second = client.get("/v1/records/proposicao:1", headers={"If-None-Match": etag})
        assert second.status_code == 304

        provenance = client.get("/v1/records/proposicao:1/provenance")
        assert provenance.status_code == 200
        assert provenance.headers["content-type"].startswith("application/ld+json")
        assert provenance.json()["entity"]["suzano:recordId"] == "proposicao:1"
        assert provenance.json()["storage"]["content_hash"]

        sources = client.get("/v1/sources")
        assert sources.status_code == 200
        assert sources.json()["total"] == 2

        catalog = client.get("/v1/catalog")
        assert catalog.status_code == 200
        assert catalog.headers["content-type"].startswith("application/ld+json")
        assert catalog.json()["@type"] == "dcat:Catalog"
        assert "suzano" in catalog.json()["@context"]

        missing = client.get("/v1/records/nao-existe")
        assert missing.status_code == 404
        assert missing.headers["content-type"].startswith("application/problem+json")


def test_openapi_capabilities_metrics_and_read_only(tmp_path: Path) -> None:
    database = _database(tmp_path)
    app = create_app(ApiSettings(database=database, auto_sync=False, metrics_enabled=True))
    with TestClient(app) as client:
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert schema.json()["info"]["version"] == "1.2.0"
        required = {
            "/v1/search",
            "/v1/documents",
            "/v1/legislation",
            "/v1/procurements",
            "/v1/capabilities",
            "/v1/sources",
            "/v1/catalog",
            "/v1/records/{record_id}/provenance",
        }
        assert required.issubset(schema.json()["paths"])

        capabilities = client.get("/v1/capabilities")
        assert capabilities.status_code == 200
        assert capabilities.json()["read_only"] is True
        assert "RFC 9457 Problem Details" in capabilities.json()["standards"]
        assert "licitacao" in capabilities.json()["record_kinds"]

        client.get("/v1/stats")
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "suzano_api_requests_total" in metrics.text

        assert client.post("/v1/records").status_code == 405


def test_readiness_fails_without_index(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite3"
    app = create_app(ApiSettings(database=missing, auto_sync=False))
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["ready"] is False


def test_pagination_is_bounded_and_validation_is_problem_json(tmp_path: Path) -> None:
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
        assert invalid.headers["content-type"].startswith("application/problem+json")
        assert invalid.json()["type"].endswith("/validation")

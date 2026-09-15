from __future__ import annotations

from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.provenance import dcat_catalog, record_provenance


def test_source_metadata_does_not_rewrite_content_fingerprint() -> None:
    base = PublicRecord(
        id="lei:1",
        kind="lei",
        title="Lei municipal",
        date="2026-09-15",
        year=2026,
        source=SourceRef(name="Câmara", url="https://example.test/lei/1"),
    )
    enriched = base.model_copy(
        update={
            "source": SourceRef(
                name="Câmara",
                url="https://example.test/lei/1",
                authority="Poder Legislativo municipal",
                category="legislacao",
                retrieval_method="html",
                media_type="text/html",
            )
        }
    )
    assert base.fingerprint() == enriched.fingerprint()


def test_record_provenance_is_jsonld_ready() -> None:
    record = PublicRecord(
        id="licitacao:1",
        kind="licitacao",
        title="Pregão 1/2026",
        year=2026,
        source=SourceRef(name="PNCP", url="https://pncp.gov.br/app/editais/1"),
    )
    payload = record_provenance(record)
    assert payload["@context"]["prov"] == "http://www.w3.org/ns/prov#"
    assert payload["source_class"] == "federal_official"
    assert payload["entity"]["suzano:recordId"] == "licitacao:1"
    assert payload["entity"]["suzano:fingerprint"] == record.fingerprint()


def test_dcat_catalog_declares_project_namespace() -> None:
    payload = dcat_catalog(
        stats={"records": 10, "documents": 4, "legislation": 3, "procurements": 2},
        distributions=[{"@type": "dcat:Distribution", "dct:title": "Snapshot"}],
    )
    assert payload["@context"]["suzano"].endswith("/ns#")
    dataset = payload["dcat:dataset"]
    assert dataset["suzano:records"] == 10
    assert dataset["suzano:procurements"] == 2

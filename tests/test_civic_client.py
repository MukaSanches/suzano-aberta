from __future__ import annotations

from datetime import UTC, datetime

import httpx

from suzano_aberta.client import SuzanoClient


def _meta() -> dict[str, object]:
    return {
        "api_version": "1.2.0",
        "schema_version": "2026-09-15",
        "dataset_version": "dataset-v1",
        "request_id": "req-test",
    }


def _record(title: str) -> dict[str, object]:
    return {
        "id": "contrato:1",
        "kind": "contrato",
        "title": title,
        "summary": None,
        "date": "2026-09-16",
        "year": 2026,
        "attributes": {},
        "source": {
            "name": "Fonte",
            "url": "https://example.test/1",
            "collected_at": "2026-09-16T12:00:00Z",
            "content_sha256": None,
            "authority": None,
            "category": None,
            "retrieval_method": None,
            "media_type": None,
        },
    }


def test_client_consumes_quality_history_at_diff_and_manifest() -> None:
    now = datetime.now(UTC).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/quality":
            return httpx.Response(
                200,
                json={
                    "report": {
                        "contract": "core",
                        "contract_version": "1.0.0",
                        "contract_sha256": "a" * 64,
                        "status": "pass",
                        "score": 100,
                        "checked_at": now,
                        "database": "data.sqlite3",
                        "records": 10,
                        "sources": 2,
                        "last_seen": now,
                        "fts_records": 10,
                        "findings": [],
                    },
                    "meta": _meta(),
                },
            )
        if path == "/v1/records/contrato:1/history":
            return httpx.Response(
                200,
                json={
                    "record_id": "contrato:1",
                    "page": {"total": 1, "limit": 50, "offset": 0, "next_offset": None},
                    "items": [
                        {
                            "record_id": "contrato:1",
                            "version": 1,
                            "observed_at": now,
                            "content_hash": "b" * 64,
                            "record": _record("Contrato"),
                        }
                    ],
                    "meta": _meta(),
                },
            )
        if path == "/v1/records/contrato:1/at":
            assert request.url.params["at"]
            return httpx.Response(200, json=_record("Contrato histórico"))
        if path == "/v1/diff":
            assert request.url.params["from"]
            assert request.url.params["to"]
            return httpx.Response(
                200,
                json={
                    "from_time": now,
                    "to_time": now,
                    "total": 0,
                    "new": 0,
                    "changed": 0,
                    "absent": 0,
                    "page": {"total": 0, "limit": 100, "offset": 0, "next_offset": None},
                    "items": [],
                    "meta": _meta(),
                },
            )
        if path == "/v1/manifest":
            return httpx.Response(
                200,
                json={
                    "manifest": {
                        "schema": "suzano-aberta-manifest/v1",
                        "created_at": now,
                        "software_version": "1.0.0",
                        "dataset_version": "dataset-v1",
                        "database_sha256": "c" * 64,
                        "database_bytes": 42,
                        "records": 10,
                        "sources": 2,
                        "contract_status": "pass",
                        "contract_sha256": "a" * 64,
                    },
                    "verification": {
                        "ok": True,
                        "manifest_sha256": "d" * 64,
                        "database_sha256": "c" * 64,
                        "expected_database_sha256": "c" * 64,
                        "database_bytes": 42,
                        "expected_database_bytes": 42,
                    },
                    "meta": _meta(),
                },
            )
        raise AssertionError(path)

    with SuzanoClient(
        "https://api.example.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.quality().report.score == 100
        assert client.history("contrato:1").items[0].version == 1
        assert client.record_at("contrato:1", now).title == "Contrato histórico"
        assert client.diff(now, now).total == 0
        assert client.manifest().verification.ok

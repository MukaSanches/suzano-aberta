from __future__ import annotations

import httpx
import pytest

from suzano_aberta.client import SuzanoApiError, SuzanoClient


def _record(record_id: str, title: str) -> dict[str, object]:
    return {
        "id": record_id,
        "kind": "noticia",
        "title": title,
        "summary": None,
        "date": "2026-09-15",
        "year": 2026,
        "attributes": {},
        "source": {
            "name": "Prefeitura Municipal de Suzano",
            "url": f"https://example.test/{record_id}",
            "collected_at": "2026-09-15T12:00:00Z",
            "content_sha256": None,
            "authority": None,
            "category": None,
            "retrieval_method": None,
            "media_type": None,
        },
    }


def test_client_iterates_records_and_serializes_filters() -> None:
    seen_offsets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/records"
        assert request.url.params["year"] == "2026"
        assert request.url.params["date_from"] == "2026-09-01"
        offset = int(request.url.params.get("offset", "0"))
        seen_offsets.append(offset)
        items = (
            [_record("noticia:1", "Primeira"), _record("noticia:2", "Segunda")]
            if offset == 0
            else [_record("noticia:3", "Terceira")]
        )
        return httpx.Response(
            200,
            json={
                "query": None,
                "filters": {"year": 2026},
                "page": {
                    "total": 3,
                    "limit": 2,
                    "offset": offset,
                    "next_offset": 2 if offset == 0 else None,
                },
                "items": items,
                "meta": {
                    "api_version": "1.2.0",
                    "schema_version": "2026-09-15",
                    "dataset_version": "dataset-1",
                    "request_id": None,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    with SuzanoClient("https://api.example.test", transport=transport) as client:
        records = list(
            client.iter_records(
                year=2026,
                date_from="2026-09-01",
                page_size=2,
            )
        )

    assert [item.id for item in records] == ["noticia:1", "noticia:2", "noticia:3"]
    assert seen_offsets == [0, 2]


def test_client_problem_details_become_typed_exception() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            headers={"X-Request-ID": "req-404"},
            json={
                "type": "https://example.test/problems/http-404",
                "title": "Requisição não concluída",
                "status": 404,
                "detail": "Registro não encontrado.",
                "instance": request.url.path,
                "request_id": "req-404",
                "errors": None,
            },
        )

    with SuzanoClient("https://api.example.test", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SuzanoApiError) as captured:
            client.record("missing")

    assert captured.value.status_code == 404
    assert captured.value.request_id == "req-404"
    assert captured.value.problem is not None
    assert str(captured.value) == "Registro não encontrado."


def test_client_readiness_preserves_degraded_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={
                "status": "degraded",
                "ready": False,
                "records": 0,
                "documents": 0,
                "legislation": 0,
                "procurements": 0,
                "dataset_version": None,
                "detail": "índice indisponível",
            },
        )

    with SuzanoClient("https://api.example.test", transport=httpx.MockTransport(handler)) as client:
        readiness = client.readiness()

    assert readiness.ready is False
    assert readiness.status == "degraded"

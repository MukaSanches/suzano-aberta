from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date, datetime
from types import TracebackType
from typing import Any, Literal, cast

import httpx
from pydantic import ValidationError

from .api.schemas import (
    AutopilotResponse,
    CapabilitiesResponse,
    ChangesResponse,
    HealthResponse,
    ManifestResponse,
    ProblemDetail,
    QualityResponse,
    RecordHistoryResponse,
    RecordsResponse,
    ServiceResponse,
    SnapshotResponse,
    SourcesResponse,
    StatsResponse,
    TemporalDiffResponse,
)
from .models import PublicRecord, RecordKind

SortMode = Literal["date_desc", "date_asc", "relevance"]
DateMode = Literal["effective", "record", "observed"]


class SuzanoApiError(RuntimeError):
    """Erro retornado pela Suzano Aberta API ou pela conexão com ela."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        problem: ProblemDetail | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.problem = problem


class SuzanoClient:
    """Cliente Python tipado e somente leitura para a Suzano Aberta API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float = 20.0,
        user_agent: str = "suzano-aberta-python/1.0",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        normalized = base_url.rstrip("/") + "/"
        self.base_url = normalized
        self._client = httpx.Client(
            base_url=normalized,
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": user_agent},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SuzanoClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @staticmethod
    def _params(values: Mapping[str, object | None]) -> dict[str, str | int]:
        params: dict[str, str | int] = {}
        for key, value in values.items():
            if value is None or value == "":
                continue
            if isinstance(value, (date, datetime)):
                params[key] = value.isoformat()
            elif isinstance(value, bool):
                params[key] = "true" if value else "false"
            elif isinstance(value, int):
                params[key] = value
            else:
                params[key] = str(value)
        return params

    def _get(
        self,
        path: str,
        *,
        params: Mapping[str, object | None] | None = None,
        allow_status: frozenset[int] = frozenset(),
        accept: str = "application/json",
    ) -> httpx.Response:
        try:
            response = self._client.get(
                path.lstrip("/"),
                params=self._params(params or {}),
                headers={"Accept": accept},
            )
        except httpx.HTTPError as exc:
            raise SuzanoApiError(f"Falha de conexão com a Suzano Aberta API: {exc}") from exc

        if response.status_code < 400 or response.status_code in allow_status:
            return response

        problem: ProblemDetail | None = None
        try:
            problem = ProblemDetail.model_validate(response.json())
        except (ValueError, ValidationError):
            pass

        request_id = response.headers.get("X-Request-ID")
        if problem is not None:
            request_id = problem.request_id or request_id
            message = problem.detail
        else:
            body = response.text.strip()
            message = body[:500] if body else f"HTTP {response.status_code}"

        raise SuzanoApiError(
            message,
            status_code=response.status_code,
            request_id=request_id,
            problem=problem,
        )

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        return response.json()

    def service(self) -> ServiceResponse:
        return ServiceResponse.model_validate(self._json(self._get("/")))

    def liveness(self) -> HealthResponse:
        return HealthResponse.model_validate(self._json(self._get("/health/live")))

    def readiness(self) -> HealthResponse:
        response = self._get("/health/ready", allow_status=frozenset({503}))
        return HealthResponse.model_validate(self._json(response))

    def autopilot(self) -> AutopilotResponse:
        return AutopilotResponse.model_validate(self._json(self._get("/v1/autopilot")))

    def quality(self) -> QualityResponse:
        return QualityResponse.model_validate(self._json(self._get("/v1/quality")))

    def manifest(self) -> ManifestResponse:
        return ManifestResponse.model_validate(self._json(self._get("/v1/manifest")))

    def capabilities(self) -> CapabilitiesResponse:
        return CapabilitiesResponse.model_validate(self._json(self._get("/v1/capabilities")))

    def stats(self) -> StatsResponse:
        return StatsResponse.model_validate(self._json(self._get("/v1/stats")))

    def sources(self) -> SourcesResponse:
        return SourcesResponse.model_validate(self._json(self._get("/v1/sources")))

    def snapshot(self) -> SnapshotResponse:
        return SnapshotResponse.model_validate(self._json(self._get("/v1/snapshot")))

    def catalog(self) -> dict[str, Any]:
        payload = self._json(self._get("/v1/catalog"))
        if not isinstance(payload, dict):
            raise SuzanoApiError("Resposta inesperada do catálogo da API.")
        return cast(dict[str, Any], payload)

    def provenance(self, record_id: str) -> dict[str, Any]:
        payload = self._json(self._get(f"/v1/records/{record_id}/provenance"))
        if not isinstance(payload, dict):
            raise SuzanoApiError("Resposta inesperada de proveniência da API.")
        return cast(dict[str, Any], payload)

    def record(self, record_id: str) -> PublicRecord:
        response = self._get(f"/v1/records/{record_id}")
        return PublicRecord.model_validate(self._json(response))

    def record_at(self, record_id: str, at: datetime | str) -> PublicRecord:
        response = self._get(f"/v1/records/{record_id}/at", params={"at": at})
        return PublicRecord.model_validate(self._json(response))

    def history(
        self,
        record_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> RecordHistoryResponse:
        response = self._get(
            f"/v1/records/{record_id}/history",
            params={"limit": limit, "offset": offset},
        )
        return RecordHistoryResponse.model_validate(self._json(response))

    def diff(
        self,
        from_time: datetime | str,
        to_time: datetime | str,
        *,
        kind: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> TemporalDiffResponse:
        response = self._get(
            "/v1/diff",
            params={
                "from": from_time,
                "to": to_time,
                "kind": kind,
                "limit": limit,
                "offset": offset,
            },
        )
        return TemporalDiffResponse.model_validate(self._json(response))

    def changes_feed_atom(self, *, limit: int = 50) -> str:
        response = self._get(
            "/v1/feed/changes.atom",
            params={"limit": limit},
            accept="application/atom+xml",
        )
        return response.text

    def search(
        self,
        query: str,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 30,
        offset: int = 0,
    ) -> RecordsResponse:
        response = self._get(
            "/v1/search",
            params={
                "q": query,
                "kind": kind,
                "year": year,
                "source": source,
                "date_from": date_from,
                "date_to": date_to,
                "date_mode": date_mode,
                "sort": sort,
                "limit": limit,
                "offset": offset,
            },
        )
        return RecordsResponse.model_validate(self._json(response))

    def records(
        self,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> RecordsResponse:
        response = self._get(
            "/v1/records",
            params={
                "kind": kind,
                "year": year,
                "source": source,
                "date_from": date_from,
                "date_to": date_to,
                "date_mode": date_mode,
                "sort": sort,
                "limit": limit,
                "offset": offset,
            },
        )
        return RecordsResponse.model_validate(self._json(response))

    def documents(
        self,
        query: str = "",
        *,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> RecordsResponse:
        response = self._get(
            "/v1/documents",
            params={
                "q": query,
                "year": year,
                "source": source,
                "date_from": date_from,
                "date_to": date_to,
                "date_mode": date_mode,
                "sort": sort,
                "limit": limit,
                "offset": offset,
            },
        )
        return RecordsResponse.model_validate(self._json(response))

    def legislation(
        self,
        query: str = "",
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> RecordsResponse:
        response = self._get(
            "/v1/legislation",
            params={
                "q": query,
                "kind": kind,
                "year": year,
                "date_from": date_from,
                "date_to": date_to,
                "date_mode": date_mode,
                "sort": sort,
                "limit": limit,
                "offset": offset,
            },
        )
        return RecordsResponse.model_validate(self._json(response))

    def procurements(
        self,
        query: str = "",
        *,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> RecordsResponse:
        response = self._get(
            "/v1/procurements",
            params={
                "q": query,
                "year": year,
                "source": source,
                "date_from": date_from,
                "date_to": date_to,
                "date_mode": date_mode,
                "sort": sort,
                "limit": limit,
                "offset": offset,
            },
        )
        return RecordsResponse.model_validate(self._json(response))

    def changes(
        self,
        *,
        kind: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ChangesResponse:
        response = self._get(
            "/v1/changes",
            params={"kind": kind, "limit": limit, "offset": offset},
        )
        return ChangesResponse.model_validate(self._json(response))

    def iter_records(
        self,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        page_size: int = 100,
        max_items: int | None = None,
    ) -> Iterator[PublicRecord]:
        offset = 0
        emitted = 0
        while True:
            page = self.records(
                kind=kind,
                year=year,
                source=source,
                date_from=date_from,
                date_to=date_to,
                date_mode=date_mode,
                sort=sort,
                limit=page_size,
                offset=offset,
            )
            for item in page.items:
                if max_items is not None and emitted >= max_items:
                    return
                yield item
                emitted += 1
            if page.page.next_offset is None:
                return
            offset = page.page.next_offset

    def iter_search(
        self,
        query: str,
        *,
        kind: RecordKind | None = None,
        year: int | None = None,
        source: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        date_mode: DateMode = "effective",
        sort: SortMode = "date_desc",
        page_size: int = 100,
        max_items: int | None = None,
    ) -> Iterator[PublicRecord]:
        offset = 0
        emitted = 0
        while True:
            page = self.search(
                query,
                kind=kind,
                year=year,
                source=source,
                date_from=date_from,
                date_to=date_to,
                date_mode=date_mode,
                sort=sort,
                limit=page_size,
                offset=offset,
            )
            for item in page.items:
                if max_items is not None and emitted >= max_items:
                    return
                yield item
                emitted += 1
            if page.page.next_offset is None:
                return
            offset = page.page.next_offset

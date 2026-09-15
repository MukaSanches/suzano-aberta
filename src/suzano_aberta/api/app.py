from __future__ import annotations

import asyncio
import importlib.metadata
import sqlite3
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, suppress
from datetime import date
from hashlib import sha256
from typing import Any, cast

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from ..models import PublicRecord, RecordKind
from ..provenance import PORTAL_URL, dcat_catalog, record_provenance
from ..snapshot import LATEST_SNAPSHOT_URL
from .repository import ApiRepository, DateMode, SortMode
from .schemas import (
    CapabilitiesResponse,
    ChangesResponse,
    HealthResponse,
    PageInfo,
    ProblemDetail,
    RecordsResponse,
    ResponseMeta,
    ServiceResponse,
    SnapshotResponse,
    SourceCount,
    SourcesResponse,
    SourceSummary,
    StatsResponse,
)
from .settings import ApiSettings
from .telemetry import ApiMetrics

API_VERSION = "1.2.0"
SCHEMA_VERSION = "2026-09-15"
MAX_PAGE_SIZE = 100
MAX_OFFSET = 100_000


def _package_version() -> str:
    try:
        return importlib.metadata.version("suzano-aberta")
    except importlib.metadata.PackageNotFoundError:
        return "0.5.0"


def _page(total: int, *, limit: int, offset: int) -> PageInfo:
    next_offset = offset + limit if offset + limit < total else None
    return PageInfo(total=total, limit=limit, offset=offset, next_offset=next_offset)


def _date_value(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _validate_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from não pode ser posterior a date_to.")


def _problem(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    problem_type: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    payload = ProblemDetail(
        type=problem_type,
        title=title,
        status=status,
        detail=detail,
        instance=str(request.url.path),
        request_id=request_id,
        errors=errors,
    ).model_dump(mode="json")
    return JSONResponse(status_code=status, content=payload, media_type="application/problem+json")


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    resolved = settings or ApiSettings.from_env()
    metrics = ApiMetrics()

    def needs_snapshot() -> bool:
        if not resolved.database.exists():
            return True
        try:
            with ApiRepository(resolved.database) as repository:
                return cast(int, repository.stats()["records"]) == 0
        except (OSError, sqlite3.Error):
            return True

    async def sync_snapshot() -> str | None:
        try:
            from ..snapshot import sync_latest_snapshot

            await asyncio.to_thread(sync_latest_snapshot, resolved.database)
            return None
        except Exception as exc:
            return f"{type(exc).__name__}: {exc}"

    async def periodic_sync(app: FastAPI) -> None:
        while True:
            await asyncio.sleep(resolved.sync_interval_seconds)
            app.state.last_sync_error = await sync_snapshot()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.last_sync_error = None
        if resolved.auto_sync and needs_snapshot():
            app.state.last_sync_error = await sync_snapshot()
        task: asyncio.Task[None] | None = None
        if resolved.auto_sync and resolved.sync_interval_seconds > 0:
            task = asyncio.create_task(periodic_sync(app))
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(
        title="Suzano Aberta API",
        summary="API pública, somente leitura, para consulta rastreável ao acervo digital de Suzano.",
        description=(
            "Camada HTTP sobre snapshots validados do Suzano Aberta. O serviço é somente leitura, "
            "preserva proveniência, expõe catálogo interoperável e mantém limites explícitos de consumo."
        ),
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={"name": "Suzano Aberta", "url": "https://github.com/MukaSanches/suzano-aberta"},
        license_info={"name": "Apache-2.0"},
        openapi_tags=[
            {"name": "sistema", "description": "Estado, capacidades e metadados operacionais."},
            {"name": "acervo", "description": "Pesquisa e leitura de todo o acervo público."},
            {"name": "documentos", "description": "Documentos e arquivos públicos indexados."},
            {"name": "legislacao", "description": "Leis, decretos e proposições municipais."},
            {"name": "contratacoes", "description": "Licitações, contratos e atas de múltiplas fontes públicas."},
            {"name": "proveniencia", "description": "Rastreabilidade e catálogo interoperável."},
            {"name": "historico", "description": "Mudanças observadas entre coletas."},
        ],
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    if resolved.allowed_hosts != ("*",):
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(resolved.allowed_hosts))
    if resolved.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "HEAD", "OPTIONS"],
            allow_headers=["Accept", "Content-Type", "If-None-Match", "X-Request-ID"],
            expose_headers=[
                "ETag",
                "X-Request-ID",
                "Server-Timing",
                "X-API-Version",
                "X-Schema-Version",
                "X-Dataset-Version",
            ],
            max_age=3600,
        )

    def dataset_etag(request: Request) -> str | None:
        if request.method not in {"GET", "HEAD"} or not request.url.path.startswith("/v1/"):
            return None
        try:
            stat = resolved.database.stat()
        except OSError:
            return None
        raw = f"{API_VERSION}|{SCHEMA_VERSION}|{stat.st_size}|{stat.st_mtime_ns}|{request.url.path}|{request.url.query}"
        return f'W/"{sha256(raw.encode()).hexdigest()[:32]}"'

    @app.middleware("http")
    async def observability(request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        etag = dataset_etag(request)
        if etag and request.headers.get("If-None-Match") == etag:
            response = Response(status_code=304)
            response.headers["ETag"] = etag
            response.headers["X-Request-ID"] = request_id
            return response

        started = time.perf_counter()
        response = cast(Response, await call_next(request))
        elapsed_ms = (time.perf_counter() - started) * 1000
        route = getattr(request.scope.get("route"), "path", request.url.path)
        metrics.observe(method=request.method, route=str(route), status=response.status_code, duration_ms=elapsed_ms)

        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.2f}"
        response.headers["X-API-Version"] = API_VERSION
        response.headers["X-Schema-Version"] = SCHEMA_VERSION
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        if etag and response.status_code == 200:
            response.headers["ETag"] = etag
        return response

    @app.exception_handler(HTTPException)
    async def http_problem(request: Request, exc: HTTPException) -> JSONResponse:
        detail = str(exc.detail)
        return _problem(
            request,
            status=exc.status_code,
            title="Requisição não concluída",
            detail=detail,
            problem_type=f"https://mukasanches.github.io/suzano-aberta/problems/http-{exc.status_code}",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_problem(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            request,
            status=422,
            title="Parâmetros inválidos",
            detail="Um ou mais parâmetros não atendem ao contrato da API.",
            problem_type="https://mukasanches.github.io/suzano-aberta/problems/validation",
            errors=[dict(item) for item in exc.errors()],
        )

    def repository_dependency() -> Iterator[ApiRepository]:
        try:
            repository = ApiRepository(resolved.database)
        except (FileNotFoundError, OSError) as exc:
            raise HTTPException(status_code=503, detail="Índice local ainda não está disponível.") from exc
        try:
            yield repository
        finally:
            repository.close()

    def response_meta(request: Request, repository: ApiRepository) -> ResponseMeta:
        return ResponseMeta(
            api_version=API_VERSION,
            schema_version=SCHEMA_VERSION,
            dataset_version=repository.dataset_version(),
            request_id=getattr(request.state, "request_id", None),
        )

    @app.get("/", response_model=ServiceResponse, tags=["sistema"])
    def root() -> ServiceResponse:
        return ServiceResponse(
            name="Suzano Aberta API",
            api_version=API_VERSION,
            schema_version=SCHEMA_VERSION,
            package_version=_package_version(),
            description="Consulta pública, cronológica, rastreável e interoperável ao acervo digital de Suzano.",
            documentation="/docs",
            openapi="/openapi.json",
            endpoints={
                "search": "/v1/search?q=educacao&sort=date_desc",
                "records": "/v1/records",
                "documents": "/v1/documents",
                "legislation": "/v1/legislation",
                "procurements": "/v1/procurements",
                "record": "/v1/records/{id}",
                "provenance": "/v1/records/{id}/provenance",
                "sources": "/v1/sources",
                "catalog": "/v1/catalog",
                "capabilities": "/v1/capabilities",
                "stats": "/v1/stats",
                "changes": "/v1/changes",
                "snapshot": "/v1/snapshot",
                "metrics": "/metrics",
            },
        )

    @app.get("/health/live", response_model=HealthResponse, tags=["sistema"])
    def live() -> HealthResponse:
        return HealthResponse(status="ok", ready=True)

    @app.get("/health/ready", response_model=HealthResponse, tags=["sistema"])
    def ready() -> Any:
        try:
            with ApiRepository(resolved.database) as repository:
                base = repository.stats()
                total = cast(int, base["records"])
                documents = cast(int, base["documents"])
                legislation = cast(int, base["legislation"])
                procurements = cast(int, base["procurements"])
                dataset_version = repository.dataset_version()
            if total < 1:
                raise RuntimeError("índice vazio")
            if documents < 1:
                raise RuntimeError("índice sem documentos")
            if legislation < 1:
                raise RuntimeError("índice sem legislação/proposições")
        except Exception as exc:
            detail = getattr(app.state, "last_sync_error", None) or str(exc)
            payload = HealthResponse(status="degraded", ready=False, detail=detail)
            return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))
        return HealthResponse(
            status="ok",
            ready=True,
            records=total,
            documents=documents,
            legislation=legislation,
            procurements=procurements,
            dataset_version=dataset_version,
        )

    @app.get("/v1/capabilities", response_model=CapabilitiesResponse, tags=["sistema"])
    def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse(
            api_version=API_VERSION,
            schema_version=SCHEMA_VERSION,
            read_only=True,
            formats=["application/json", "application/problem+json", "application/ld+json", "text/plain; version=0.0.4"],
            pagination={"mode": "offset", "max_page_size": MAX_PAGE_SIZE, "max_offset": MAX_OFFSET},
            sorting=["date_desc", "date_asc", "relevance"],
            date_modes=["effective", "record", "observed"],
            record_kinds=list(cast(tuple[str, ...], __import__("typing").get_args(RecordKind))),
            standards=["OpenAPI 3", "RFC 9457 Problem Details", "W3C PROV", "W3C DCAT 3"],
            endpoints={
                "catalog": "/v1/catalog",
                "sources": "/v1/sources",
                "provenance": "/v1/records/{id}/provenance",
                "bulk_snapshot": "/v1/snapshot",
            },
        )

    @app.get("/v1/search", response_model=RecordsResponse, tags=["acervo"])
    def search(
        request: Request,
        response: Response,
        q: str = Query(min_length=1, max_length=200),
        kind: RecordKind | None = Query(default=None),
        year: int | None = Query(default=None, ge=1900, le=2100),
        source: str | None = Query(default=None, min_length=2, max_length=120),
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
        date_mode: DateMode = Query(default="effective"),
        sort: SortMode = Query(default="date_desc"),
        limit: int = Query(default=30, ge=1, le=MAX_PAGE_SIZE),
        offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> RecordsResponse:
        _validate_range(date_from, date_to)
        items, total = repository.search(
            q, kind=kind, year=year, source=source,
            date_from=_date_value(date_from), date_to=_date_value(date_to),
            date_mode=date_mode, sort=sort, limit=limit, offset=offset,
        )
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
        return RecordsResponse(
            query=q,
            filters={"kind": kind, "year": year, "source": source, "date_from": _date_value(date_from), "date_to": _date_value(date_to), "date_mode": date_mode, "sort": sort},
            page=_page(total, limit=limit, offset=offset), items=items, meta=response_meta(request, repository),
        )

    @app.get("/v1/records", response_model=RecordsResponse, tags=["acervo"])
    def records(
        request: Request,
        response: Response,
        kind: RecordKind | None = Query(default=None),
        year: int | None = Query(default=None, ge=1900, le=2100),
        source: str | None = Query(default=None, min_length=2, max_length=120),
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
        date_mode: DateMode = Query(default="effective"),
        sort: SortMode = Query(default="date_desc"),
        limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
        offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> RecordsResponse:
        _validate_range(date_from, date_to)
        items, total = repository.list_records(
            kind=kind, year=year, source=source,
            date_from=_date_value(date_from), date_to=_date_value(date_to),
            date_mode=date_mode, sort=sort, limit=limit, offset=offset,
        )
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
        return RecordsResponse(
            filters={"kind": kind, "year": year, "source": source, "date_from": _date_value(date_from), "date_to": _date_value(date_to), "date_mode": date_mode, "sort": sort},
            page=_page(total, limit=limit, offset=offset), items=items, meta=response_meta(request, repository),
        )

    def collection_response(
        *, request: Request, response: Response, repository: ApiRepository,
        scope: str, q: str, items: list[PublicRecord], total: int, year: int | None,
        source: str | None, date_from: date | None, date_to: date | None,
        date_mode: DateMode, sort: SortMode, limit: int, offset: int,
    ) -> RecordsResponse:
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
        return RecordsResponse(
            query=q or None,
            filters={"scope": scope, "year": year, "source": source, "date_from": _date_value(date_from), "date_to": _date_value(date_to), "date_mode": date_mode, "sort": sort},
            page=_page(total, limit=limit, offset=offset), items=items, meta=response_meta(request, repository),
        )

    @app.get("/v1/documents", response_model=RecordsResponse, tags=["documentos"])
    def documents(
        request: Request, response: Response,
        q: str = Query(default="", max_length=200), year: int | None = Query(default=None, ge=1900, le=2100),
        source: str | None = Query(default=None, min_length=2, max_length=120),
        date_from: date | None = Query(default=None), date_to: date | None = Query(default=None),
        date_mode: DateMode = Query(default="effective"), sort: SortMode = Query(default="date_desc"),
        limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> RecordsResponse:
        _validate_range(date_from, date_to)
        items, total = repository.documents(q, year=year, source=source, date_from=_date_value(date_from), date_to=_date_value(date_to), date_mode=date_mode, sort=sort, limit=limit, offset=offset)
        return collection_response(request=request, response=response, repository=repository, scope="documents", q=q, items=items, total=total, year=year, source=source, date_from=date_from, date_to=date_to, date_mode=date_mode, sort=sort, limit=limit, offset=offset)

    @app.get("/v1/legislation", response_model=RecordsResponse, tags=["legislacao"])
    def legislation(
        request: Request, response: Response,
        q: str = Query(default="", max_length=200), kind: RecordKind | None = Query(default=None),
        year: int | None = Query(default=None, ge=1900, le=2100),
        date_from: date | None = Query(default=None), date_to: date | None = Query(default=None),
        date_mode: DateMode = Query(default="effective"), sort: SortMode = Query(default="date_desc"),
        limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> RecordsResponse:
        _validate_range(date_from, date_to)
        if kind is not None and kind not in {"lei", "decreto", "proposicao"}:
            raise HTTPException(status_code=422, detail="kind deve ser lei, decreto ou proposicao neste endpoint.")
        if kind is None:
            items, total = repository.legislation(q, year=year, date_from=_date_value(date_from), date_to=_date_value(date_to), date_mode=date_mode, sort=sort, limit=limit, offset=offset)
        else:
            items, total = repository.search(q, kind=kind, year=year, date_from=_date_value(date_from), date_to=_date_value(date_to), date_mode=date_mode, sort=sort, limit=limit, offset=offset)
        result = collection_response(request=request, response=response, repository=repository, scope="legislation", q=q, items=items, total=total, year=year, source=None, date_from=date_from, date_to=date_to, date_mode=date_mode, sort=sort, limit=limit, offset=offset)
        result.filters["kind"] = kind
        return result

    @app.get("/v1/procurements", response_model=RecordsResponse, tags=["contratacoes"])
    def procurements(
        request: Request, response: Response,
        q: str = Query(default="", max_length=200), year: int | None = Query(default=None, ge=1900, le=2100),
        source: str | None = Query(default=None, min_length=2, max_length=120),
        date_from: date | None = Query(default=None), date_to: date | None = Query(default=None),
        date_mode: DateMode = Query(default="effective"), sort: SortMode = Query(default="date_desc"),
        limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> RecordsResponse:
        _validate_range(date_from, date_to)
        items, total = repository.procurements(q, year=year, source=source, date_from=_date_value(date_from), date_to=_date_value(date_to), date_mode=date_mode, sort=sort, limit=limit, offset=offset)
        return collection_response(request=request, response=response, repository=repository, scope="procurements", q=q, items=items, total=total, year=year, source=source, date_from=date_from, date_to=date_to, date_mode=date_mode, sort=sort, limit=limit, offset=offset)

    @app.get("/v1/records/{record_id}", response_model=PublicRecord, tags=["acervo"])
    def record(record_id: str, request: Request, response: Response, repository: ApiRepository = Depends(repository_dependency)) -> Any:
        item = repository.get(record_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")
        etag = f'"{item.fingerprint()}"'
        if request.headers.get("If-None-Match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
        return item

    @app.get("/v1/records/{record_id}/provenance", tags=["proveniencia"])
    def provenance(record_id: str, repository: ApiRepository = Depends(repository_dependency)) -> JSONResponse:
        item = repository.get(record_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")
        payload = record_provenance(item)
        payload["storage"] = repository.record_storage_metadata(record_id)
        return JSONResponse(content=payload, media_type="application/ld+json")

    @app.get("/v1/sources", response_model=SourcesResponse, tags=["proveniencia"])
    def sources(request: Request, repository: ApiRepository = Depends(repository_dependency)) -> SourcesResponse:
        rows = repository.source_catalog()
        return SourcesResponse(
            items=[SourceSummary(**row) for row in rows],
            total=len(rows),
            meta=response_meta(request, repository),
        )

    @app.get("/v1/catalog", tags=["proveniencia"])
    def catalog(repository: ApiRepository = Depends(repository_dependency)) -> JSONResponse:
        stats = repository.stats()
        base = LATEST_SNAPSHOT_URL.rsplit("/", 1)[0]
        payload = dcat_catalog(
            stats=stats,
            distributions=[
                {"@type": "dcat:Distribution", "dct:title": "API JSON", "dcat:accessURL": f"{PORTAL_URL}desenvolvedores.html", "dcat:mediaType": "application/json"},
                {"@type": "dcat:Distribution", "dct:title": "Snapshot SQLite", "dcat:downloadURL": LATEST_SNAPSHOT_URL, "dcat:mediaType": "application/vnd.sqlite3"},
                {"@type": "dcat:Distribution", "dct:title": "Metadados do snapshot", "dcat:downloadURL": f"{base}/data-latest.json", "dcat:mediaType": "application/json"},
            ],
        )
        return JSONResponse(content=payload, media_type="application/ld+json")

    @app.get("/v1/stats", response_model=StatsResponse, tags=["sistema"])
    def stats(response: Response, repository: ApiRepository = Depends(repository_dependency)) -> StatsResponse:
        base = repository.stats()
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
        return StatsResponse(
            records=cast(int, base["records"]), documents=cast(int, base["documents"]),
            legislation=cast(int, base["legislation"]), procurements=cast(int, base["procurements"]),
            first_seen=base["first_seen"] if isinstance(base["first_seen"], str) else None,
            last_seen=base["last_seen"] if isinstance(base["last_seen"], str) else None,
            fts_enabled=cast(bool, base["fts_enabled"]), database_bytes=cast(int, base["database_bytes"]),
            sqlite_version=str(base["sqlite_version"]), dataset_version=repository.dataset_version(),
            kinds=repository.counts_by_kind(),
            top_sources=[SourceCount(name=name, records=count) for name, count in repository.source_counts(limit=50)],
        )

    @app.get("/v1/changes", response_model=ChangesResponse, tags=["historico"])
    def changes(
        request: Request, response: Response,
        kind: str | None = Query(default=None, min_length=2, max_length=80),
        limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> ChangesResponse:
        items, total = repository.changes(kind=kind, limit=limit, offset=offset)
        response.headers["Cache-Control"] = "public, max-age=15, stale-while-revalidate=30"
        return ChangesResponse(page=_page(total, limit=limit, offset=offset), items=items, meta=response_meta(request, repository))

    @app.get("/v1/snapshot", response_model=SnapshotResponse, tags=["sistema"])
    def snapshot(response: Response) -> SnapshotResponse:
        base = LATEST_SNAPSHOT_URL.rsplit("/", 1)[0]
        response.headers["Cache-Control"] = "public, max-age=300"
        return SnapshotResponse(
            database_url=LATEST_SNAPSHOT_URL,
            checksum_url=f"{LATEST_SNAPSHOT_URL}.sha256",
            metadata_url=f"{base}/data-latest.json",
            note="Para cargas em massa, prefira o snapshot ao invés de paginar toda a API.",
        )

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> PlainTextResponse:
        if not resolved.metrics_enabled:
            return PlainTextResponse("metrics disabled\n", status_code=404)
        return PlainTextResponse(metrics.prometheus(), media_type="text/plain; version=0.0.4; charset=utf-8")

    return app

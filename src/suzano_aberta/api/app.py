from __future__ import annotations

import asyncio
import importlib.metadata
import sqlite3
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, suppress
from typing import Any, cast

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from ..models import PublicRecord, RecordKind
from ..snapshot import LATEST_SNAPSHOT_URL
from .repository import ApiRepository
from .schemas import (
    ChangesResponse,
    HealthResponse,
    PageInfo,
    RecordsResponse,
    ServiceResponse,
    SnapshotResponse,
    SourceCount,
    StatsResponse,
)
from .settings import ApiSettings

API_VERSION = "1.0.0"


def _package_version() -> str:
    try:
        return importlib.metadata.version("suzano-aberta")
    except importlib.metadata.PackageNotFoundError:
        return "0.4.0"


def _page(total: int, *, limit: int, offset: int) -> PageInfo:
    next_offset = offset + limit if offset + limit < total else None
    return PageInfo(total=total, limit=limit, offset=offset, next_offset=next_offset)


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    resolved = settings or ApiSettings.from_env()

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
        summary="API pública de consulta ao acervo digital do município de Suzano.",
        description=(
            "Camada HTTP somente leitura sobre o índice Suzano Aberta. "
            "Todos os registros preservam a fonte pública de origem."
        ),
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={"name": "Suzano Aberta", "url": "https://github.com/MukaSanches/suzano-aberta"},
        license_info={"name": "Apache-2.0"},
        openapi_tags=[
            {"name": "sistema", "description": "Estado e metadados da API."},
            {"name": "acervo", "description": "Pesquisa e leitura do acervo público."},
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
            expose_headers=["ETag", "X-Request-ID", "Server-Timing"],
            max_age=3600,
        )

    @app.middleware("http")
    async def observability(request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        started = time.perf_counter()
        response = cast(Response, await call_next(request))
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def repository_dependency() -> Iterator[ApiRepository]:
        try:
            repository = ApiRepository(resolved.database)
        except (FileNotFoundError, OSError) as exc:
            raise HTTPException(status_code=503, detail="Índice local ainda não está disponível.") from exc
        try:
            yield repository
        finally:
            repository.close()

    @app.get("/", response_model=ServiceResponse, tags=["sistema"])
    def root() -> ServiceResponse:
        return ServiceResponse(
            name="Suzano Aberta API",
            api_version=API_VERSION,
            package_version=_package_version(),
            description="Consulta pública, rápida e rastreável ao acervo digital de Suzano.",
            documentation="/docs",
            openapi="/openapi.json",
            endpoints={
                "search": "/v1/search?q=educacao",
                "records": "/v1/records",
                "record": "/v1/records/{id}",
                "stats": "/v1/stats",
                "changes": "/v1/changes",
                "snapshot": "/v1/snapshot",
            },
        )

    @app.get("/health/live", response_model=HealthResponse, tags=["sistema"])
    def live() -> HealthResponse:
        return HealthResponse(status="ok", ready=True)

    @app.get("/health/ready", response_model=HealthResponse, tags=["sistema"])
    def ready() -> Any:
        try:
            with ApiRepository(resolved.database) as repository:
                total = cast(int, repository.stats()["records"])
            if total < 1:
                raise RuntimeError("índice vazio")
        except Exception as exc:
            detail = getattr(app.state, "last_sync_error", None) or str(exc)
            payload = HealthResponse(status="degraded", ready=False, detail=detail)
            return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))
        return HealthResponse(status="ok", ready=True, records=total)

    @app.get("/v1/search", response_model=RecordsResponse, tags=["acervo"])
    def search(
        response: Response,
        q: str = Query(min_length=1, max_length=200, description="Termo ou expressão a pesquisar."),
        kind: RecordKind | None = Query(default=None, description="Filtra pelo tipo de registro."),
        year: int | None = Query(default=None, ge=1900, le=2100),
        source: str | None = Query(default=None, min_length=2, max_length=120),
        limit: int = Query(default=30, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=100_000),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> RecordsResponse:
        items, total = repository.search(
            q,
            kind=kind,
            year=year,
            source=source,
            limit=limit,
            offset=offset,
        )
        response.headers["Cache-Control"] = "public, max-age=30"
        return RecordsResponse(
            query=q,
            filters={"kind": kind, "year": year, "source": source},
            page=_page(total, limit=limit, offset=offset),
            items=items,
        )

    @app.get("/v1/records", response_model=RecordsResponse, tags=["acervo"])
    def records(
        response: Response,
        kind: RecordKind | None = Query(default=None),
        year: int | None = Query(default=None, ge=1900, le=2100),
        source: str | None = Query(default=None, min_length=2, max_length=120),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=100_000),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> RecordsResponse:
        items, total = repository.list_records(
            kind=kind,
            year=year,
            source=source,
            limit=limit,
            offset=offset,
        )
        response.headers["Cache-Control"] = "public, max-age=60"
        return RecordsResponse(
            filters={"kind": kind, "year": year, "source": source},
            page=_page(total, limit=limit, offset=offset),
            items=items,
        )

    @app.get("/v1/records/{record_id}", response_model=PublicRecord, tags=["acervo"])
    def record(
        record_id: str,
        request: Request,
        response: Response,
        repository: ApiRepository = Depends(repository_dependency),
    ) -> Any:
        item = repository.get(record_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")
        etag = f'"{item.fingerprint()}"'
        if request.headers.get("If-None-Match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=300"
        return item

    @app.get("/v1/stats", response_model=StatsResponse, tags=["sistema"])
    def stats(
        response: Response,
        repository: ApiRepository = Depends(repository_dependency),
    ) -> StatsResponse:
        base = repository.stats()
        response.headers["Cache-Control"] = "public, max-age=60"
        return StatsResponse(
            records=cast(int, base["records"]),
            first_seen=base["first_seen"] if isinstance(base["first_seen"], str) else None,
            last_seen=base["last_seen"] if isinstance(base["last_seen"], str) else None,
            fts_enabled=cast(bool, base["fts_enabled"]),
            database_bytes=cast(int, base["database_bytes"]),
            sqlite_version=str(base["sqlite_version"]),
            kinds=repository.counts_by_kind(),
            top_sources=[
                SourceCount(name=name, records=count)
                for name, count in repository.source_counts(limit=50)
            ],
        )

    @app.get("/v1/changes", response_model=ChangesResponse, tags=["historico"])
    def changes(
        response: Response,
        kind: str | None = Query(default=None, min_length=2, max_length=80),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=100_000),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> ChangesResponse:
        items, total = repository.changes(kind=kind, limit=limit, offset=offset)
        response.headers["Cache-Control"] = "public, max-age=15"
        return ChangesResponse(page=_page(total, limit=limit, offset=offset), items=items)

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

    return app

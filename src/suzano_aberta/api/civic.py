from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import Response as FastAPIResponse

from ..content_store import ManifestVerification, SnapshotManifest, load_manifest, verify_manifest
from ..contracts import validate_database_contract
from ..models import PublicRecord
from ..release import build_snapshot_manifest, manifest_path_for
from .repository import ApiRepository
from .schemas import (
    ManifestResponse,
    PageInfo,
    QualityResponse,
    RecordHistoryResponse,
    ResponseMeta,
    TemporalDiffResponse,
)
from .settings import ApiSettings


def _page(total: int, *, limit: int, offset: int) -> PageInfo:
    next_offset = offset + limit if offset + limit < total else None
    return PageInfo(total=total, limit=limit, offset=offset, next_offset=next_offset)


def install_civic_routes(
    app: FastAPI,
    settings: ApiSettings,
    *,
    api_version: str,
    schema_version: str,
) -> None:
    router = APIRouter()

    def repository_dependency() -> Iterator[ApiRepository]:
        try:
            repository = ApiRepository(settings.database)
        except (FileNotFoundError, OSError) as exc:
            raise HTTPException(status_code=503, detail="Índice local ainda não está disponível.") from exc
        try:
            yield repository
        finally:
            repository.close()

    def meta(request: Request, repository: ApiRepository) -> ResponseMeta:
        return ResponseMeta(
            api_version=api_version,
            schema_version=schema_version,
            dataset_version=repository.dataset_version(),
            request_id=getattr(request.state, "request_id", None),
        )

    @router.get("/v1/quality", response_model=QualityResponse, tags=["sistema"])
    def quality(
        request: Request,
        repository: ApiRepository = Depends(repository_dependency),
    ) -> QualityResponse:
        report = validate_database_contract(settings.database)
        return QualityResponse(report=report, meta=meta(request, repository))

    @router.get(
        "/v1/records/{record_id}/history",
        response_model=RecordHistoryResponse,
        tags=["historico"],
    )
    def record_history(
        record_id: str,
        request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=100_000),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> RecordHistoryResponse:
        if repository.get(record_id) is None:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")
        items, total = repository.record_history(record_id, limit=limit, offset=offset)
        return RecordHistoryResponse(
            record_id=record_id,
            page=_page(total, limit=limit, offset=offset),
            items=items,
            meta=meta(request, repository),
        )

    @router.get(
        "/v1/records/{record_id}/at",
        response_model=PublicRecord,
        tags=["historico"],
    )
    def record_at(
        record_id: str,
        at: datetime = Query(description="Instante ISO-8601 da visão histórica desejada."),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> PublicRecord:
        record = repository.record_at(record_id, at)
        if record is None:
            raise HTTPException(status_code=404, detail="Não há versão observada desse registro no instante informado.")
        return record

    @router.get("/v1/diff", response_model=TemporalDiffResponse, tags=["historico"])
    def temporal_diff(
        request: Request,
        from_time: datetime = Query(alias="from", description="Início exclusivo do intervalo ISO-8601."),
        to_time: datetime = Query(alias="to", description="Fim inclusivo do intervalo ISO-8601."),
        kind: str | None = Query(default=None, max_length=80),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0, le=100_000),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> TemporalDiffResponse:
        try:
            diff = repository.temporal_diff(from_time, to_time, kind=kind, limit=limit, offset=offset)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return TemporalDiffResponse(
            from_time=diff.from_time.isoformat(),
            to_time=diff.to_time.isoformat(),
            total=diff.total,
            new=diff.new,
            changed=diff.changed,
            absent=diff.absent,
            page=_page(diff.total, limit=limit, offset=offset),
            items=diff.items,
            meta=meta(request, repository),
        )

    @router.get("/v1/manifest", response_model=ManifestResponse, tags=["proveniencia"])
    def manifest(
        request: Request,
        repository: ApiRepository = Depends(repository_dependency),
    ) -> ManifestResponse:
        sidecar = manifest_path_for(settings.database)
        if sidecar.exists():
            current = load_manifest(sidecar)
            verification = verify_manifest(settings.database, current)
        else:
            current, report = build_snapshot_manifest(settings.database)
            if not report.ok:
                raise HTTPException(status_code=503, detail="O snapshot atual não atende ao contrato de dados.")
            verification = _verify_live(settings.database, current)
        return ManifestResponse(manifest=current, verification=verification, meta=meta(request, repository))

    @router.get("/v1/feed/changes.atom", tags=["historico"], response_class=FastAPIResponse)
    def changes_atom(
        request: Request,
        limit: int = Query(default=50, ge=1, le=200),
        repository: ApiRepository = Depends(repository_dependency),
    ) -> Response:
        items, _ = repository.changes(limit=limit, offset=0)
        feed = Element("feed", {"xmlns": "http://www.w3.org/2005/Atom"})
        SubElement(feed, "title").text = "Suzano Aberta — mudanças observadas"
        SubElement(feed, "id").text = "https://mukasanches.github.io/suzano-aberta/feeds/changes"
        SubElement(feed, "updated").text = (
            items[0].observed_at.isoformat() if items else datetime.now(UTC).isoformat()
        )
        for item in items:
            entry = SubElement(feed, "entry")
            SubElement(entry, "id").text = f"urn:suzano-aberta:change:{item.record_id}:{item.observed_at.isoformat()}"
            SubElement(entry, "title").text = f"{item.change_type}: {item.record_id}"
            SubElement(entry, "updated").text = item.observed_at.isoformat()
            link = SubElement(entry, "link")
            link.set("href", str(request.base_url).rstrip("/") + f"/v1/records/{item.record_id}")
            SubElement(entry, "summary").text = f"Mudança observada no conjunto {item.kind}."
        return FastAPIResponse(
            content=tostring(feed, encoding="utf-8", xml_declaration=True),
            media_type="application/atom+xml",
            headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=300"},
        )

    app.include_router(router)


def _verify_live(database: str | Path, manifest: SnapshotManifest) -> ManifestVerification:
    return verify_manifest(database, manifest)

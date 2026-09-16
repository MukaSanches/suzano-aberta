from __future__ import annotations

from fastapi import FastAPI

from .app import API_VERSION, SCHEMA_VERSION, create_app as _create_base_app
from .autopilot import install_autopilot_routes
from .civic import install_civic_routes
from .settings import ApiSettings
from .transit import install_transit_routes


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    resolved = settings or ApiSettings.from_env()
    application = _create_base_app(resolved)
    install_autopilot_routes(application, resolved)
    install_civic_routes(
        application,
        resolved,
        api_version=API_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    install_transit_routes(application, resolved)
    return application


app = create_app()

__all__ = ["API_VERSION", "ApiSettings", "app", "create_app"]

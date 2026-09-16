from __future__ import annotations

from fastapi import FastAPI

from ..autopilot import AutoUpdatePolicy, AutonomousDataManager
from .schemas import AutopilotResponse
from .settings import ApiSettings


def install_autopilot_routes(app: FastAPI, settings: ApiSettings) -> None:
    interval = settings.sync_interval_seconds if settings.sync_interval_seconds > 0 else 900
    manager = AutonomousDataManager(
        settings.database,
        policy=AutoUpdatePolicy(check_interval_seconds=interval),
    )
    app.state.autonomous_data_manager = manager

    @app.get("/v1/autopilot", response_model=AutopilotResponse, tags=["sistema"])
    def autopilot_status() -> AutopilotResponse:
        """Estado somente leitura da atualização automática do dataset local."""
        return AutopilotResponse.model_validate(manager.status().to_dict())

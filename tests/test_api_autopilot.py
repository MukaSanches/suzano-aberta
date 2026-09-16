from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from suzano_aberta.api import create_app
from suzano_aberta.api.settings import ApiSettings


def test_api_exposes_read_only_autopilot_status(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite3"
    app = create_app(
        ApiSettings(
            database=database,
            auto_sync=False,
            sync_interval_seconds=0,
        )
    )

    with TestClient(app) as client:
        response = client.get("/v1/autopilot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["database"] == str(database)
    assert payload["database_exists"] is False
    assert payload["records"] == 0
    assert payload["due"] is True
    assert payload["fresh"] is False
    assert "/v1/autopilot" in app.openapi()["paths"]

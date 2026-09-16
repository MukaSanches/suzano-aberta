from __future__ import annotations

from .autopilot_cli import auto_app
from .cli import app

app.add_typer(auto_app, name="auto")

__all__ = ["app"]

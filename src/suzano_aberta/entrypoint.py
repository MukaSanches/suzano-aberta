from __future__ import annotations

from .autopilot_cli import auto_app
from .civic_cli import app as data_app
from .cli import app

app.add_typer(auto_app, name="auto")
app.add_typer(data_app, name="data")

__all__ = ["app"]

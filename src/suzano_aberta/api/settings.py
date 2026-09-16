from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on", "sim"}


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, parsed)


def _env_csv(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class ApiSettings:
    database: Path = Path("suzano-aberta.sqlite3")
    auto_sync: bool = True
    sync_interval_seconds: int = 900
    cors_origins: tuple[str, ...] = ()
    allowed_hosts: tuple[str, ...] = ("*",)
    metrics_enabled: bool = True

    @classmethod
    def from_env(cls) -> "ApiSettings":
        return cls(
            database=Path(os.getenv("SUZANO_API_DATABASE", "suzano-aberta.sqlite3")),
            auto_sync=_env_bool("SUZANO_API_AUTO_SYNC", True),
            sync_interval_seconds=_env_int("SUZANO_API_SYNC_INTERVAL_SECONDS", 900),
            cors_origins=_env_csv("SUZANO_API_CORS_ORIGINS"),
            allowed_hosts=_env_csv("SUZANO_API_ALLOWED_HOSTS", ("*",)),
            metrics_enabled=_env_bool("SUZANO_API_METRICS", True),
        )

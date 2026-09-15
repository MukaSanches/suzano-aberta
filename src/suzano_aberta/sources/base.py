from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..http import PoliteHttpClient
from ..models import PublicRecord


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    key: str
    name: str
    url: str
    authority: str
    category: str
    notes: str


class SourceAdapter(Protocol):
    definition: SourceDefinition

    def collect(self, *, year: int) -> list[PublicRecord]: ...


class BaseSource:
    definition: SourceDefinition

    def __init__(self, http: PoliteHttpClient) -> None:
        self.http = http

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from typing import Any, cast

from ..http import PoliteHttpClient
from .base import BaseSource, SourceDefinition


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    definition: SourceDefinition
    adapter: type[BaseSource]
    origin: str = "builtin"


class SourceRegistry:
    """Registro de adaptadores com suporte a plugins Python externos.

    Plugins podem publicar um entry point no grupo ``suzano_aberta.sources`` que
    resolva para uma subclasse de BaseSource. Isso permite ampliar a cobertura
    sem alterar o núcleo do projeto.
    """

    def __init__(self) -> None:
        self._items: dict[str, SourceRegistration] = {}

    def register(self, adapter: type[BaseSource], *, origin: str = "builtin") -> None:
        definition = adapter.definition
        if definition.key in self._items:
            raise ValueError(f"Fonte já registrada: {definition.key}")
        self._items[definition.key] = SourceRegistration(
            definition=definition,
            adapter=adapter,
            origin=origin,
        )

    def get(self, key: str) -> SourceRegistration:
        try:
            return self._items[key]
        except KeyError as exc:
            raise KeyError(f"Fonte desconhecida: {key}") from exc

    def create(self, key: str, http: PoliteHttpClient) -> BaseSource:
        return self.get(key).adapter(http)

    def registrations(self) -> tuple[SourceRegistration, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.definition.key))

    def load_entry_points(self) -> list[str]:
        loaded: list[str] = []
        entry_points = importlib.metadata.entry_points()
        selected = entry_points.select(group="suzano_aberta.sources")
        for entry_point in selected:
            candidate: Any = entry_point.load()
            if not isinstance(candidate, type) or not issubclass(candidate, BaseSource):
                raise TypeError(
                    f"Plugin {entry_point.name!r} precisa exportar uma subclasse de BaseSource"
                )
            adapter = cast(type[BaseSource], candidate)
            self.register(adapter, origin=f"entrypoint:{entry_point.name}")
            loaded.append(adapter.definition.key)
        return loaded


def default_source_registry(*, include_plugins: bool = True) -> SourceRegistry:
    from .camara_v2 import EnhancedCamaraSource
    from .comprasgov import ComprasGovSource
    from .legislacao import LegislacaoSource
    from .pncp import PncpSource
    from .prefeitura_v2 import EnhancedPrefeituraSource

    registry = SourceRegistry()
    for adapter in (
        EnhancedCamaraSource,
        EnhancedPrefeituraSource,
        PncpSource,
        ComprasGovSource,
        LegislacaoSource,
    ):
        registry.register(adapter)
    if include_plugins:
        registry.load_entry_points()
    return registry

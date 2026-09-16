from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from typing import Any

from ..http import PoliteHttpClient
from .base import BaseSource, SourceDefinition


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    definition: SourceDefinition
    adapter: type[Any]
    origin: str = "builtin"


class SourceRegistry:
    """Registro de adaptadores com suporte a plugins Python externos.

    O núcleo possui alguns adaptadores históricos que não compartilham a mesma
    classe-base, mas todos recebem um cliente HTTP no construtor. Para plugins
    externos mantemos um contrato mais rígido: subclasses de BaseSource com
    ``definition`` explícita.
    """

    def __init__(self) -> None:
        self._items: dict[str, SourceRegistration] = {}

    def register(
        self,
        adapter: type[Any],
        *,
        definition: SourceDefinition | None = None,
        origin: str = "builtin",
    ) -> None:
        resolved = definition or getattr(adapter, "definition", None)
        if not isinstance(resolved, SourceDefinition):
            raise TypeError("O adaptador precisa declarar SourceDefinition ou recebê-la no registro")
        if resolved.key in self._items:
            raise ValueError(f"Fonte já registrada: {resolved.key}")
        self._items[resolved.key] = SourceRegistration(
            definition=resolved,
            adapter=adapter,
            origin=origin,
        )

    def get(self, key: str) -> SourceRegistration:
        try:
            return self._items[key]
        except KeyError as exc:
            raise KeyError(f"Fonte desconhecida: {key}") from exc

    def create(self, key: str, http: PoliteHttpClient) -> Any:
        return self.get(key).adapter(http)

    def registrations(self) -> tuple[SourceRegistration, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.definition.key))

    def load_entry_points(self) -> list[str]:
        loaded: list[str] = []
        entry_points = importlib.metadata.entry_points()
        selected = entry_points.select(group="suzano_aberta.sources")
        for entry_point in selected:
            candidate = entry_point.load()
            if not isinstance(candidate, type) or not issubclass(candidate, BaseSource):
                raise TypeError(
                    f"Plugin {entry_point.name!r} precisa exportar uma subclasse de BaseSource"
                )
            self.register(candidate, origin=f"entrypoint:{entry_point.name}")
            loaded.append(candidate.definition.key)
        return loaded


def default_source_registry(*, include_plugins: bool = True) -> SourceRegistry:
    from .camara_v2 import EnhancedCamaraSource
    from .comprasgov import COMPRAS_DADOS, ComprasGovSource
    from .legislacao import LegislacaoSource
    from .pncp import PNCP_PORTAL, PncpSource
    from .prefeitura_v2 import EnhancedPrefeituraSource

    registry = SourceRegistry()
    registry.register(EnhancedCamaraSource)
    registry.register(EnhancedPrefeituraSource)
    registry.register(
        PncpSource,
        definition=SourceDefinition(
            key="pncp",
            name="Portal Nacional de Contratações Públicas (PNCP)",
            url=PNCP_PORTAL,
            authority="Governo federal",
            category="contratacoes",
            notes="Contratações, contratos e atas publicadas no PNCP para o Município de Suzano.",
        ),
    )
    registry.register(
        ComprasGovSource,
        definition=SourceDefinition(
            key="comprasgov",
            name="Compras.gov.br Dados Abertos",
            url=COMPRAS_DADOS,
            authority="Governo federal",
            category="contratacoes",
            notes="Dados estruturados de contratações públicas filtrados para Suzano.",
        ),
    )
    registry.register(LegislacaoSource)
    if include_plugins:
        registry.load_entry_points()
    return registry

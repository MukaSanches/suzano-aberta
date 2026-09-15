from __future__ import annotations

import json
from hashlib import sha256
from typing import Any
from urllib.parse import urlencode

from ..models import PublicRecord, SourceRef
from .pncp import SUZANO_CNPJ, _date, _first, _money

COMPRAS_DADOS = "https://dadosabertos.compras.gov.br"
CONTRATACOES_PATH = "/modulo-contratacoes/1_consultarContratacoes_PNCP_14133"


class ComprasGovSource:
    """Dados Abertos do Compras.gov.br filtrados pelo CNPJ do Município de Suzano."""

    def __init__(self, http: Any) -> None:
        self.http = http

    def _get_json(self, url: str) -> Any:
        return json.loads(self.http.get(url, attempts=3).text)

    @staticmethod
    def _items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("resultado", "resultados", "data", "items", "content"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    def procurements(self, *, year: int) -> list[PublicRecord]:
        records: dict[str, PublicRecord] = {}
        max_pages = 80
        for page in range(1, max_pages + 1):
            params = {
                "orgaoEntidadeCnpj": SUZANO_CNPJ,
                "dataPublicacaoPncpInicial": f"{year}-01-01",
                "dataPublicacaoPncpFinal": f"{year}-12-31",
                "pagina": page,
                "tamanhoPagina": 250,
            }
            url = f"{COMPRAS_DADOS}{CONTRATACOES_PATH}?{urlencode(params)}"
            payload = self._get_json(url)
            items = self._items(payload)
            if not items:
                break
            for row in items:
                record = self._record(row, year)
                if record is not None:
                    records[record.id] = record
            if isinstance(payload, dict):
                total_pages = _first(payload, "totalPaginas", "total_pages", "paginas", default=None)
                try:
                    if total_pages is not None and page >= int(total_pages):
                        break
                except (TypeError, ValueError):
                    pass
                if len(items) < 250:
                    break
        return sorted(records.values(), key=lambda item: (item.date or "", item.id), reverse=True)

    def _record(self, row: dict[str, Any], year: int) -> PublicRecord | None:
        control = str(_first(row, "numeroControlePNCP", "numero_controle_pncp", default="")).strip()
        purchase_id = _first(row, "idCompra", "id_compra", "id", default=None)
        ano = int(_first(row, "anoCompra", "ano_compra", default=year) or year)
        seq = _first(row, "sequencialCompra", "sequencial_compra", default=None)
        number = _first(row, "numeroCompra", "numero_compra", "numero", default=None)
        if not control and purchase_id is None and number is None:
            return None

        obj = _first(row, "objetoCompra", "objeto_compra", "objeto", default=None)
        modality = _first(row, "modalidadeNome", "modalidade_nome", "modalidade", default=None)
        status = _first(row, "situacaoCompraNome", "situacao_compra_nome", "situacao", default=None)
        stable = control or str(purchase_id or f"{ano}-{seq or number}")
        portal_url = (
            f"https://pncp.gov.br/app/editais/{SUZANO_CNPJ}/{ano}/{seq}"
            if seq is not None
            else "https://dadosabertos.compras.gov.br/"
        )
        attrs = {
            "identifier": control or str(number or purchase_id),
            "numero_controle_pncp": control or None,
            "id_compra": purchase_id,
            "numero": number,
            "processo": _first(row, "processo", "numeroProcesso", "numero_processo", default=None),
            "modalidade": modality,
            "situacao": status,
            "modo_disputa": _first(row, "modoDisputaNome", "modo_disputa_nome", default=None),
            "objeto": obj,
            "valor_estimado": _money(_first(row, "valorTotalEstimado", "valor_total_estimado", default=None)),
            "valor_homologado": _money(_first(row, "valorTotalHomologado", "valor_total_homologado", default=None)),
            "data_abertura_proposta": _date(_first(row, "dataAberturaProposta", "data_abertura_proposta", default=None)),
            "data_encerramento_proposta": _date(_first(row, "dataEncerramentoProposta", "data_encerramento_proposta", default=None)),
            "uasg": _first(row, "unidadeOrgaoCodigoUnidade", "codigoUnidade", "uasg", default=None),
            "orgao": _first(row, "orgaoEntidadeRazaoSocial", "orgaoEntidade", "orgao", default=None),
            "unidade": _first(row, "unidadeOrgaoNomeUnidade", "unidadeOrgao", "unidade", default=None),
            "fonte_api": "Compras.gov.br Dados Abertos",
            "api_url": f"{COMPRAS_DADOS}{CONTRATACOES_PATH}",
            "portal_url": portal_url,
        }
        title = f"{modality or 'Contratação'} {number or control or purchase_id}"
        return PublicRecord(
            id=f"comprasgov:licitacao:{sha256(stable.encode()).hexdigest()[:20]}",
            kind="licitacao",
            title=title[:500],
            summary=str(obj)[:4000] if obj else None,
            date=_date(_first(row, "dataPublicacaoPncp", "data_publicacao_pncp", default=None)),
            year=ano,
            attributes=attrs,
            source=SourceRef(name="Compras.gov.br — Dados Abertos", url=portal_url),
        )

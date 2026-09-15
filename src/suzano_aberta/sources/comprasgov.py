from __future__ import annotations

import json
from collections import defaultdict
from hashlib import sha256
from typing import Any
from urllib.parse import urlencode

from ..models import PublicRecord, SourceRef
from .pncp import SUZANO_CNPJ, _date, _first, _money

COMPRAS_DADOS = "https://dadosabertos.compras.gov.br"
CONTRATACOES_PATH = "/modulo-contratacoes/1_consultarContratacoes_PNCP_14133"
RESULTADOS_PATH = "/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133"
UASG_PATH = "/modulo-uasg/1_consultarUasg"
CONTRATOS_PATH = "/modulo-contratos/1_consultarContratos"
ARP_PATH = "/modulo-arp/1_consultarARP"

# Códigos publicados no Manual da API Compras.gov.br v2.0 (01/2026).
COMPRAS_MODALITY_CODES = (1, 2, 3, 4, 5, 6, 7, 12, 20, 22, 33, 44, 57)


class ComprasGovSource:
    """Dados Abertos do Compras.gov.br relacionados ao Município de Suzano."""

    def __init__(self, http: Any) -> None:
        self.http = http
        self._units_cache: list[dict[str, Any]] | None = None
        self._award_cache: dict[int, dict[str, dict[str, Any]]] = {}

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

    def _pages(
        self,
        path: str,
        params: dict[str, Any],
        *,
        max_pages: int = 120,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            query = urlencode({**params, "pagina": page, "tamanhoPagina": page_size})
            payload = self._get_json(f"{COMPRAS_DADOS}{path}?{query}")
            items = self._items(payload)
            if not items:
                break
            records.extend(items)
            if isinstance(payload, dict):
                remaining = payload.get("paginasRestantes")
                total_pages = _first(payload, "totalPaginas", "total_pages", "paginas", default=None)
                if remaining in (0, "0"):
                    break
                try:
                    if total_pages is not None and page >= int(total_pages):
                        break
                except (TypeError, ValueError):
                    pass
            if len(items) < page_size:
                break
        return records

    def units(self) -> list[dict[str, Any]]:
        """Resolve UASGs ligadas ao CNPJ municipal para filtros que não aceitam CNPJ."""
        if self._units_cache is not None:
            return self._units_cache
        rows = self._pages(
            UASG_PATH,
            {"cnpjCpfOrgao": SUZANO_CNPJ, "statusUasg": "true"},
            max_pages=10,
        )
        unique: dict[str, dict[str, Any]] = {}
        for row in rows:
            code = str(_first(row, "codigoUasg", "codigoUASG", "codigoUnidade", default="")).strip()
            if code:
                unique[code] = row
        self._units_cache = list(unique.values())
        return self._units_cache

    def award_summaries(self, *, year: int) -> dict[str, dict[str, Any]]:
        """Resume resultados homologados por idCompra, removendo duplicatas da paginação."""
        if year in self._award_cache:
            return self._award_cache[year]
        try:
            rows = self._pages(
                RESULTADOS_PATH,
                {
                    "orgaoEntidadeCnpj": SUZANO_CNPJ,
                    "dataResultadoPncpInicial": f"{year}-01-01",
                    "dataResultadoPncpFinal": f"{year}-12-31",
                },
            )
        except Exception:
            self._award_cache[year] = {}
            return {}

        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"suppliers": {}, "rows": {}, "value": 0.0}
        )
        for row in rows:
            purchase_id = str(_first(row, "idCompra", default="")).strip()
            if not purchase_id:
                continue
            item_id = str(_first(row, "idCompraItem", default="")).strip()
            seq = str(_first(row, "sequencialResultado", default="")).strip()
            supplier_id = str(_first(row, "niFornecedor", default="")).strip()
            supplier_name = str(_first(row, "nomeRazaoSocialFornecedor", default="")).strip()
            value = _money(_first(row, "valorTotalHomologado", default=None)) or 0.0
            row_key = f"{item_id}:{seq}:{supplier_id}:{value}"
            if row_key in grouped[purchase_id]["rows"]:
                continue
            grouped[purchase_id]["rows"][row_key] = True
            if supplier_id or supplier_name:
                grouped[purchase_id]["suppliers"][supplier_id or supplier_name] = supplier_name or supplier_id
            grouped[purchase_id]["value"] += value

        result: dict[str, dict[str, Any]] = {}
        for purchase_id, bucket in grouped.items():
            suppliers = [
                {"documento": key, "nome": name}
                for key, name in sorted(bucket["suppliers"].items())
            ]
            result[purchase_id] = {
                "resultados_itens": len(bucket["rows"]),
                "fornecedores_homologados": suppliers,
                "resultados_valor_total_homologado": round(float(bucket["value"]), 2),
            }
        self._award_cache[year] = result
        return result

    def procurements(self, *, year: int) -> list[PublicRecord]:
        records: dict[str, PublicRecord] = {}
        errors: list[Exception] = []
        awards = self.award_summaries(year=year)
        for modality in COMPRAS_MODALITY_CODES:
            try:
                rows = self._pages(
                    CONTRATACOES_PATH,
                    {
                        "orgaoEntidadeCnpj": SUZANO_CNPJ,
                        "dataPublicacaoPncpInicial": f"{year}-01-01",
                        "dataPublicacaoPncpFinal": f"{year}-12-31",
                        "codigoModalidade": modality,
                    },
                )
            except Exception as exc:
                errors.append(exc)
                continue
            for row in rows:
                record = self._procurement_record(row, year, awards)
                if record is not None:
                    records[record.id] = record
        if not records and errors:
            raise errors[0]
        return sorted(records.values(), key=lambda item: (item.date or "", item.id), reverse=True)

    def contracts(self, *, year: int) -> list[PublicRecord]:
        records: dict[str, PublicRecord] = {}
        units = self.units()
        for unit in units:
            code = _first(unit, "codigoUasg", "codigoUASG", "codigoUnidade", default=None)
            if code in (None, ""):
                continue
            for field in ("codigoUnidadeGestora", "codigoUnidadeGestoraOrigemContrato"):
                try:
                    rows = self._pages(
                        CONTRATOS_PATH,
                        {
                            field: code,
                            "dataVigenciaInicialMin": f"{year}-01-01",
                            "dataVigenciaInicialMax": f"{year}-12-31",
                        },
                    )
                except Exception:
                    continue
                for row in rows:
                    record = self._contract_record(row, year)
                    if record is not None:
                        records[record.id] = record
        return sorted(records.values(), key=lambda item: (item.date or "", item.id), reverse=True)

    def atas(self, *, year: int) -> list[PublicRecord]:
        records: dict[str, PublicRecord] = {}
        for unit in self.units():
            code = _first(unit, "codigoUasg", "codigoUASG", "codigoUnidade", default=None)
            if code in (None, ""):
                continue
            try:
                rows = self._pages(
                    ARP_PATH,
                    {
                        "codigoUnidadeGerenciadora": code,
                        "dataVigenciaInicialMin": f"{year}-01-01",
                        "dataVigenciaInicialMax": f"{year}-12-31",
                    },
                )
            except Exception:
                continue
            for row in rows:
                record = self._ata_record(row, year)
                if record is not None:
                    records[record.id] = record
        return sorted(records.values(), key=lambda item: (item.date or "", item.id), reverse=True)

    def _procurement_record(
        self,
        row: dict[str, Any],
        year: int,
        awards: dict[str, dict[str, Any]],
    ) -> PublicRecord | None:
        control = str(_first(row, "numeroControlePNCP", "numero_controle_pncp", default="")).strip()
        purchase_id = _first(row, "idCompra", "id_compra", "id", default=None)
        ano = int(_first(row, "anoCompraPncp", "anoCompra", "ano_compra", default=year) or year)
        seq = _first(row, "sequencialCompraPncp", "sequencialCompra", "sequencial_compra", default=None)
        number = _first(row, "numeroCompra", "numero_compra", "numero", default=None)
        if not control and purchase_id is None and number is None:
            return None

        obj = _first(row, "objetoCompra", "objeto_compra", "objeto", default=None)
        modality = _first(row, "modalidadeNome", "modalidade_nome", "modalidade", default=None)
        status = _first(
            row,
            "situacaoCompraNomePncp",
            "situacaoCompraNome",
            "situacao_compra_nome",
            "situacao",
            default=None,
        )
        stable = control or str(purchase_id or f"{ano}-{seq or number}")
        portal_url = (
            f"https://pncp.gov.br/app/editais/{SUZANO_CNPJ}/{ano}/{seq}"
            if seq is not None
            else "https://dadosabertos.compras.gov.br/"
        )
        attrs: dict[str, Any] = {
            "identifier": control or str(number or purchase_id),
            "numero_controle_pncp": control or None,
            "id_compra": purchase_id,
            "numero": number,
            "processo": _first(row, "processo", "numeroProcesso", "numero_processo", default=None),
            "modalidade": modality,
            "situacao": status,
            "modo_disputa": _first(row, "modoDisputaNomePncp", "modoDisputaNome", "modo_disputa_nome", default=None),
            "objeto": obj,
            "valor_estimado": _money(_first(row, "valorTotalEstimado", "valor_total_estimado", default=None)),
            "valor_homologado": _money(_first(row, "valorTotalHomologado", "valor_total_homologado", default=None)),
            "data_abertura_proposta": _date(_first(row, "dataAberturaPropostaPncp", "dataAberturaProposta", "data_abertura_proposta", default=None)),
            "data_encerramento_proposta": _date(_first(row, "dataEncerramentoPropostaPncp", "dataEncerramentoProposta", "data_encerramento_proposta", default=None)),
            "uasg": _first(row, "unidadeOrgaoCodigoUnidade", "codigoUnidade", "uasg", default=None),
            "orgao": _first(row, "orgaoEntidadeRazaoSocial", "orgaoEntidade", "orgao", default=None),
            "unidade": _first(row, "unidadeOrgaoNomeUnidade", "unidadeOrgao", "unidade", default=None),
            "srp": _first(row, "srp", default=None),
            "amparo_legal": _first(row, "amparoLegalNome", "amparoLegalDescricao", default=None),
            "fonte_api": "Compras.gov.br Dados Abertos",
            "api_url": f"{COMPRAS_DADOS}{CONTRATACOES_PATH}",
            "portal_url": portal_url,
        }
        if purchase_id is not None:
            attrs.update(awards.get(str(purchase_id), {}))
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

    def _contract_record(self, row: dict[str, Any], year: int) -> PublicRecord | None:
        control = str(_first(row, "numeroControlePncpContrato", "numeroControlePNCPContrato", default="")).strip()
        number = _first(row, "numeroContrato", default=None)
        unit = _first(row, "codigoUnidadeGestora", default=None)
        process = _first(row, "processo", default=None)
        if not control and not number:
            return None
        stable = control or f"{unit}:{number}:{process or year}"
        obj = _first(row, "objeto", default=None)
        supplier = _first(row, "nomeRazaoSocialFornecedor", default=None)
        source_url = "https://dadosabertos.compras.gov.br/"
        attrs = {
            "identifier": control or str(number),
            "numero_controle_pncp": control or None,
            "id_compra": _first(row, "idCompra", default=None),
            "numero": number,
            "processo": process,
            "modalidade": _first(row, "nomeModalidadeCompra", default=None),
            "categoria": _first(row, "nomeCategoria", default=None),
            "tipo_contrato": _first(row, "nomeTipo", default=None),
            "objeto": obj,
            "contractor": supplier,
            "contratada": supplier,
            "cnpj_fornecedor": _first(row, "niFornecedor", default=None),
            "valor": _money(_first(row, "valorGlobal", default=None)),
            "valor_global": _money(_first(row, "valorGlobal", default=None)),
            "valor_acumulado": _money(_first(row, "valorAcumulado", default=None)),
            "vigencia_inicio": _date(_first(row, "dataVigenciaInicial", default=None)),
            "vigencia_fim": _date(_first(row, "dataVigenciaFinal", default=None)),
            "uasg": unit,
            "unidade": _first(row, "nomeUnidadeGestora", default=None),
            "orgao": _first(row, "nomeOrgao", default=None),
            "fonte_api": "Compras.gov.br Dados Abertos — Contratos",
            "api_url": f"{COMPRAS_DADOS}{CONTRATOS_PATH}",
            "portal_url": source_url,
        }
        return PublicRecord(
            id=f"comprasgov:contrato:{sha256(stable.encode()).hexdigest()[:20]}",
            kind="contrato",
            title=f"Contrato {number or control}"[:500],
            summary=str(obj)[:4000] if obj else None,
            date=_date(_first(row, "dataHoraInclusao", "dataVigenciaInicial", default=None)),
            year=year,
            attributes=attrs,
            source=SourceRef(name="Compras.gov.br — Contratos", url=source_url),
        )

    def _ata_record(self, row: dict[str, Any], year: int) -> PublicRecord | None:
        control = str(_first(row, "numeroControlePncpAta", "numeroControlePNCPAta", default="")).strip()
        number = _first(row, "numeroAtaRegistroPreco", default=None)
        unit = _first(row, "codigoUnidadeGerenciadora", default=None)
        if not control and not number:
            return None
        stable = control or f"{unit}:{number}:{year}"
        obj = _first(row, "objeto", default=None)
        source_url = str(_first(row, "linkAtaPNCP", default="https://dadosabertos.compras.gov.br/"))
        attrs = {
            "identifier": control or str(number),
            "numero_controle_pncp": control or None,
            "numero_controle_pncp_compra": _first(row, "numeroControlePncpCompra", default=None),
            "id_compra": _first(row, "idCompra", default=None),
            "numero": number,
            "modalidade": _first(row, "nomeModalidadeCompra", default=None),
            "situacao": _first(row, "statusAta", default=None),
            "objeto": obj,
            "valor": _money(_first(row, "valorTotal", default=None)),
            "valor_global": _money(_first(row, "valorTotal", default=None)),
            "quantidade_itens": _first(row, "quantidadeItens", default=None),
            "vigencia_inicio": _date(_first(row, "dataVigenciaInicial", default=None)),
            "vigencia_fim": _date(_first(row, "dataVigenciaFinal", default=None)),
            "data_assinatura": _date(_first(row, "dataAssinatura", default=None)),
            "uasg": unit,
            "unidade": _first(row, "nomeUnidadeGerenciadora", default=None),
            "orgao": _first(row, "nomeOrgao", default=None),
            "link_compra_pncp": _first(row, "linkCompraPNCP", default=None),
            "fonte_api": "Compras.gov.br Dados Abertos — ARP",
            "api_url": f"{COMPRAS_DADOS}{ARP_PATH}",
            "portal_url": source_url,
        }
        return PublicRecord(
            id=f"comprasgov:ata:{sha256(stable.encode()).hexdigest()[:20]}",
            kind="ata",
            title=f"Ata de registro de preços {number or control}"[:500],
            summary=str(obj)[:4000] if obj else None,
            date=_date(_first(row, "dataAssinatura", "dataHoraInclusao", default=None)),
            year=year,
            attributes=attrs,
            source=SourceRef(name="Compras.gov.br — Atas de Registro de Preços", url=source_url),
        )

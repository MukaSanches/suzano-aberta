from __future__ import annotations

import json
from hashlib import sha256
from typing import Any
from urllib.parse import urlencode

from ..models import PublicRecord, SourceRef

PNCP_CONSULTA = "https://pncp.gov.br/api/consulta/v1"
PNCP_API = "https://pncp.gov.br/api/pncp/v1"
PNCP_PORTAL = "https://pncp.gov.br/app"
SUZANO_CNPJ = "46523056000121"
# Tabela de modalidades do PNCP. Consultamos uma faixa defensiva e ignoramos códigos
# que o serviço não reconhecer, preservando resultados das demais modalidades.
MODALITY_CODES = tuple(range(1, 16))


def _first(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
    if len(raw) >= 8 and raw[:8].isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw[:10] if raw else None


def _money(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PncpSource:
    """Consultas públicas do Portal Nacional de Contratações Públicas para Suzano."""

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
        for key in ("data", "items", "content", "resultados", "resultado"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    def _pages(self, path: str, params: dict[str, Any], *, max_pages: int = 80) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            query = urlencode({**params, "pagina": page})
            payload = self._get_json(f"{PNCP_CONSULTA}/{path}?{query}")
            items = self._items(payload)
            if not items:
                break
            records.extend(items)
            if isinstance(payload, dict):
                remaining = payload.get("paginasRestantes")
                total = payload.get("totalPaginas") or payload.get("totalPages")
                if remaining in (0, "0"):
                    break
                try:
                    if total is not None and page >= int(total):
                        break
                except (TypeError, ValueError):
                    pass
        return records

    def procurements(self, *, year: int) -> list[PublicRecord]:
        rows: list[dict[str, Any]] = []
        errors: list[Exception] = []
        for modality in MODALITY_CODES:
            try:
                rows.extend(
                    self._pages(
                        "contratacoes/publicacao",
                        {
                            "dataInicial": f"{year}0101",
                            "dataFinal": f"{year}1231",
                            "codigoModalidadeContratacao": modality,
                            "cnpj": SUZANO_CNPJ,
                        },
                    )
                )
            except Exception as exc:
                errors.append(exc)
        if not rows and errors:
            raise errors[0]

        unique: dict[str, PublicRecord] = {}
        for row in rows:
            record = self._procurement_record(row, year)
            if record is not None:
                unique[record.id] = record
        return sorted(unique.values(), key=lambda item: (item.date or "", item.id), reverse=True)

    def contracts(self, *, year: int) -> list[PublicRecord]:
        rows = self._pages(
            "contratos",
            {
                "dataInicial": f"{year}0101",
                "dataFinal": f"{year}1231",
                "cnpjOrgao": SUZANO_CNPJ,
            },
        )
        unique: dict[str, PublicRecord] = {}
        for row in rows:
            record = self._contract_record(row, year)
            if record is not None:
                unique[record.id] = record
        return sorted(unique.values(), key=lambda item: (item.date or "", item.id), reverse=True)

    def atas(self, *, year: int) -> list[PublicRecord]:
        rows = self._pages(
            "atas",
            {
                "dataInicial": f"{year}0101",
                "dataFinal": f"{year}1231",
                "cnpj": SUZANO_CNPJ,
            },
        )
        unique: dict[str, PublicRecord] = {}
        for row in rows:
            record = self._ata_record(row, year)
            if record is not None:
                unique[record.id] = record
        return sorted(unique.values(), key=lambda item: (item.date or "", item.id), reverse=True)

    def _procurement_record(self, row: dict[str, Any], year: int) -> PublicRecord | None:
        control = str(_first(row, "numeroControlePNCP", "numero_controle_pncp", default="")).strip()
        ano = int(_first(row, "anoCompra", "ano", default=year) or year)
        seq = _first(row, "sequencialCompra", "sequencial", default=None)
        number = _first(row, "numeroCompra", "numeroContratacao", "numero", default=None)
        process = _first(row, "processo", "numeroProcesso", default=None)
        obj = _first(row, "objetoCompra", "objeto", "informacaoComplementar", default=None)
        modality = _first(row, "modalidadeNome", "modalidadeContratacaoNome", default=None)
        status = _first(row, "situacaoCompraNome", "situacaoNome", default=None)
        published = _date(_first(row, "dataPublicacaoPncp", "dataPublicacaoPNCP", "dataInclusao", default=None))
        if not control and seq is None and not number:
            return None
        stable = control or f"{SUZANO_CNPJ}-{ano}-{seq or number}"
        api_url = f"{PNCP_API}/orgaos/{SUZANO_CNPJ}/compras/{ano}/{seq}" if seq is not None else ""
        portal_url = f"{PNCP_PORTAL}/editais/{SUZANO_CNPJ}/{ano}/{seq}" if seq is not None else "https://pncp.gov.br/"
        title_number = number or control or f"{ano}/{seq}"
        title = f"{modality or 'Contratação'} {title_number}"
        attrs = {
            "identifier": control or str(title_number),
            "numero_controle_pncp": control or None,
            "numero": number,
            "processo": process,
            "modalidade": modality,
            "situacao": status,
            "modo_disputa": _first(row, "modoDisputaNome", default=None),
            "objeto": obj,
            "valor_estimado": _money(_first(row, "valorTotalEstimado", "valorEstimado", default=None)),
            "valor_homologado": _money(_first(row, "valorTotalHomologado", "valorHomologado", default=None)),
            "data_abertura_proposta": _date(_first(row, "dataAberturaProposta", default=None)),
            "data_encerramento_proposta": _date(_first(row, "dataEncerramentoProposta", default=None)),
            "amparo_legal": _first(row, "amparoLegal", default=None),
            "srp": _first(row, "srp", default=None),
            "orgao": _first(row, "orgaoEntidade", "orgao", default=None),
            "unidade": _first(row, "unidadeOrgao", "unidade", default=None),
            "link_sistema_origem": _first(row, "linkSistemaOrigem", default=None),
            "api_url": api_url or None,
            "portal_url": portal_url,
            "fonte_api": "PNCP",
        }
        return PublicRecord(
            id=f"pncp:licitacao:{sha256(stable.encode()).hexdigest()[:20]}",
            kind="licitacao",
            title=title[:500],
            summary=str(obj)[:4000] if obj else None,
            date=published,
            year=ano,
            attributes=attrs,
            source=SourceRef(name="Portal Nacional de Contratações Públicas (PNCP)", url=portal_url),
        )

    def _contract_record(self, row: dict[str, Any], year: int) -> PublicRecord | None:
        control = str(_first(row, "numeroControlePNCP", "numero_controle_pncp", default="")).strip()
        purchase_control = str(_first(row, "numeroControlePNCPCompra", "numero_controle_pncp_compra", default="")).strip()
        ano = int(_first(row, "anoContrato", "ano", default=year) or year)
        seq = _first(row, "sequencialContrato", "sequencial", default=None)
        number = _first(row, "numeroContratoEmpenho", "numeroContrato", "numero", default=None)
        obj = _first(row, "objetoContrato", "objeto", default=None)
        supplier = _first(row, "nomeRazaoSocialFornecedor", "razaoSocialFornecedor", "fornecedor", default=None)
        supplier_id = _first(row, "niFornecedor", "cnpjFornecedor", default=None)
        if not control and seq is None and not number:
            return None
        stable = control or f"{SUZANO_CNPJ}-{ano}-{seq or number}"
        detail_url = f"{PNCP_API}/orgaos/{SUZANO_CNPJ}/contratos/{ano}/{seq}" if seq is not None else "https://pncp.gov.br/"
        title = f"Contrato {number or control or f'{ano}/{seq}'}"
        attrs = {
            "identifier": control or str(number or stable),
            "numero_controle_pncp": control or None,
            "numero_controle_pncp_compra": purchase_control or None,
            "numero": number,
            "processo": _first(row, "processo", "numeroProcesso", default=None),
            "tipo_contrato": _first(row, "tipoContratoNome", default=None),
            "categoria": _first(row, "categoriaProcessoNome", default=None),
            "objeto": obj,
            "contractor": supplier,
            "contratada": supplier,
            "cnpj_fornecedor": supplier_id,
            "valor": _money(_first(row, "valorInicial", "valorGlobal", default=None)),
            "valor_inicial": _money(_first(row, "valorInicial", default=None)),
            "valor_global": _money(_first(row, "valorGlobal", default=None)),
            "vigencia_inicio": _date(_first(row, "dataVigenciaInicio", "vigenciaInicio", default=None)),
            "vigencia_fim": _date(_first(row, "dataVigenciaFim", "vigenciaFim", default=None)),
            "api_url": detail_url,
            "fonte_api": "PNCP",
        }
        return PublicRecord(
            id=f"pncp:contrato:{sha256(stable.encode()).hexdigest()[:20]}",
            kind="contrato",
            title=title[:500],
            summary=str(obj)[:4000] if obj else None,
            date=_date(_first(row, "dataPublicacaoPncp", "dataAssinatura", default=None)),
            year=ano,
            attributes=attrs,
            source=SourceRef(name="Portal Nacional de Contratações Públicas (PNCP)", url=detail_url),
        )

    def _ata_record(self, row: dict[str, Any], year: int) -> PublicRecord | None:
        control = str(_first(row, "numeroControlePNCPAta", "numeroControlePNCP", default="")).strip()
        purchase_control = str(_first(row, "numeroControlePNCPCompra", default="")).strip()
        ano = int(_first(row, "anoAta", "ano", default=year) or year)
        seq = _first(row, "sequencialAta", "sequencial", default=None)
        number = _first(row, "numeroAtaRegistroPreco", "numeroAta", "numero", default=None)
        if not control and seq is None and not number:
            return None
        stable = control or f"{SUZANO_CNPJ}-{ano}-{seq or number}"
        title = f"Ata de registro de preços {number or control or f'{ano}/{seq}'}"
        attrs = {
            "identifier": control or str(number or stable),
            "numero_controle_pncp": control or None,
            "numero_controle_pncp_compra": purchase_control or None,
            "numero": number,
            "objeto": _first(row, "objetoContratacao", "objeto", default=None),
            "vigencia_inicio": _date(_first(row, "dataVigenciaInicio", default=None)),
            "vigencia_fim": _date(_first(row, "dataVigenciaFim", default=None)),
            "fonte_api": "PNCP",
        }
        return PublicRecord(
            id=f"pncp:ata:{sha256(stable.encode()).hexdigest()[:20]}",
            kind="ata",
            title=title[:500],
            summary=str(attrs["objeto"])[:4000] if attrs["objeto"] else None,
            date=_date(_first(row, "dataPublicacaoPncp", "dataAssinatura", default=None)),
            year=ano,
            attributes=attrs,
            source=SourceRef(name="Portal Nacional de Contratações Públicas (PNCP)", url="https://pncp.gov.br/"),
        )

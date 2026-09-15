from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

from suzano_aberta.sources.pncp import PncpSource


class Result:
    def __init__(self, payload: object) -> None:
        self.text = json.dumps(payload)


class FakeHttp:
    def get(self, url: str, *, attempts: int = 3) -> Result:
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        page = int(query.get("pagina", ["1"])[0])
        if page > 1:
            return Result({"data": [], "paginasRestantes": 0})
        if parts.path.endswith("/contratacoes/publicacao"):
            modality = int(query.get("codigoModalidadeContratacao", ["0"])[0])
            if modality != 8:
                return Result({"data": [], "paginasRestantes": 0})
            return Result({"data": [{
                "numeroControlePNCP": "46523056000121-1-000123/2026",
                "anoCompra": 2026,
                "sequencialCompra": 123,
                "numeroCompra": "063/2026",
                "processo": "12345/2026",
                "objetoCompra": "Aquisição de equipamentos",
                "modalidadeNome": "Dispensa",
                "situacaoCompraNome": "Divulgada no PNCP",
                "dataPublicacaoPncp": "2026-09-10T12:00:00",
                "valorTotalEstimado": 15000.5,
            }], "paginasRestantes": 0})
        if parts.path.endswith("/contratos"):
            return Result({"data": [{
                "numeroControlePNCP": "46523056000121-2-000010/2026",
                "numeroControlePNCPCompra": "46523056000121-1-000123/2026",
                "anoContrato": 2026,
                "sequencialContrato": 10,
                "numeroContratoEmpenho": "10/2026",
                "objetoContrato": "Fornecimento de equipamentos",
                "nomeRazaoSocialFornecedor": "Fornecedor Teste Ltda",
                "niFornecedor": "12345678000199",
                "valorInicial": 14900,
                "dataPublicacaoPncp": "2026-09-12T10:00:00",
            }], "paginasRestantes": 0})
        if parts.path.endswith("/atas"):
            return Result({"data": [{
                "numeroControlePNCPAta": "46523056000121-3-000004/2026",
                "anoAta": 2026,
                "sequencialAta": 4,
                "numeroAtaRegistroPreco": "04/2026",
                "objetoContratacao": "Registro de preços para materiais",
                "dataPublicacaoPncp": "2026-09-13T10:00:00",
            }], "paginasRestantes": 0})
        raise AssertionError(url)


def test_pncp_collects_procurements_contracts_and_atas() -> None:
    source = PncpSource(FakeHttp())
    procurements = source.procurements(year=2026)
    contracts = source.contracts(year=2026)
    atas = source.atas(year=2026)

    assert len(procurements) == 1
    assert procurements[0].kind == "licitacao"
    assert procurements[0].attributes["numero_controle_pncp"] == "46523056000121-1-000123/2026"
    assert procurements[0].attributes["valor_estimado"] == 15000.5
    assert len(contracts) == 1
    assert contracts[0].kind == "contrato"
    assert contracts[0].attributes["contratada"] == "Fornecedor Teste Ltda"
    assert len(atas) == 1
    assert atas[0].kind == "ata"

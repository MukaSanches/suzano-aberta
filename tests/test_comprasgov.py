from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

from suzano_aberta.sources.comprasgov import ComprasGovSource


class Result:
    def __init__(self, payload: object) -> None:
        self.text = json.dumps(payload)


class FakeHttp:
    def get(self, url: str, *, attempts: int = 3) -> Result:
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        page = int(query.get("pagina", ["1"])[0])
        if page > 1:
            return Result({"resultado": [], "totalPaginas": 1, "paginasRestantes": 0})

        if parts.path.endswith("1_consultarContratacoes_PNCP_14133"):
            assert "codigoModalidade" in query
            if query["codigoModalidade"][0] != "6":
                return Result({"resultado": [], "totalPaginas": 1, "paginasRestantes": 0})
            return Result({
                "resultado": [{
                    "numeroControlePNCP": "46523056000121-1-000123/2026",
                    "idCompra": "9001",
                    "anoCompraPncp": 2026,
                    "sequencialCompraPncp": 123,
                    "numeroCompra": "063/2026",
                    "processo": "12345/2026",
                    "objetoCompra": "Aquisição de equipamentos",
                    "modalidadeNome": "Dispensa de licitação",
                    "situacaoCompraNomePncp": "Divulgada no PNCP",
                    "modoDisputaNomePncp": "Dispensa com disputa",
                    "dataPublicacaoPncp": "2026-09-10T12:00:00",
                    "dataAberturaPropostaPncp": "2026-09-11T12:00:00",
                    "dataEncerramentoPropostaPncp": "2026-09-12T12:00:00",
                    "valorTotalEstimado": 15000.5,
                    "unidadeOrgaoCodigoUnidade": "987151",
                }],
                "totalPaginas": 1,
                "paginasRestantes": 0,
            })

        if parts.path.endswith("3_consultarResultadoItensContratacoes_PNCP_14133"):
            return Result({
                "resultado": [{
                    "idCompra": "9001",
                    "idCompraItem": "9001-1",
                    "sequencialResultado": 1,
                    "niFornecedor": "12345678000199",
                    "nomeRazaoSocialFornecedor": "Fornecedor Teste Ltda",
                    "valorTotalHomologado": 14900,
                }],
                "totalPaginas": 1,
                "paginasRestantes": 0,
            })

        if parts.path.endswith("1_consultarUasg"):
            assert query["cnpjCpfOrgao"][0] == "46523056000121"
            return Result({
                "resultado": [{
                    "codigoUasg": "987151",
                    "nomeUasg": "PREFEITURA MUNICIPAL DE SUZANO",
                    "cnpjCpfOrgao": "46523056000121",
                }],
                "totalPaginas": 1,
                "paginasRestantes": 0,
            })

        if parts.path.endswith("1_consultarContratos"):
            return Result({
                "resultado": [{
                    "codigoOrgao": 1,
                    "nomeOrgao": "PREFEITURA MUNICIPAL DE SUZANO",
                    "codigoUnidadeGestora": 987151,
                    "nomeUnidadeGestora": "PREFEITURA MUNICIPAL DE SUZANO",
                    "numeroContrato": "10/2026",
                    "processo": "12345/2026",
                    "objeto": "Fornecimento de equipamentos",
                    "nomeRazaoSocialFornecedor": "Fornecedor Teste Ltda",
                    "niFornecedor": "12345678000199",
                    "valorGlobal": 14900,
                    "dataVigenciaInicial": "2026-09-15T00:00:00",
                    "dataVigenciaFinal": "2027-09-14T00:00:00",
                    "dataHoraInclusao": "2026-09-14T10:00:00",
                    "numeroControlePncpContrato": "46523056000121-2-000010/2026",
                    "idCompra": "9001",
                }],
                "totalPaginas": 1,
                "paginasRestantes": 0,
            })

        if parts.path.endswith("1_consultarARP"):
            return Result({
                "resultado": [{
                    "numeroAtaRegistroPreco": "04/2026",
                    "codigoUnidadeGerenciadora": 987151,
                    "nomeUnidadeGerenciadora": "PREFEITURA MUNICIPAL DE SUZANO",
                    "nomeOrgao": "PREFEITURA MUNICIPAL DE SUZANO",
                    "linkAtaPNCP": "https://pncp.gov.br/ata/4",
                    "linkCompraPNCP": "https://pncp.gov.br/compra/9001",
                    "dataAssinatura": "2026-09-13T00:00:00",
                    "dataVigenciaInicial": "2026-09-15T00:00:00",
                    "dataVigenciaFinal": "2027-09-14T00:00:00",
                    "valorTotal": 14900,
                    "statusAta": "Ativa",
                    "objeto": "Registro de preços para equipamentos",
                    "quantidadeItens": 1,
                    "numeroControlePncpAta": "46523056000121-3-000004/2026",
                    "numeroControlePncpCompra": "46523056000121-1-000123/2026",
                    "idCompra": "9001",
                }],
                "totalPaginas": 1,
                "paginasRestantes": 0,
            })

        raise AssertionError(url)


def test_comprasgov_uses_required_modality_and_enriches_awards() -> None:
    records = ComprasGovSource(FakeHttp()).procurements(year=2026)
    assert len(records) == 1
    record = records[0]
    assert record.kind == "licitacao"
    assert record.attributes["numero_controle_pncp"] == "46523056000121-1-000123/2026"
    assert record.attributes["uasg"] == "987151"
    assert record.attributes["resultados_itens"] == 1
    assert record.attributes["resultados_valor_total_homologado"] == 14900
    assert record.attributes["fornecedores_homologados"][0]["nome"] == "Fornecedor Teste Ltda"
    assert record.source.name == "Compras.gov.br — Dados Abertos"


def test_comprasgov_resolves_uasg_and_collects_contracts_and_atas() -> None:
    source = ComprasGovSource(FakeHttp())
    assert source.units()[0]["codigoUasg"] == "987151"

    contracts = source.contracts(year=2026)
    assert len(contracts) == 1
    assert contracts[0].kind == "contrato"
    assert contracts[0].attributes["contratada"] == "Fornecedor Teste Ltda"
    assert contracts[0].attributes["numero_controle_pncp"] == "46523056000121-2-000010/2026"

    atas = source.atas(year=2026)
    assert len(atas) == 1
    assert atas[0].kind == "ata"
    assert atas[0].attributes["situacao"] == "Ativa"
    assert atas[0].attributes["numero_controle_pncp"] == "46523056000121-3-000004/2026"

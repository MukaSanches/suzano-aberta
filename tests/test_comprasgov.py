from __future__ import annotations

import json

from suzano_aberta.sources.comprasgov import ComprasGovSource


class Result:
    def __init__(self, payload: object) -> None:
        self.text = json.dumps(payload)


class FakeHttp:
    def get(self, url: str, *, attempts: int = 3) -> Result:
        if "pagina=1" in url:
            return Result({
                "resultado": [{
                    "numeroControlePNCP": "46523056000121-1-000123/2026",
                    "idCompra": 9001,
                    "anoCompra": 2026,
                    "sequencialCompra": 123,
                    "numeroCompra": "063/2026",
                    "processo": "12345/2026",
                    "objetoCompra": "Aquisição de equipamentos",
                    "modalidadeNome": "Dispensa",
                    "situacaoCompraNome": "Divulgada no PNCP",
                    "dataPublicacaoPncp": "2026-09-10T12:00:00",
                    "valorTotalEstimado": 15000.5,
                    "unidadeOrgaoCodigoUnidade": "987151",
                }],
                "totalPaginas": 1,
            })
        return Result({"resultado": [], "totalPaginas": 1})


def test_comprasgov_normalizes_procurement() -> None:
    records = ComprasGovSource(FakeHttp()).procurements(year=2026)
    assert len(records) == 1
    record = records[0]
    assert record.kind == "licitacao"
    assert record.attributes["numero_controle_pncp"] == "46523056000121-1-000123/2026"
    assert record.attributes["uasg"] == "987151"
    assert record.source.name == "Compras.gov.br — Dados Abertos"

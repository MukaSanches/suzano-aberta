from __future__ import annotations

from scripts.build_portal_enrichment import merge_procurements


def test_merge_procurements_crosses_same_pncp_identifier() -> None:
    items = [
        {
            "id": "pncp:1",
            "kind": "licitacao",
            "title": "Dispensa 63/2026",
            "summary": "Aquisição de equipamentos",
            "date": "2026-09-10",
            "source": {"name": "PNCP", "url": "https://pncp.gov.br/a"},
            "attributes": {
                "numero_controle_pncp": "46523056000121-1-000123/2026",
                "valor_estimado": 15000,
            },
        },
        {
            "id": "comprasgov:1",
            "kind": "licitacao",
            "title": "Dispensa 63/2026",
            "summary": None,
            "date": "2026-09-10",
            "source": {"name": "Compras.gov.br — Dados Abertos", "url": "https://dadosabertos.compras.gov.br/a"},
            "attributes": {
                "numero_controle_pncp": "46523056000121-1-000123/2026",
                "uasg": "987151",
            },
        },
    ]

    merged = merge_procurements(items)
    assert len(merged) == 1
    assert merged[0]["attributes"]["fontes_total"] == 2
    assert merged[0]["attributes"]["uasg"] == "987151"
    assert len(merged[0]["attributes"]["registros_origem"]) == 2

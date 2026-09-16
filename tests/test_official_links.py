from scripts.enrich_official_links import enrich_record, resolve_official_url


def test_resolves_direct_pncp_procurement_url() -> None:
    record = {
        "kind": "licitacao",
        "title": "Dispensa 063/2026",
        "source": {"name": "Portal Nacional de Contratações Públicas (PNCP)", "url": "https://pncp.gov.br/"},
        "attributes": {"numero_controle_pncp": "46523056000121-1-000123/2026"},
    }
    assert resolve_official_url(record) == (
        "https://pncp.gov.br/app/editais/46523056000121/2026/123",
        "exact",
    )


def test_resolves_direct_pncp_contract_url() -> None:
    record = {
        "kind": "contrato",
        "title": "Contrato 10/2026",
        "source": {"name": "PNCP", "url": "https://pncp.gov.br/api/pncp/v1/orgaos/x"},
        "attributes": {"numero_controle_pncp": "46523056000121-2-000010/2026"},
    }
    assert resolve_official_url(record) == (
        "https://pncp.gov.br/app/contratos/46523056000121/2026/10",
        "exact",
    )


def test_resolves_direct_pncp_ata_from_combined_control() -> None:
    record = {
        "kind": "ata",
        "title": "Ata 00112",
        "source": {"name": "PNCP", "url": "https://pncp.gov.br/"},
        "attributes": {"numero_controle_pncp": "46523056000121-1-000187/2026-000003"},
    }
    assert resolve_official_url(record) == (
        "https://pncp.gov.br/app/atas/46523056000121/2026/187/3",
        "exact",
    )


def test_reported_ata_00112_opens_exact_pncp_record() -> None:
    record = {
        "id": "pncp:ata:4c4df136eac04341d99c",
        "kind": "ata",
        "title": "Ata de registro de preços 00112",
        "source": {"name": "Portal Nacional de Contratações Públicas (PNCP)", "url": "https://pncp.gov.br/"},
        "attributes": {
            "numero_controle_pncp": "46523056000121-1-000049/2026-000001",
            "numero_controle_pncp_compra": "46523056000121-1-000049/2026",
        },
    }
    assert resolve_official_url(record) == (
        "https://pncp.gov.br/app/atas/46523056000121/2026/49/1",
        "exact",
    )


def test_resolves_direct_pncp_ata_from_purchase_and_ata_sequences() -> None:
    record = {
        "kind": "ata",
        "title": "Ata 04/2026",
        "source": {"name": "PNCP", "url": "https://pncp.gov.br/"},
        "attributes": {
            "numero_controle_pncp": "46523056000121-3-000004/2026",
            "numero_controle_pncp_compra": "46523056000121-1-000123/2026",
        },
    }
    assert resolve_official_url(record) == (
        "https://pncp.gov.br/app/atas/46523056000121/2026/123/4",
        "exact",
    )


def test_falls_back_to_pncp_search_when_exact_route_cannot_be_derived() -> None:
    record = {
        "kind": "ata",
        "title": "Ata 04/2026",
        "source": {"name": "PNCP", "url": "https://pncp.gov.br/"},
        "attributes": {"identifier": "ATA 04/2026"},
    }
    resolved = resolve_official_url(record)
    assert resolved is not None
    assert resolved[1] == "search"
    assert resolved[0].startswith("https://pncp.gov.br/app/atas?q=")


def test_enrich_record_rewrites_pncp_source_to_exact_detail() -> None:
    record = {
        "kind": "contrato",
        "title": "Contrato 10/2026",
        "source": {"name": "PNCP", "url": "https://pncp.gov.br/"},
        "attributes": {
            "numero_controle_pncp": "46523056000121-2-000010/2026",
            "fontes_cruzadas": [{"name": "PNCP", "url": "https://pncp.gov.br/"}],
        },
    }
    assert enrich_record(record)
    assert record["source"]["url"] == "https://pncp.gov.br/app/contratos/46523056000121/2026/10"
    assert record["attributes"]["official_url_quality"] == "exact"
    assert record["attributes"]["fontes_cruzadas"][0]["url"].endswith("/2026/10")

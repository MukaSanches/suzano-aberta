from suzano_aberta.parsing import clean_text, csv_dicts, parse_br_date


def test_clean_text_collapses_whitespace() -> None:
    assert clean_text("  Câmara\n  Municipal\xa0de Suzano ") == "Câmara Municipal de Suzano"


def test_parse_br_date() -> None:
    assert parse_br_date("Sessão em 02/09/2026") == "2026-09-02"
    assert parse_br_date("sem data") is None


def test_csv_dicts_accepts_semicolon() -> None:
    data = "N.°;Data;Contratada;Valor\n001/2026;20/02/2026;Empresa X;R$ 3.948,00\n".encode()
    rows = csv_dicts(data)
    assert rows[0]["n"] == "001/2026"
    assert rows[0]["contratada"] == "Empresa X"

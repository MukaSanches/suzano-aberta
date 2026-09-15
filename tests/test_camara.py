from suzano_aberta.http import HttpResult
from suzano_aberta.sources.camara import CamaraSource, VEREADORES_URL


class FakeHttp:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def get(self, url: str, *, attempts: int = 3) -> HttpResult:
        html = self.pages[url]
        return HttpResult(url=url, status_code=200, content=html.encode(), content_type="text/html; charset=utf-8", encoding="utf-8", elapsed_ms=1)


def test_sessions_and_propositions_are_normalized() -> None:
    sessions_url = "https://www.camarasuzano.sp.gov.br/ordinarias/sessoes_ordinarias.php?ano=2026"
    project_url = "https://www.camarasuzano.sp.gov.br/ordinarias/sessao_projetos.php?sid=908"
    pages = {
        sessions_url: '<html><body><div><a href="sessao_ordinaria.php?sid=908">26ª Sessão Ordinária</a> 02/09/2026</div></body></html>',
        project_url: '<html><body><p>PROJETO DE LEI - 0142/2026 - Institui política pública de exemplo.</p><p>JOÃO DA SILVA</p></body></html>',
    }
    source = CamaraSource(FakeHttp(pages))  # type: ignore[arg-type]
    sessions = source.sessions(year=2026)
    propositions = source.propositions(year=2026, sessions=sessions)
    assert sessions[0].attributes["sid"] == "908"
    assert sessions[0].date == "2026-09-02"
    assert propositions[0].attributes["number"] == "0142/2026"
    assert "política pública" in (propositions[0].summary or "")


def test_councilors_extract_party_alias_and_leave() -> None:
    pages = {VEREADORES_URL: '<html><body><p>Adilson de Lima Franco (União) – Adilson Horse</p><p>André Chiang (PL) – LICENCIADO</p><p>Jaime Siunte (Avante)</p></body></html>'}
    source = CamaraSource(FakeHttp(pages))  # type: ignore[arg-type]
    records = source.councilors()
    assert len(records) == 3
    assert records[0].attributes["partido"] == "UNIÃO"
    assert records[0].attributes["nome_publico"] == "Adilson Horse"
    assert records[1].attributes["licenciado"] is True
    assert records[1].attributes["nome_publico"] is None

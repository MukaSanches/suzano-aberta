from suzano_aberta.http import HttpResult
from suzano_aberta.sources.prefeitura import IMPRENSA_URL, LICITACOES_URL, PrefeituraSource


class FakeHttp:
    def __init__(self, pages: dict[str, str] | None = None) -> None:
        self.pages = pages or {}

    def get(self, url: str, *, attempts: int = 3) -> HttpResult:
        if url in self.pages:
            html = self.pages[url]
        elif url == LICITACOES_URL:
            html = '''<html><body>
            <div><span>09/09/2026</span><h5><a href="/editais-licitacoes/pregao-eletronico-063-2026/">PREGÃO ELETRÔNICO Nº: 063/2026</a></h5></div>
            <div><span>09/09/2025</span><h5><a href="/editais-licitacoes/pregao-eletronico-099-2025/">PREGÃO ELETRÔNICO Nº: 099/2025</a></h5></div>
            </body></html>'''
        else:
            raise KeyError(url)
        return HttpResult(url=url, status_code=200, content=html.encode(), content_type="text/html; charset=utf-8", encoding="utf-8", elapsed_ms=1)


def test_tenders_preserve_official_url_and_filter_year() -> None:
    source = PrefeituraSource(FakeHttp())  # type: ignore[arg-type]
    records = source.tenders(year=2026)
    assert len(records) == 1
    assert records[0].attributes["identifier"] == "063/2026"
    assert records[0].source.url.endswith("/pregao-eletronico-063-2026/")


def test_official_gazette_tracks_canonical_edition_page() -> None:
    pages = {IMPRENSA_URL: '''<html><body>
    <article><time>15/09/2026</time><h5><a href="/imprensa-oficial/edicao-193-15-09-2026/">Edição 193 – 15.09.2026</a></h5></article>
    <article><time>30/12/2025</time><h5><a href="/imprensa-oficial/edicao-120-30-12-2025/">Edição 120 – 30.12.2025</a></h5></article>
    </body></html>'''}
    source = PrefeituraSource(FakeHttp(pages))  # type: ignore[arg-type]
    records = source.official_gazette(year=2026)
    assert len(records) == 1
    assert records[0].date == "2026-09-15"
    assert records[0].attributes["edicao"] == "193"
    assert records[0].source.url.endswith("/edicao-193-15-09-2026/")

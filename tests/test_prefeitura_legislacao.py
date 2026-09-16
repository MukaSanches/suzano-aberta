from suzano_aberta.http import HttpResult
from suzano_aberta.sources.prefeitura_legislacao import ROOT, PrefeituraLegislationSource


class FakeHttp:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def get(self, url: str, *, attempts: int = 3) -> HttpResult:
        html = self.pages[url]
        return HttpResult(
            url=url,
            status_code=200,
            content=html.encode(),
            content_type="text/html; charset=utf-8",
            encoding="utf-8",
            elapsed_ms=1,
        )


def test_prefeitura_current_listing_yields_laws_and_decrees() -> None:
    law_url = "https://suzano.sp.gov.br/leis-e-decretos/lei-5751/"
    decree_url = "https://suzano.sp.gov.br/leis-e-decretos/decreto-10384/"
    pages = {
        ROOT: f"""<html><body>
        <article><time>30/06/2026</time><h2><a href=\"{law_url}\">LEI 5.751</a></h2></article>
        <article><time>17/03/2026</time><h2><a href=\"{decree_url}\">DECRETO Nº 10.384 DE 17 DE MARÇO DE 2026</a></h2></article>
        </body></html>""",
        law_url: """<html><body><main><article>
        <h1>LEI Nº 5.751 DE 30 DE JUNHO DE 2026</h1>
        <div class="entry-content">LEI Nº 5.751 DE 30 DE JUNHO DE 2026 Dispõe sobre exemplo de norma municipal.
        <a href="/wp-content/uploads/2026/06/lei-5751.pdf">Baixar PDF</a></div>
        </article></main></body></html>""",
        decree_url: """<html><body><main><article>
        <h1>DECRETO Nº 10.384 DE 17 DE MARÇO DE 2026</h1>
        <div class="entry-content">DECRETO Nº 10.384 DE 17 DE MARÇO DE 2026 Regulamenta exemplo de ato municipal.</div>
        </article></main></body></html>""",
    }

    source = PrefeituraLegislationSource(FakeHttp(pages))  # type: ignore[arg-type]
    records = source.collect_range(from_year=2026, to_year=2026, max_pages=1)

    assert len(records) == 2
    law = next(record for record in records if record.kind == "lei")
    decree = next(record for record in records if record.kind == "decreto")

    assert law.date == "2026-06-30"
    assert law.year == 2026
    assert law.attributes["numero"] == "5.751"
    assert law.attributes["document_url"].endswith("/wp-content/uploads/2026/06/lei-5751.pdf")
    assert "Dispõe sobre exemplo" in str(law.attributes["texto_integral"])
    assert law.source.url == law_url

    assert decree.date == "2026-03-17"
    assert decree.year == 2026
    assert decree.attributes["numero"] == "10.384"
    assert decree.source.url == decree_url


def test_prefeitura_legislation_filters_requested_year() -> None:
    old_url = "https://suzano.sp.gov.br/leis-e-decretos/decreto-9737/"
    pages = {
        ROOT: f"""<html><body><article>
        <a href=\"{old_url}\">DECRETO Nº 9.737 DE 04 DE FEVEREIRO DE 2022</a>
        </article></body></html>""",
        old_url: """<html><body><article>
        <h1>DECRETO Nº 9.737 DE 04 DE FEVEREIRO DE 2022</h1>
        <div class="entry-content">DECRETO Nº 9.737 DE 04 DE FEVEREIRO DE 2022 Conteúdo oficial.</div>
        </article></body></html>""",
    }
    source = PrefeituraLegislationSource(FakeHttp(pages))  # type: ignore[arg-type]
    records = source.collect_range(from_year=2026, to_year=2026, max_pages=1)
    assert records == []

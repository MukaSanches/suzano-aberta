from suzano_aberta.http import HttpResult
from suzano_aberta.integrity import TRANSPARENCIA_URL, check_transparency_integrity


class FakeHttp:
    def get(self, url: str, *, attempts: int = 3) -> HttpResult:
        assert url == TRANSPARENCIA_URL
        html = '''<html><body>
        <a href="/editais-licitacoes/">Licitações</a>
        <a href="https://grp.suzano.sp.gov.br/">Portal do Cidadão</a>
        <a href="https://radardatransparencia.atricon.org.br/">Radar</a>
        <a href="https://unexpected.example/offer">conteúdo inesperado</a>
        </body></html>'''
        return HttpResult(
            url=url,
            status_code=200,
            content=html.encode(),
            content_type="text/html; charset=utf-8",
            encoding="utf-8",
            elapsed_ms=12,
        )


def test_integrity_flags_only_unknown_external_hosts() -> None:
    report = check_transparency_integrity(FakeHttp())  # type: ignore[arg-type]

    assert report.status_code == 200
    assert report.ok is False
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.host == "unexpected.example"
    assert finding.evidence == "conteúdo inesperado"
    assert finding.check == "dominio_externo_nao_reconhecido"
    assert "grp.suzano.sp.gov.br" not in report.external_hosts
    assert "radardatransparencia.atricon.org.br" in report.external_hosts

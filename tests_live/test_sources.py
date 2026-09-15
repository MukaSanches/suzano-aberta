from __future__ import annotations

from datetime import datetime

from suzano_aberta import Suzano


def test_official_sources_are_reachable() -> None:
    with Suzano(timeout=30.0, min_interval=0.3) as suzano:
        statuses = suzano.doctor()
    failed = [item for item in statuses if not item.ok]
    assert not failed, [(item.source, item.status_code, item.detail) for item in failed]


def test_current_legislative_sources_return_plausible_data() -> None:
    year = datetime.now().year
    with Suzano(timeout=30.0, min_interval=0.3) as suzano:
        councilors = suzano.camara.councilors()
        sessions = suzano.camara.sessions(year=year)
    assert 10 <= len(councilors) <= 30
    assert sessions
    assert all(item.source.url.startswith("https://www.camarasuzano.sp.gov.br") for item in sessions)


def test_current_executive_sources_return_plausible_data() -> None:
    year = datetime.now().year
    with Suzano(timeout=30.0, min_interval=0.3) as suzano:
        tenders = suzano.prefeitura.tenders(year=year)
        gazette = suzano.prefeitura.official_gazette(year=year, limit=10)
    assert tenders
    assert gazette
    assert all(item.source.url.startswith("https://suzano.sp.gov.br") for item in gazette)


def test_transparency_integrity_check_executes_against_live_source() -> None:
    with Suzano(timeout=30.0, min_interval=0.3) as suzano:
        report = suzano.integrity()
    assert report.status_code == 200
    assert report.source_url == "https://suzano.sp.gov.br/transparencia/"
    assert isinstance(report.findings, list)

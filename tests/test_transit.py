from __future__ import annotations

from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from suzano_aberta.api.settings import ApiSettings
from suzano_aberta.api.transit import ARTESP_OCCURRENCES_URL, ARTESP_PUBLIC_STATUS_URL, ARTESP_STATUS_URL, CPTM_OCCURRENCE_DOWNLOAD_URL, CPTM_STATUS_URLS, Line11StatusService, install_transit_routes
from suzano_aberta.api.app import create_app as create_base_app
from suzano_aberta.store import Store


def _settings(tmp_path: Path, **kwargs: object) -> ApiSettings:
    database = tmp_path / "empty.sqlite3"
    with Store(database):
        pass
    return ApiSettings(database=database, auto_sync=False, transit_cache_seconds=30, **kwargs)


def test_cptm_parser_requires_explicit_line_and_recognized_status(tmp_path: Path) -> None:
    service = Line11StatusService(_settings(tmp_path))
    parsed = service._html('<div>Situação das linhas CORAL Operação Normal Atualizado em: 16/09/2026 14:05</div>', 'CPTM — Situação das Linhas', CPTM_STATUS_URLS[0], 'cptm-status')
    assert parsed is not None
    assert parsed['status'] == 'Operação Normal'
    assert parsed['operation_normal'] is True
    assert parsed['source_updated_at'].startswith('2026-09-16T14:05:00')
    assert service._html('<div>CORAL informação qualquer</div>', 'CPTM', CPTM_STATUS_URLS[0], 'cptm-status') is None


def test_artesp_api_detects_line_11_without_guessing_numeric_id_and_occurrence(tmp_path: Path) -> None:
    settings = _settings(tmp_path, artesp_api_key='test-key')
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get('Authorization') == 'Api-Key test-key'
        if str(request.url).startswith(ARTESP_STATUS_URL):
            return httpx.Response(200, json={'empresas':[{'id':99,'nome':'Operadora oficial retornada pela fonte','linhas':[{'id':777,'nome':'Linha 11-Coral','codigo':'11','status':{'situacao':'Velocidade Reduzida','classificacao':'operacional','operacao_normal':False,'atualizado_em':'2026-09-16T14:10:00-03:00'}}]}]})
        if str(request.url).startswith(ARTESP_OCCURRENCES_URL):
            return httpx.Response(200, json={'ocorrencias':[{'data_hora':'2026-09-16T14:08:00-03:00','linha':{'id':'777','nome':'Linha 11-Coral','codigo':'11'},'situacao':'Velocidade Reduzida','descricao':'Circulação com velocidade reduzida entre as estações Suzano e Estudantes devido a falha técnica.'}]})
        return httpx.Response(404)
    service = Line11StatusService(settings, transport=httpx.MockTransport(handler))
    result = service._artesp_api()
    assert result['status'] == 'Velocidade Reduzida'
    assert result['operator'] == 'Operadora oficial retornada pela fonte'
    assert result['affected_segment'] == 'Suzano – Estudantes'
    assert 'falha técnica' in result['reason']
    assert result['source_updated_at'] == '2026-09-16T14:10:00-03:00'


def test_fallback_uses_artesp_when_cptm_has_no_usable_line_11(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) in CPTM_STATUS_URLS:
            return httpx.Response(200, text='<html><body>Carregando...</body></html>')
        if str(request.url).startswith(ARTESP_PUBLIC_STATUS_URL):
            return httpx.Response(200, text='<div>Linha 11-Coral Operação Normal</div>')
        return httpx.Response(404)
    result = Line11StatusService(settings, transport=httpx.MockTransport(handler)).get()
    assert result['availability'] == 'available'
    assert result['status'] == 'Operação Normal'
    assert result['source']['id'] == 'artesp-status-publico'
    assert any(item['source'] == 'CPTM' for item in result['source_errors'])


def test_last_known_good_is_returned_as_stale_after_sources_fail(tmp_path: Path) -> None:
    clock = [0.0]
    online = [True]
    def handler(request: httpx.Request) -> httpx.Response:
        if online[0] and str(request.url) == CPTM_STATUS_URLS[0]:
            return httpx.Response(200, text='<div>CORAL Operação Normal</div>')
        return httpx.Response(503)
    service = Line11StatusService(_settings(tmp_path, transit_stale_seconds=600), transport=httpx.MockTransport(handler), clock=lambda: clock[0])
    assert service.get()['availability'] == 'available'
    online[0] = False
    clock[0] = 31.0
    second = service.get()
    assert second['availability'] == 'stale'
    assert second['stale'] is True
    assert second['cache']['state'] == 'stale'


def test_unavailable_never_fabricates_status_or_occurrence(tmp_path: Path) -> None:
    service = Line11StatusService(_settings(tmp_path), transport=httpx.MockTransport(lambda request: httpx.Response(503)))
    result = service.get()
    assert result['availability'] == 'unavailable'
    assert result['occurrence'] is None and result['affected_segment'] is None and result['reason'] is None and result['source'] is None
    historical = next(item for item in result['verified_sources'] if item['id'] == 'cptm-ocorrencias-pdf')
    assert historical['url'] == CPTM_OCCURRENCE_DOWNLOAD_URL
    assert historical['eligible_for_live_status'] is False


def test_route_exposes_cache_headers_and_transparent_unavailable_state(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_base_app(settings)
    install_transit_routes(app, settings)
    service = app.state.line11_status_service
    service._cptm = lambda: (_ for _ in ()).throw(RuntimeError('offline'))  # type: ignore[method-assign]
    service._artesp = lambda _: (_ for _ in ()).throw(RuntimeError('offline'))  # type: ignore[method-assign]
    with TestClient(app) as client:
        response = client.get('/v1/transit/line-11')
    assert response.status_code == 200
    assert response.json()['availability'] == 'unavailable'
    assert response.json()['focus_stations'] == ['Calmon Viana','Suzano','Jundiapeba','Estudantes']
    assert 'stale-while-revalidate' in response.headers['cache-control']

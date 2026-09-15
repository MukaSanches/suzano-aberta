from suzano_aberta.entities import build_entity_graph, canonical_entity_id, normalize_cnpj
from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.quality import quality_report


def _record(record_id: str, title: str) -> PublicRecord:
    return PublicRecord(
        id=record_id,
        kind="contrato",
        title=title,
        source=SourceRef(name="Prefeitura Municipal de Suzano", url="https://suzano.sp.gov.br/"),
        attributes={"fornecedor": "Empresa Exemplo 12.345.678/0001-90"},
    )


def test_entity_ids_are_deterministic() -> None:
    assert canonical_entity_id("orgao", "Prefeitura de Suzano") == canonical_entity_id("orgao", "prefeitura de suzano")
    assert normalize_cnpj("12.345.678/0001-90") == "12345678000190"


def test_graph_extracts_cnpj_and_source() -> None:
    graph = build_entity_graph([_record("a", "Contrato A"), _record("b", "Contrato B")])
    suppliers = [entity for entity in graph.entities if entity.kind == "fornecedor"]
    agencies = [entity for entity in graph.entities if entity.kind == "orgao"]
    assert len(suppliers) == 1
    assert suppliers[0].identifier == "12345678000190"
    assert suppliers[0].records == 2
    assert len(agencies) == 1
    assert agencies[0].records == 2


def test_quality_report_is_measurable() -> None:
    report = quality_report([_record("a", "Contrato A"), _record("a", "Contrato duplicado")])
    assert report.records == 2
    assert report.unique_ids == 1
    assert report.duplicate_ids == 1
    assert report.uniqueness == 0.5
    assert report.completeness == 1.0

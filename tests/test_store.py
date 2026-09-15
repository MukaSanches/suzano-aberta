from pathlib import Path

from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.store import Store


def make_record(summary: str = "Objeto original") -> PublicRecord:
    return PublicRecord(
        id="camara:contrato:2026:001/2026",
        kind="contrato",
        title="Contrato 001/2026",
        summary=summary,
        year=2026,
        attributes={"secretaria": "Educação e Cultura"},
        source=SourceRef(name="Câmara", url="https://example.test/contrato"),
    )


def test_store_detects_new_and_changed_records(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with Store(database) as store:
        first = store.upsert_many([make_record()])
        second = store.upsert_many([make_record()])
        third = store.upsert_many([make_record("Objeto atualizado")])

        assert [item.change_type for item in first] == ["novo"]
        assert second == []
        assert [item.change_type for item in third] == ["alterado"]
        assert store.counts_by_kind() == {"contrato": 1}


def test_store_fts_searches_accents_prefixes_and_attributes(tmp_path: Path) -> None:
    database = tmp_path / "search.sqlite3"
    with Store(database) as store:
        store.upsert_many([make_record("Reforma de escola municipal")])

        assert [item.id for item in store.search("educacao")] == [make_record().id]
        assert [item.id for item in store.search("reform escol")] == [make_record().id]
        assert store.rebuild_search_index() == 1
        store.optimize()
        assert store.count_records() == 1

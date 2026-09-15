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

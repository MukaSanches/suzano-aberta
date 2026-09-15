from pathlib import Path

from suzano_aberta.console import parse_command
from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.store import Store


def test_parse_command_supports_windows_quotes() -> None:
    command, args = parse_command('buscar "transporte escolar"')
    assert command == "buscar"
    assert args == ["transporte escolar"]


def test_console_database_can_store_and_retrieve_record(tmp_path: Path) -> None:
    database = tmp_path / "console.sqlite3"
    record = PublicRecord(
        id="teste:1",
        kind="noticia",
        title="Registro de teste",
        source=SourceRef(name="Fonte pública", url="https://example.org/registro"),
    )
    with Store(database) as store:
        store.upsert_many([record])
        loaded = store.get("teste:1")
    assert loaded is not None
    assert loaded.title == "Registro de teste"

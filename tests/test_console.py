from pathlib import Path

from suzano_aberta.console import parse_command, resolve_reference
from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.store import Store


def _record(record_id: str, title: str) -> PublicRecord:
    return PublicRecord(
        id=record_id,
        kind="noticia",
        title=title,
        source=SourceRef(name="Fonte pública", url=f"https://example.org/{record_id}"),
    )


def test_parse_command_supports_windows_quotes() -> None:
    command, args = parse_command('buscar "transporte escolar"')
    assert command == "buscar"
    assert args == ["transporte escolar"]


def test_parse_command_expands_short_aliases() -> None:
    assert parse_command("b educacao") == ("buscar", ["educacao"])
    assert parse_command("diag") == ("diagnostico", [])
    assert parse_command("q") == ("sair", [])


def test_numbered_reference_resolves_last_result() -> None:
    records = [_record("teste:1", "Primeiro"), _record("teste:2", "Segundo")]
    assert resolve_reference("1", records) == "teste:1"
    assert resolve_reference("2", records) == "teste:2"
    assert resolve_reference("teste:2", records) == "teste:2"
    assert resolve_reference("9", records) == "9"


def test_console_database_can_store_and_retrieve_record(tmp_path: Path) -> None:
    database = tmp_path / "console.sqlite3"
    record = _record("teste:1", "Registro de teste")
    with Store(database) as store:
        store.upsert_many([record])
        loaded = store.get("teste:1")
    assert loaded is not None
    assert loaded.title == "Registro de teste"

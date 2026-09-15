from pathlib import Path

from suzano_aberta.diagnostics import human_bytes, inspect_local_environment
from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.store import Store


def test_human_bytes_is_stable() -> None:
    assert human_bytes(0) == "0 B"
    assert human_bytes(1024) == "1.0 KiB"
    assert human_bytes(1024 * 1024) == "1.0 MiB"


def test_diagnostics_explains_missing_database(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite3"
    report = inspect_local_environment(database)
    assert report.records == 0
    assert report.database_bytes == 0
    assert not report.fts_enabled
    assert any(check.name == "Banco local" and check.status == "warning" for check in report.checks)


def test_diagnostics_reads_valid_database_without_mutating_it(tmp_path: Path) -> None:
    database = tmp_path / "healthy.sqlite3"
    record = PublicRecord(
        id="diag:1",
        kind="noticia",
        title="Registro diagnóstico",
        source=SourceRef(name="Fonte pública", url="https://example.org/diag"),
    )
    with Store(database) as store:
        store.upsert_many([record])

    before = database.stat().st_size
    report = inspect_local_environment(database, deep=True)
    after = database.stat().st_size

    assert report.records == 1
    assert report.fts_enabled
    assert report.healthy
    assert before == after
    assert any(check.name == "Integridade SQLite" and check.status == "ok" for check in report.checks)

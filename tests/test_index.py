from __future__ import annotations

from pathlib import Path

import pytest

from suzano_aberta import SuzanoIndex
from suzano_aberta.models import PublicRecord, SourceRef
from suzano_aberta.store import Store


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "index.sqlite3"
    records = [
        PublicRecord(
            id="lei:2026:1",
            kind="lei",
            title="Lei de educação",
            summary="Política municipal de educação.",
            date="2026-09-10",
            year=2026,
            source=SourceRef(name="Prefeitura Municipal de Suzano", url="https://example.test/lei"),
        ),
        PublicRecord(
            id="licitacao:2026:1",
            kind="licitacao",
            title="Transporte escolar",
            summary="Contratação de transporte escolar.",
            date="2026-08-20",
            year=2026,
            source=SourceRef(name="PNCP", url="https://example.test/licitacao"),
        ),
        PublicRecord(
            id="noticia:2025:1",
            kind="noticia",
            title="Notícia antiga",
            date="2025-01-10",
            year=2025,
            source=SourceRef(name="Prefeitura Municipal de Suzano", url="https://example.test/noticia"),
        ),
    ]
    with Store(path) as store:
        store.upsert_many(records)
    return path


def test_local_index_reuses_api_query_semantics(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with SuzanoIndex(database) as index:
        page = index.search("educacao", year=2026)
        assert page.total == 1
        assert page.items[0].id == "lei:2026:1"

        procurements = index.procurements("transporte", year=2026)
        assert procurements.total == 1
        assert procurements.items[0].kind == "licitacao"

        stats = index.stats()
        assert stats.records == 3
        assert stats.legislation == 1
        assert stats.procurements == 1
        assert stats.dataset_version


def test_local_index_pagination_and_iteration(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with SuzanoIndex(database) as index:
        first = index.records(limit=2)
        assert first.total == 3
        assert first.next_offset == 2
        assert first.previous_offset is None
        assert first.has_more is True

        items = list(index.iter_records(page_size=1, max_items=2))
        assert len(items) == 2


def test_local_index_validates_legislation_kind(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with SuzanoIndex(database) as index:
        with pytest.raises(ValueError, match="kind deve ser"):
            index.legislation(kind="contrato")

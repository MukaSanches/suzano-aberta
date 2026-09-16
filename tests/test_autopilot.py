from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import suzano_aberta.autopilot as autopilot_module
from suzano_aberta.autopilot import AutoUpdatePolicy, AutonomousDataManager
from suzano_aberta.snapshot import SnapshotError, snapshot_checksum_path


def _database(path: Path, count: int = 3) -> None:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE records (id TEXT PRIMARY KEY, active INTEGER NOT NULL)")
    connection.executemany(
        "INSERT INTO records(id, active) VALUES (?, 1)",
        [(f"record:{index}",) for index in range(count)],
    )
    connection.commit()
    connection.close()


def test_manager_throttles_checks_and_persists_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "data.sqlite3"
    calls: list[int] = []

    def fake_sync(destination: str | Path, *, timeout: float, min_records: int) -> int:
        calls.append(min_records)
        _database(Path(destination), 5)
        snapshot_checksum_path(destination).write_text("a" * 64 + "\n", encoding="utf-8")
        return 5

    monkeypatch.setattr(autopilot_module, "sync_latest_snapshot", fake_sync)
    manager = AutonomousDataManager(
        database,
        policy=AutoUpdatePolicy(check_interval_seconds=3600),
    )

    first = manager.ensure_fresh(force=True)
    second = manager.ensure_fresh()
    status = manager.status()

    assert first.action == "updated"
    assert first.records == 5
    assert second.action == "skipped"
    assert calls == [1]
    assert status.records == 5
    assert status.last_error is None
    assert status.successful_checks == 1
    assert status.updates == 1
    assert status.remote_checksum == "a" * 64


def test_manager_preserves_existing_database_after_sync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "data.sqlite3"
    _database(database, 10)

    def failed_sync(destination: str | Path, *, timeout: float, min_records: int) -> int:
        assert Path(destination) == database
        assert min_records == 8
        raise SnapshotError("rede indisponível")

    monkeypatch.setattr(autopilot_module, "sync_latest_snapshot", failed_sync)
    manager = AutonomousDataManager(database)
    result = manager.ensure_fresh(force=True)

    assert result.action == "failed"
    assert result.records == 10
    assert manager.status().consecutive_failures == 1
    assert "rede indisponível" in (manager.status().last_error or "")


def test_manager_refuses_parallel_update_when_lock_is_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "data.sqlite3"
    _database(database, 2)
    manager = AutonomousDataManager(database)
    manager.lock_path.write_text("{}", encoding="utf-8")

    def should_not_run(destination: str | Path, *, timeout: float, min_records: int) -> int:
        raise AssertionError("sync não deveria ser executado com lock ativo")

    monkeypatch.setattr(autopilot_module, "sync_latest_snapshot", should_not_run)
    result = manager.ensure_fresh(force=True)

    assert result.action == "busy"
    assert result.records == 2

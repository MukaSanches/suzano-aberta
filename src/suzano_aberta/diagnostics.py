from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DiagnosticStatus = Literal["ok", "warning", "error"]


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    """Resultado pequeno e determinístico de uma verificação local."""

    name: str
    status: DiagnosticStatus
    detail: str

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True, slots=True)
class LocalDiagnostic:
    """Retrato operacional do ambiente local sem chamadas de rede."""

    database: Path
    records: int
    database_bytes: int
    fts_enabled: bool
    last_seen: str | None
    checks: tuple[DiagnosticCheck, ...]

    @property
    def healthy(self) -> bool:
        return not any(check.status == "error" for check in self.checks)


def human_bytes(value: int) -> str:
    """Formata bytes sem dependências externas e sem esconder o valor real."""

    amount = float(max(0, value))
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for unit in units:
        if amount < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024.0
    return f"{value} B"


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def inspect_local_environment(
    database: str | Path = "suzano-aberta.sqlite3",
    *,
    deep: bool = False,
) -> LocalDiagnostic:
    """Inspeciona Python, diretório e SQLite sem modificar o acervo.

    ``deep=False`` é apropriado para a tela inicial. ``deep=True`` também executa
    ``PRAGMA quick_check`` e verifica JSON1, sendo indicado para diagnóstico
    explícito pelo usuário.
    """

    path = Path(database)
    checks: list[DiagnosticCheck] = []

    python_ok = sys.version_info >= (3, 11)
    checks.append(
        DiagnosticCheck(
            "Python",
            "ok" if python_ok else "error",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )

    parent = path.parent if str(path.parent) else Path(".")
    parent_exists = parent.exists()
    writable = parent_exists and os.access(parent, os.W_OK)
    checks.append(
        DiagnosticCheck(
            "Diretório de dados",
            "ok" if writable else "error",
            str(parent.resolve()) if parent_exists else f"não existe: {parent}",
        )
    )

    if parent_exists:
        try:
            free = shutil.disk_usage(parent).free
            disk_status: DiagnosticStatus = "ok" if free >= 256 * 1024 * 1024 else "warning"
            checks.append(DiagnosticCheck("Espaço livre", disk_status, human_bytes(free)))
        except OSError as exc:
            checks.append(DiagnosticCheck("Espaço livre", "warning", str(exc)))

    if not path.exists():
        checks.append(
            DiagnosticCheck(
                "Banco local",
                "warning",
                "ainda não existe; execute sincronizar para instalar o snapshot",
            )
        )
        return LocalDiagnostic(
            database=path,
            records=0,
            database_bytes=0,
            fts_enabled=False,
            last_seen=None,
            checks=tuple(checks),
        )

    size = path.stat().st_size
    records = 0
    fts_enabled = False
    last_seen: str | None = None

    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only=ON")
            records_table = _table_exists(connection, "records")
            if not records_table:
                checks.append(DiagnosticCheck("Esquema SQLite", "error", "tabela records ausente"))
            else:
                row = connection.execute(
                    "SELECT COUNT(*), MAX(last_seen) FROM records WHERE active=1"
                ).fetchone()
                if row is not None:
                    records = int(row[0])
                    last_seen = str(row[1]) if row[1] is not None else None
                checks.append(
                    DiagnosticCheck(
                        "Banco local",
                        "ok" if records > 0 else "warning",
                        f"{records:,} registros · {human_bytes(size)}".replace(",", "."),
                    )
                )

            fts_enabled = _table_exists(connection, "records_fts")
            checks.append(
                DiagnosticCheck(
                    "Busca FTS5",
                    "ok" if fts_enabled else "warning",
                    "índice ativo" if fts_enabled else "indisponível; a busca usa fallback",
                )
            )

            if deep:
                quick_row = connection.execute("PRAGMA quick_check").fetchone()
                quick = str(quick_row[0]) if quick_row is not None else "sem resposta"
                checks.append(
                    DiagnosticCheck(
                        "Integridade SQLite",
                        "ok" if quick.casefold() == "ok" else "error",
                        quick,
                    )
                )
                try:
                    connection.execute("SELECT json('{}')").fetchone()
                except sqlite3.OperationalError as exc:
                    checks.append(DiagnosticCheck("SQLite JSON1", "warning", str(exc)))
                else:
                    checks.append(DiagnosticCheck("SQLite JSON1", "ok", "disponível"))
    except (OSError, sqlite3.DatabaseError) as exc:
        checks.append(DiagnosticCheck("Abertura do banco", "error", str(exc)))

    return LocalDiagnostic(
        database=path,
        records=records,
        database_bytes=size,
        fts_enabled=fts_enabled,
        last_seen=last_seen,
        checks=tuple(checks),
    )

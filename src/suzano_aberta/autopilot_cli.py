from __future__ import annotations

import json
from pathlib import Path
from threading import Event

import typer
from rich.console import Console
from rich.table import Table

from .autopilot import AutoUpdatePolicy, AutonomousDataManager, AutopilotResult

DEFAULT_DATABASE = Path("suzano-aberta.sqlite3")
console = Console()
auto_app = typer.Typer(
    name="auto",
    help="Mantém o snapshot local atualizado de forma autônoma e segura.",
    no_args_is_help=True,
)


def _manager(database: Path, interval: int) -> AutonomousDataManager:
    return AutonomousDataManager(
        database,
        policy=AutoUpdatePolicy(check_interval_seconds=interval),
    )


def _print_result(result: AutopilotResult) -> None:
    labels = {
        "updated": "atualizado",
        "current": "já atual",
        "skipped": "checagem ainda não necessária",
        "busy": "outro processo está atualizando",
        "failed": "falhou; último banco válido foi preservado",
    }
    console.print(
        f"[bold]Autopilot:[/bold] {labels[result.action]} | "
        f"{result.records:,} registros".replace(",", ".")
    )
    if result.error:
        console.print(f"[yellow]{result.error}[/yellow]")


@auto_app.command("status")
def status(
    database: Path = typer.Option(DEFAULT_DATABASE, "--db", help="Arquivo SQLite local."),
    interval: int = typer.Option(900, "--intervalo", min=0, help="Intervalo entre checagens, em segundos."),
    as_json: bool = typer.Option(False, "--json", help="Saída estruturada."),
) -> None:
    """Mostra estado, frescor, falhas e próxima checagem automática."""
    manager = _manager(database, interval)
    report = manager.status()
    if as_json:
        console.print_json(json.dumps(report.to_dict(), ensure_ascii=False))
        return

    table = Table(title="Suzano Aberta — Autopilot local")
    table.add_column("Item")
    table.add_column("Valor")
    table.add_row("Banco", report.database)
    table.add_row("Registros", f"{report.records:,}".replace(",", "."))
    table.add_row("Banco disponível", "sim" if report.database_exists else "não")
    table.add_row("Fresco", "sim" if report.fresh else "não")
    table.add_row("Checagem necessária", "sim" if report.due else "não")
    table.add_row("Outro processo atualizando", "sim" if report.locked else "não")
    table.add_row("Último sucesso", report.last_success_at or "—")
    table.add_row("Próxima checagem", report.next_check_at or "agora")
    table.add_row("Falhas consecutivas", str(report.consecutive_failures))
    table.add_row("Atualizações instaladas", str(report.updates))
    table.add_row("Último erro", report.last_error or "—")
    console.print(table)


@auto_app.command("agora")
def update_now(
    database: Path = typer.Option(DEFAULT_DATABASE, "--db", help="Arquivo SQLite local."),
    interval: int = typer.Option(900, "--intervalo", min=0),
) -> None:
    """Força uma checagem agora, baixando dados somente se o release mudou."""
    result = _manager(database, interval).ensure_fresh(force=True)
    _print_result(result)
    if result.action == "failed":
        raise typer.Exit(code=2)


@auto_app.command("vigiar")
def watch(
    database: Path = typer.Option(DEFAULT_DATABASE, "--db", help="Arquivo SQLite local."),
    interval: int = typer.Option(900, "--intervalo", min=60, help="Segundos entre verificações."),
    once: bool = typer.Option(False, "--uma-vez", help="Executa um ciclo e termina."),
) -> None:
    """Mantém um processo local verificando novas versões do snapshot."""
    manager = _manager(database, interval)
    if once:
        result = manager.ensure_fresh(force=True)
        _print_result(result)
        if result.action == "failed":
            raise typer.Exit(code=2)
        return

    console.print(
        f"Autopilot ativo. Verificação a cada {interval} segundos. "
        "Ctrl+C encerra apenas este processo; o banco atual permanece intacto."
    )
    stop = Event()
    try:
        manager.run_forever(stop_event=stop, on_result=_print_result)
    except KeyboardInterrupt:
        stop.set()
        console.print("Autopilot encerrado.")

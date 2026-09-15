from __future__ import annotations

import shlex
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .catalog import SOURCES
from .core import Suzano, explain
from .snapshot import SnapshotError
from .store import Store

DEFAULT_DATABASE = Path("suzano-aberta.sqlite3")
console = Console()

COMMANDS = (
    ("buscar <texto>", "Pesquisa o acervo e mostra IDs, títulos, datas e fontes."),
    ("ver <id>", "Abre um registro completo e mostra a fonte original."),
    ("panorama", "Mostra a quantidade de registros por tipo."),
    ("mudancas [n]", "Mostra registros novos ou alterados recentemente."),
    ("fontes", "Lista as fontes públicas conhecidas pelo projeto."),
    ("sincronizar", "Instala o snapshot público mais recente."),
    ("reindexar", "Reconstrói e otimiza o índice de pesquisa local."),
    ("status", "Mostra banco em uso, versão e quantidade de registros."),
    ("ajuda", "Mostra os comandos disponíveis."),
    ("limpar", "Limpa a tela."),
    ("sair", "Fecha o console."),
)


def print_help() -> None:
    table = Table(title="Comandos do Suzano Aberta")
    table.add_column("Comando", style="bold")
    table.add_column("O que faz")
    for command, description in COMMANDS:
        table.add_row(command, description)
    console.print(table)


def search_records(query: str, database: Path, *, limit: int = 20) -> None:
    if not query.strip():
        console.print("Uso: buscar <palavra ou expressão>")
        return
    with Suzano(database=database) as suzano:
        records = suzano.search(query, limit=limit)
        bootstrap_error = suzano.last_bootstrap_error
    table = Table(title=f'Resultados para "{query}"')
    table.add_column("ID", overflow="fold")
    table.add_column("Tipo")
    table.add_column("Título", overflow="fold")
    table.add_column("Data")
    table.add_column("Fonte", overflow="fold")
    for record in records:
        table.add_row(
            record.id,
            record.kind,
            record.title,
            record.date or "—",
            record.source.name,
        )
    console.print(table)
    if records:
        console.print("Abra qualquer resultado com: [bold]ver <ID>[/bold]")
    elif bootstrap_error:
        console.print(f"[yellow]Snapshot remoto indisponível: {bootstrap_error}[/yellow]")
    else:
        console.print("Nenhum resultado encontrado.")


def show_record(record_id: str, database: Path) -> None:
    if not record_id.strip():
        console.print("Uso: ver <ID>")
        return
    with Store(database) as store:
        record = store.get(record_id)
    if record is None:
        console.print("[yellow]Registro não encontrado.[/yellow]")
        return
    console.print(Panel(explain(record), title=record.title, expand=False))


def show_snapshot(database: Path) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        counts = suzano.snapshot()
    table = Table(title="Panorama local")
    table.add_column("Tipo")
    table.add_column("Registros", justify="right")
    for kind, count in counts.items():
        table.add_row(kind, str(count))
    console.print(table)
    if not counts:
        console.print("O banco ainda está vazio. Execute [bold]sincronizar[/bold].")


def show_changes(database: Path, limit: int) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        items = suzano.changes(limit=limit)
    table = Table(title="Mudanças detectadas")
    table.add_column("Quando")
    table.add_column("Tipo")
    table.add_column("Registro")
    table.add_column("Evento")
    for item in items:
        table.add_row(
            item.observed_at.isoformat(timespec="seconds"),
            item.kind,
            item.record_id,
            item.change_type,
        )
    console.print(table)


def show_sources() -> None:
    table = Table(title="Fontes públicas catalogadas")
    table.add_column("Chave")
    table.add_column("Fonte")
    table.add_column("Categoria")
    table.add_column("Autoridade")
    for source in SOURCES:
        table.add_row(source.key, source.name, source.category, source.authority)
    console.print(table)


def sync_database(database: Path) -> None:
    try:
        with Suzano(database=database, auto_sync=False) as suzano:
            count = suzano.sync()
    except SnapshotError as exc:
        console.print(f"[red]Não foi possível sincronizar:[/red] {exc}")
        return
    console.print(f"Snapshot instalado com [bold]{count}[/bold] registros pesquisáveis.")


def reindex_database(database: Path) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        count = suzano.reindex()
    console.print(f"Índice reconstruído para [bold]{count}[/bold] registros.")


def show_status(database: Path) -> None:
    with Store(database) as store:
        records = store.count_records()
        fts = store.fts_enabled
    table = Table(title="Status local")
    table.add_column("Item")
    table.add_column("Valor")
    table.add_row("Versão", __version__)
    table.add_row("Banco", str(database.resolve()))
    table.add_row("Registros", str(records))
    table.add_row("FTS5", "ativo" if fts else "fallback")
    console.print(table)


def parse_command(raw: str) -> tuple[str, list[str]]:
    parts = shlex.split(raw, posix=False)
    if not parts:
        return "", []
    return parts[0].casefold(), [part.strip('"') for part in parts[1:]]


def run_console(database: Path = DEFAULT_DATABASE) -> None:
    console.print(
        Panel.fit(
            f"[bold]Suzano Aberta {__version__}[/bold]\n"
            "Console interativo para consultar informação pública pelo terminal.\n"
            "Digite [bold]ajuda[/bold] para conhecer os comandos.",
            title="Suzano Aberta",
        )
    )
    while True:
        try:
            raw = console.input("\n[bold cyan]suzano>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nEncerrando.")
            return
        if not raw:
            continue
        try:
            command, args = parse_command(raw)
            if command in {"sair", "exit", "quit"}:
                console.print("Encerrando.")
                return
            if command in {"ajuda", "help", "?"}:
                print_help()
            elif command == "buscar":
                search_records(" ".join(args), database)
            elif command == "ver":
                show_record(args[0] if args else "", database)
            elif command == "panorama":
                show_snapshot(database)
            elif command in {"mudancas", "mudanças"}:
                limit = int(args[0]) if args else 20
                if limit < 1 or limit > 500:
                    raise ValueError("o limite deve estar entre 1 e 500")
                show_changes(database, limit)
            elif command == "fontes":
                show_sources()
            elif command == "sincronizar":
                sync_database(database)
            elif command == "reindexar":
                reindex_database(database)
            elif command == "status":
                show_status(database)
            elif command in {"limpar", "cls", "clear"}:
                console.clear()
            else:
                console.print(f"Comando desconhecido: [bold]{command}[/bold]. Digite ajuda.")
        except (ValueError, IndexError) as exc:
            console.print(f"[yellow]Comando inválido:[/yellow] {exc}")
        except Exception as exc:
            console.print(f"[red]Não foi possível concluir o comando:[/red] {exc}")


def main() -> None:
    run_console()


if __name__ == "__main__":
    main()

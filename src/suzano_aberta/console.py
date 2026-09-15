from __future__ import annotations

import shlex
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import Suzano, explain
from .store import Store

console = Console()
DEFAULT_DATABASE = Path("suzano-aberta.sqlite3")

HELP = {
    "buscar <texto>": "Pesquisa leis, contratos, licitações, notícias e outros registros.",
    "ver <id>": "Mostra os detalhes de um registro e sua fonte.",
    "panorama": "Mostra quantos registros existem por tipo.",
    "mudancas [n]": "Mostra os registros novos ou alterados mais recentes.",
    "fontes": "Lista as fontes públicas catalogadas.",
    "sincronizar": "Baixa e valida o snapshot público mais recente.",
    "reindexar": "Reconstrói o índice de pesquisa local.",
    "ajuda": "Mostra esta lista de comandos.",
    "limpar": "Limpa a tela.",
    "sair": "Fecha o console.",
}


def _help() -> None:
    table = Table(title="Comandos disponíveis")
    table.add_column("Comando", style="bold")
    table.add_column("O que faz")
    for command, description in HELP.items():
        table.add_row(command, description)
    console.print(table)


def _search(query: str, database: Path) -> None:
    if not query.strip():
        console.print("Use: buscar <palavra ou expressão>")
        return
    with Suzano(database=database) as suzano:
        records = suzano.search(query, limit=20)
    table = Table(title=f'Resultados para "{query}"')
    table.add_column("ID", overflow="fold")
    table.add_column("Tipo")
    table.add_column("Título", overflow="fold")
    table.add_column("Data")
    for record in records:
        table.add_row(record.id, record.kind, record.title, record.date or "—")
    console.print(table)
    if not records:
        console.print("Nenhum resultado encontrado.")
    else:
        console.print("Para abrir um item: ver <ID>")


def _show(record_id: str, database: Path) -> None:
    if not record_id:
        console.print("Use: ver <ID>")
        return
    with Store(database) as store:
        records = store.search(record_id, limit=10)
    record = next((item for item in records if item.id == record_id), None)
    if record is None:
        console.print("Registro não encontrado.")
        return
    console.print(Panel(explain(record), title=record.title, expand=False))


def _snapshot(database: Path) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        counts = suzano.snapshot()
    table = Table(title="Panorama local")
    table.add_column("Tipo")
    table.add_column("Registros", justify="right")
    for kind, count in counts.items():
        table.add_row(kind, str(count))
    console.print(table)


def _changes(database: Path, limit: int) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        items = suzano.changes(limit=limit)
    table = Table(title="Mudanças detectadas")
    table.add_column("Quando")
    table.add_column("Tipo")
    table.add_column("Registro")
    table.add_column("Evento")
    for item in items:
        table.add_row(item.observed_at.isoformat(timespec="seconds"), item.kind, item.record_id, item.change_type)
    console.print(table)


def _sources() -> None:
    from .catalog import SOURCES

    table = Table(title="Fontes públicas")
    table.add_column("Chave")
    table.add_column("Fonte")
    table.add_column("Categoria")
    for source in SOURCES:
        table.add_row(source.key, source.name, source.category)
    console.print(table)


def _sync(database: Path) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        count = suzano.sync()
    console.print(f"Snapshot instalado: {count} registros pesquisáveis.")


def _reindex(database: Path) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        count = suzano.reindex()
    console.print(f"Índice reconstruído para {count} registros.")


def run_console(database: Path = DEFAULT_DATABASE) -> None:
    console.print(
        Panel.fit(
            "[bold]Suzano Aberta[/bold]\n"
            "Console interativo para pesquisar informação pública pelo CMD.\n\n"
            "Digite [bold]ajuda[/bold] para ver os comandos.",
            title="Suzano Aberta 0.7",
        )
    )
    while True:
        try:
            raw = console.input("\n[bold cyan]suzano>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nEncerrando Suzano Aberta.")
            return
        if not raw:
            continue
        try:
            parts = shlex.split(raw, posix=False)
        except ValueError as exc:
            console.print(f"Comando inválido: {exc}")
            continue
        command = parts[0].lower()
        args = [item.strip('"') for item in parts[1:]]
        try:
            if command in {"sair", "exit", "quit"}:
                console.print("Até a próxima.")
                return
            if command in {"ajuda", "help", "?"}:
                _help()
            elif command == "buscar":
                _search(" ".join(args), database)
            elif command == "ver":
                _show(args[0] if args else "", database)
            elif command == "panorama":
                _snapshot(database)
            elif command in {"mudancas", "mudanças"}:
                limit = int(args[0]) if args else 20
                _changes(database, limit)
            elif command == "fontes":
                _sources()
            elif command == "sincronizar":
                _sync(database)
            elif command == "reindexar":
                _reindex(database)
            elif command in {"limpar", "cls", "clear"}:
                console.clear()
            else:
                console.print(f"Comando desconhecido: {command}. Digite ajuda.")
        except Exception as exc:
            console.print(f"[red]Não foi possível concluir o comando:[/red] {exc}")

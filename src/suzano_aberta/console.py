from __future__ import annotations

import shlex
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .catalog import SOURCES
from .core import Suzano, explain
from .diagnostics import LocalDiagnostic, human_bytes, inspect_local_environment
from .index import SuzanoIndex
from .models import PublicRecord
from .snapshot import SnapshotError
from .store import Store

DEFAULT_DATABASE = Path("suzano-aberta.sqlite3")
console = Console()

COMMANDS = (
    ("buscar <texto>", "Pesquisa o acervo. Texto digitado sozinho também vira busca."),
    ("ver <id|n>", "Abre um registro por ID ou pelo número do último resultado."),
    ("fonte <id|n>", "Mostra a URL pública original de um registro."),
    ("abrir <id|n>", "Abre a fonte pública original no navegador padrão."),
    ("recentes [n]", "Mostra os registros mais recentes do índice local."),
    ("panorama", "Mostra a quantidade de registros por tipo."),
    ("mudancas [n]", "Mostra registros novos ou alterados recentemente."),
    ("fontes", "Lista as fontes públicas conhecidas pelo projeto."),
    ("sincronizar", "Instala o snapshot público mais recente."),
    ("reindexar", "Reconstrói e otimiza o índice de pesquisa local."),
    ("status", "Mostra um painel resumido do ambiente e do acervo."),
    ("diagnostico", "Executa verificações locais de Python, SQLite, FTS5 e disco."),
    ("sobre", "Explica em poucas linhas o que o Suzano Aberta faz."),
    ("ajuda", "Mostra os comandos disponíveis e atalhos."),
    ("limpar", "Limpa a tela e redesenha o painel inicial."),
    ("sair", "Fecha o console."),
)

ALIASES = {
    "b": "buscar",
    "busca": "buscar",
    "v": "ver",
    "r": "recentes",
    "recente": "recentes",
    "p": "panorama",
    "m": "mudancas",
    "mudanças": "mudancas",
    "f": "fontes",
    "sync": "sincronizar",
    "diag": "diagnostico",
    "diagnóstico": "diagnostico",
    "help": "ajuda",
    "?": "ajuda",
    "cls": "limpar",
    "clear": "limpar",
    "exit": "sair",
    "quit": "sair",
    "q": "sair",
}


@dataclass(slots=True)
class ConsoleSession:
    database: Path
    last_results: list[PublicRecord] = field(default_factory=list)


def _format_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _status_symbol(status: str) -> str:
    if status == "ok":
        return "[green]●[/green]"
    if status == "warning":
        return "[yellow]●[/yellow]"
    return "[red]●[/red]"


def _render_summary(report: LocalDiagnostic) -> Table:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_row(
        f"[bold]{_format_int(report.records)}[/bold]\n[dim]registros[/dim]",
        f"[bold]{'FTS5' if report.fts_enabled else 'fallback'}[/bold]\n[dim]busca[/dim]",
        f"[bold]{human_bytes(report.database_bytes)}[/bold]\n[dim]banco local[/dim]",
        f"[bold]{__version__}[/bold]\n[dim]biblioteca[/dim]",
    )
    return table


def show_home(database: Path) -> None:
    report = inspect_local_environment(database)
    state = "pronto" if report.records else "aguardando snapshot"
    console.print(
        Panel(
            _render_summary(report),
            title=f"[bold]Suzano Aberta {__version__}[/bold] · {state}",
            subtitle="informação pública · local-first · rastreável",
            border_style="cyan" if report.healthy else "yellow",
        )
    )
    if report.records:
        console.print(
            "[dim]Dica:[/dim] digite um assunto diretamente, como [bold]educação[/bold], "
            "ou use [bold]recentes[/bold]. Depois abra um resultado com [bold]1[/bold], "
            "[bold]2[/bold], [bold]3[/bold]..."
        )
    else:
        console.print(
            "[yellow]O índice local ainda não está preparado.[/yellow] "
            "Execute [bold]sincronizar[/bold] ou simplesmente faça sua primeira busca."
        )


def print_help() -> None:
    table = Table(title="Suzano Aberta · comandos", header_style="bold cyan")
    table.add_column("Comando", style="bold", no_wrap=True)
    table.add_column("O que faz")
    for command, description in COMMANDS:
        table.add_row(command, description)
    console.print(table)
    console.print(
        "[dim]Atalhos:[/dim] b=buscar · v=ver · r=recentes · p=panorama · "
        "m=mudancas · f=fontes · diag=diagnostico · q=sair"
    )
    console.print(
        "[dim]Navegação:[/dim] depois de uma busca, digite apenas [bold]1[/bold], "
        "[bold]2[/bold]... para abrir um resultado."
    )


def _render_records(records: list[PublicRecord], *, title: str) -> None:
    table = Table(title=title, header_style="bold cyan", show_lines=False)
    table.add_column("#", justify="right", style="bold", no_wrap=True)
    table.add_column("Tipo", no_wrap=True)
    table.add_column("Título", overflow="fold", ratio=4)
    table.add_column("Data", no_wrap=True)
    table.add_column("Fonte", overflow="fold", ratio=2)
    for position, record in enumerate(records, start=1):
        table.add_row(
            str(position),
            record.kind,
            Text(record.title),
            record.date or "—",
            Text(record.source.name),
        )
    console.print(table)


def search_records(query: str, database: Path, *, limit: int = 20) -> list[PublicRecord]:
    clean = query.strip()
    if not clean:
        console.print("Uso: buscar <palavra ou expressão>")
        return []
    with Suzano(database=database) as suzano:
        records = suzano.search(clean, limit=limit)
        bootstrap_error = suzano.last_bootstrap_error
    if records:
        _render_records(records, title=f'Resultados para "{clean}"')
        console.print(
            "[dim]Abra pelo número:[/dim] [bold]1[/bold], [bold]2[/bold]... · "
            "[dim]Fonte:[/dim] [bold]fonte 1[/bold] · [dim]Navegador:[/dim] [bold]abrir 1[/bold]"
        )
    elif bootstrap_error:
        console.print(f"[yellow]Snapshot remoto indisponível:[/yellow] {bootstrap_error}")
    else:
        console.print("Nenhum resultado encontrado.")
    return records


def recent_records(database: Path, *, limit: int = 15) -> list[PublicRecord]:
    if not database.exists():
        console.print("O banco local ainda não existe. Execute [bold]sincronizar[/bold].")
        return []
    with SuzanoIndex(database) as index:
        records = index.records(limit=limit, sort="date_desc").items
    if records:
        _render_records(records, title="Publicações mais recentes no índice")
    else:
        console.print("O índice local não contém registros.")
    return records


def resolve_reference(value: str, results: list[PublicRecord]) -> str:
    """Resolve ``1``/``2``... contra a última lista, preservando IDs literais."""

    token = value.strip()
    if token.isdecimal():
        position = int(token)
        if 1 <= position <= len(results):
            return results[position - 1].id
    return token


def _get_record(reference: str, session: ConsoleSession) -> PublicRecord | None:
    record_id = resolve_reference(reference, session.last_results)
    if not record_id:
        return None
    if not session.database.exists():
        return None
    with Store(session.database) as store:
        return store.get(record_id)


def show_record(reference: str, session: ConsoleSession) -> PublicRecord | None:
    if not reference.strip():
        console.print("Uso: ver <ID ou número do resultado>")
        return None
    record = _get_record(reference, session)
    if record is None:
        console.print("[yellow]Registro não encontrado.[/yellow]")
        return None
    console.print(
        Panel(
            Text(explain(record)),
            title=Text(record.title, style="bold"),
            subtitle=Text(record.kind),
            border_style="cyan",
            expand=False,
        )
    )
    console.print(f"[dim]ID:[/dim] {record.id}")
    console.print(f"[dim]Fonte:[/dim] {record.source.url}")
    return record


def show_source(reference: str, session: ConsoleSession, *, open_browser: bool = False) -> None:
    record = _get_record(reference, session)
    if record is None:
        console.print("[yellow]Registro não encontrado.[/yellow]")
        return
    console.print(f"[bold]{record.source.name}[/bold]\n{record.source.url}")
    if open_browser:
        opened = webbrowser.open(record.source.url, new=2)
        if not opened:
            console.print("[yellow]O navegador não confirmou a abertura. Use a URL exibida acima.[/yellow]")


def show_snapshot(database: Path) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        counts = suzano.snapshot()
    table = Table(title="Panorama local", header_style="bold cyan")
    table.add_column("Tipo")
    table.add_column("Registros", justify="right")
    for kind, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        table.add_row(kind, _format_int(count))
    console.print(table)
    if not counts:
        console.print("O banco ainda está vazio. Execute [bold]sincronizar[/bold].")


def show_changes(database: Path, limit: int) -> None:
    with Suzano(database=database, auto_sync=False) as suzano:
        items = suzano.changes(limit=limit)
    table = Table(title="Mudanças detectadas", header_style="bold cyan")
    table.add_column("Quando")
    table.add_column("Tipo")
    table.add_column("Registro", overflow="fold")
    table.add_column("Evento")
    for item in items:
        table.add_row(
            item.observed_at.isoformat(timespec="seconds"),
            item.kind,
            Text(item.record_id),
            item.change_type,
        )
    console.print(table)
    if not items:
        console.print("Nenhuma mudança registrada neste banco.")


def show_sources() -> None:
    table = Table(title="Fontes públicas catalogadas", header_style="bold cyan")
    table.add_column("Chave")
    table.add_column("Fonte")
    table.add_column("Categoria")
    table.add_column("Autoridade")
    for source in SOURCES:
        table.add_row(source.key, source.name, source.category, source.authority)
    console.print(table)


def sync_database(database: Path) -> None:
    try:
        with console.status("[bold cyan]Baixando e validando o snapshot público…[/bold cyan]"):
            with Suzano(database=database, auto_sync=False) as suzano:
                count = suzano.sync()
    except SnapshotError as exc:
        console.print(f"[red]Não foi possível sincronizar:[/red] {exc}")
        return
    console.print(
        f"[green]Snapshot validado e instalado.[/green] "
        f"[bold]{_format_int(count)}[/bold] registros pesquisáveis."
    )


def reindex_database(database: Path) -> None:
    with console.status("[bold cyan]Reconstruindo o índice FTS5…[/bold cyan]"):
        with Suzano(database=database, auto_sync=False) as suzano:
            count = suzano.reindex()
    console.print(f"Índice reconstruído para [bold]{_format_int(count)}[/bold] registros.")


def show_status(database: Path) -> None:
    report = inspect_local_environment(database)
    console.print(_render_summary(report))
    table = Table(title="Estado local", show_header=False)
    table.add_column("Item", style="bold")
    table.add_column("Valor")
    table.add_row("Banco", str(database.resolve()))
    table.add_row("Última observação", report.last_seen or "—")
    table.add_row("Estado", "operacional" if report.healthy else "requer atenção")
    console.print(table)


def show_diagnostics(database: Path) -> None:
    with console.status("[bold cyan]Verificando ambiente local…[/bold cyan]"):
        report = inspect_local_environment(database, deep=True)
    table = Table(title="Diagnóstico local", header_style="bold cyan")
    table.add_column("", width=2)
    table.add_column("Verificação", style="bold")
    table.add_column("Detalhe", overflow="fold")
    for check in report.checks:
        table.add_row(_status_symbol(check.status), check.name, check.detail)
    console.print(table)
    if report.healthy:
        console.print("[green]Nenhum erro local crítico foi detectado.[/green]")
    else:
        console.print("[yellow]Há pelo menos um item que exige correção antes do uso normal.[/yellow]")


def show_about() -> None:
    console.print(
        Panel(
            "O Suzano Aberta transforma publicações públicas dispersas em um acervo "
            "pesquisável e verificável. Cada registro preserva o caminho de volta à fonte.\n\n"
            "O núcleo combina coleta responsável, SQLite, FTS5, histórico, API somente "
            "leitura, SDK Python e portal web. Relações só devem ser apresentadas quando "
            "existir evidência pública verificável; o projeto não produz juízo político.",
            title="Sobre o Suzano Aberta",
            border_style="cyan",
        )
    )


def parse_command(raw: str) -> tuple[str, list[str]]:
    parts = shlex.split(raw, posix=False)
    if not parts:
        return "", []
    command = parts[0].casefold()
    command = ALIASES.get(command, command)
    return command, [part.strip('"') for part in parts[1:]]


def _parse_limit(args: list[str], *, default: int, maximum: int = 500) -> int:
    limit = int(args[0]) if args else default
    if limit < 1 or limit > maximum:
        raise ValueError(f"o limite deve estar entre 1 e {maximum}")
    return limit


def run_console(database: Path = DEFAULT_DATABASE) -> None:
    session = ConsoleSession(database=database)
    show_home(database)
    while True:
        try:
            raw = console.input("\n[bold cyan]suzano›[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nAté a próxima.")
            return
        if not raw:
            continue
        try:
            command, args = parse_command(raw)
            if command == "sair":
                console.print("Até a próxima.")
                return
            if command == "ajuda":
                print_help()
            elif command == "buscar":
                session.last_results = search_records(" ".join(args), database)
            elif command == "ver":
                show_record(args[0] if args else "", session)
            elif command == "fonte":
                show_source(args[0] if args else "", session)
            elif command == "abrir":
                show_source(args[0] if args else "", session, open_browser=True)
            elif command == "recentes":
                session.last_results = recent_records(database, limit=_parse_limit(args, default=15, maximum=100))
                if session.last_results:
                    console.print("[dim]Digite um número para abrir o registro.[/dim]")
            elif command == "panorama":
                show_snapshot(database)
            elif command == "mudancas":
                show_changes(database, _parse_limit(args, default=20))
            elif command == "fontes":
                show_sources()
            elif command == "sincronizar":
                sync_database(database)
                show_status(database)
            elif command == "reindexar":
                reindex_database(database)
            elif command == "status":
                show_status(database)
            elif command == "diagnostico":
                show_diagnostics(database)
            elif command == "sobre":
                show_about()
            elif command == "limpar":
                console.clear()
                show_home(database)
            elif command.isdecimal() and not args:
                show_record(command, session)
            else:
                session.last_results = search_records(raw, database)
        except (ValueError, IndexError) as exc:
            console.print(f"[yellow]Comando inválido:[/yellow] {exc}")
        except Exception as exc:
            console.print(f"[red]Não foi possível concluir o comando:[/red] {exc}")


def main() -> None:
    run_console()


if __name__ == "__main__":
    main()

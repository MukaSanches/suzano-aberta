from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.table import Table

from .catalog import SOURCES
from .core import Profile, Suzano, explain
from .store import Store

DEFAULT_DATABASE = Path("suzano-aberta.sqlite3")

app = typer.Typer(
    name="suzano",
    help="Consulta e preserva dados públicos oficiais do município de Suzano.",
    no_args_is_help=True,
)
console = Console()


def _default_year() -> int:
    return datetime.now().year


@app.command("fontes")
def sources() -> None:
    """Lista as fontes públicas conhecidas pela biblioteca."""
    table = Table(title="Fontes oficiais catalogadas")
    table.add_column("Chave")
    table.add_column("Fonte")
    table.add_column("Categoria")
    table.add_column("Autoridade")
    for source in SOURCES:
        table.add_row(source.key, source.name, source.category, source.authority)
    console.print(table)


@app.command("coletar")
def collect(
    year: Annotated[int | None, typer.Option("--ano", "-a", help="Ano de referência.")] = None,
    profile: Annotated[
        str,
        typer.Option("--perfil", "-p", help="completo, legislativo ou executivo"),
    ] = "completo",
    database: Annotated[Path, typer.Option("--db", help="Arquivo SQLite local.")] = DEFAULT_DATABASE,
) -> None:
    """Coleta fontes oficiais e atualiza o histórico local."""
    if profile not in {"completo", "legislativo", "executivo"}:
        raise typer.BadParameter("Use: completo, legislativo ou executivo")
    resolved_year = year if year is not None else _default_year()
    with Suzano(database=database) as suzano:
        report = suzano.collect(year=resolved_year, profile=cast(Profile, profile))
    table = Table(title=f"Coleta {resolved_year}")
    table.add_column("Métrica")
    table.add_column("Valor", justify="right")
    for key, value in (
        ("Registros", report.records),
        ("Fontes concluídas", report.sources_ok),
        ("Fontes com falha", report.sources_failed),
        ("Novos registros", report.new_records),
        ("Registros alterados", report.changed_records),
    ):
        table.add_row(key, str(value))
    console.print(table)
    for error in report.errors:
        console.print(f"[red]{error}[/red]")
    if report.sources_failed:
        raise typer.Exit(code=2)


@app.command("buscar")
def search(
    query: Annotated[str, typer.Argument(help="Palavra ou expressão para procurar.")],
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    limit: Annotated[int, typer.Option("--limite", "-n")] = 30,
) -> None:
    """Pesquisa o banco local preservando o link da fonte original."""
    with Suzano(database=database) as suzano:
        records = suzano.search(query, limit=limit)
    table = Table(title=f'Resultados para "{query}"')
    table.add_column("Tipo")
    table.add_column("Título")
    table.add_column("Data")
    table.add_column("Fonte")
    for record in records:
        table.add_row(record.kind, record.title, record.date or "—", record.source.url)
    console.print(table)


@app.command("ver")
def show(
    record_id: Annotated[str, typer.Argument(help="ID interno do registro.")],
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
) -> None:
    """Exibe um registro em linguagem simples e a sua fonte."""
    with Store(database) as store:
        records = store.search(record_id, limit=5)
    record = next((item for item in records if item.id == record_id), None)
    if record is None:
        console.print("Registro não encontrado.")
        raise typer.Exit(code=1)
    console.print(explain(record))


@app.command("panorama")
def snapshot(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
) -> None:
    """Mostra um retrato do que já foi coletado."""
    with Suzano(database=database) as suzano:
        counts = suzano.snapshot()
    table = Table(title="Suzano Aberta — panorama local")
    table.add_column("Tipo")
    table.add_column("Registros", justify="right")
    for kind, count in counts.items():
        table.add_row(kind, str(count))
    console.print(table)


@app.command("mudancas")
def changes(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    limit: Annotated[int, typer.Option("--limite", "-n")] = 30,
) -> None:
    """Mostra registros novos ou alterados detectados entre coletas."""
    with Suzano(database=database) as suzano:
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


@app.command("doctor")
def doctor(
    as_json: Annotated[bool, typer.Option("--json", help="Saída JSON para automação.")] = False,
) -> None:
    """Verifica se as fontes oficiais catalogadas continuam acessíveis."""
    with Suzano() as suzano:
        statuses = suzano.doctor()
    if as_json:
        payload = [item.model_dump(mode="json") for item in statuses]
        console.print_json(json.dumps(payload, ensure_ascii=False))
    else:
        table = Table(title="Saúde das fontes")
        table.add_column("Fonte")
        table.add_column("HTTP", justify="right")
        table.add_column("Tempo", justify="right")
        table.add_column("Estado")
        for item in statuses:
            table.add_row(
                item.source,
                str(item.status_code or "—"),
                f"{item.elapsed_ms or 0} ms",
                "OK" if item.ok else "FALHA",
            )
        console.print(table)
    if any(not item.ok for item in statuses):
        raise typer.Exit(code=2)


@app.command("exportar")
def export_data(
    output: Annotated[Path, typer.Argument(help="Arquivo .json de destino.")],
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
) -> None:
    """Exporta todos os registros preservados para JSON."""
    with Store(database) as store:
        count = store.export_json(output)
    console.print(f"{count} registros exportados para {output}")


if __name__ == "__main__":
    app()

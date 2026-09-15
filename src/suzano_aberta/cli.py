from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .catalog import SOURCES
from .core import Profile, Suzano, explain
from .store import Store

app = typer.Typer(
    name="suzano",
    help="Coleta, preserva e consulta dados públicos oficiais do município de Suzano.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _default_year() -> int:
    return datetime.now().year


def _print_json(value: object) -> None:
    console.print_json(json.dumps(value, ensure_ascii=False, default=str))


@app.command("versao")
def version() -> None:
    """Mostra a versão instalada."""
    console.print(f"Suzano Aberta {__version__}")


@app.command("fontes")
def sources(
    as_json: Annotated[bool, typer.Option("--json", help="Saída JSON para automação.")] = False,
) -> None:
    """Lista as fontes públicas conhecidas pela biblioteca."""
    if as_json:
        _print_json([asdict(source) for source in SOURCES])
        return
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
    year: Annotated[int, typer.Option("--ano", "-a", help="Ano de referência.")] = _default_year(),
    profile: Annotated[str, typer.Option("--perfil", "-p", help="completo, legislativo ou executivo")] = "completo",
    database: Annotated[Path, typer.Option("--db", help="Arquivo SQLite local.")] = Path("suzano-aberta.sqlite3"),
    as_json: Annotated[bool, typer.Option("--json", help="Saída JSON para automação.")] = False,
) -> None:
    """Coleta fontes oficiais e atualiza o histórico local."""
    if profile not in {"completo", "legislativo", "executivo"}:
        raise typer.BadParameter("Use: completo, legislativo ou executivo")
    with Suzano(database=database) as suzano:
        report = suzano.collect(year=year, profile=cast(Profile, profile))
    if as_json:
        _print_json(report.model_dump(mode="json"))
    else:
        table = Table(title=f"Coleta {year}")
        table.add_column("Métrica")
        table.add_column("Valor", justify="right")
        for key, value in (
            ("Registros observados", report.records),
            ("Coletores concluídos", report.sources_ok),
            ("Coletores com falha", report.sources_failed),
            ("Novos registros", report.new_records),
            ("Registros alterados", report.changed_records),
            ("Registros que deixaram de aparecer", report.missing_records),
            ("Registros reativados", report.reactivated_records),
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
    database: Annotated[Path, typer.Option("--db")] = Path("suzano-aberta.sqlite3"),
    limit: Annotated[int, typer.Option("--limite", "-n")] = 30,
    kind: Annotated[str | None, typer.Option("--tipo", help="Filtra pelo tipo normalizado.")] = None,
    year: Annotated[int | None, typer.Option("--ano", "-a")] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Pesquisa o acervo local preservando o link da fonte original."""
    with Suzano(database=database) as suzano:
        records = suzano.search(query, limit=limit, kind=kind, year=year)
    if as_json:
        _print_json([record.model_dump(mode="json") for record in records])
        return
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
    record_id: Annotated[str, typer.Argument(help="ID interno exato do registro.")],
    database: Annotated[Path, typer.Option("--db")] = Path("suzano-aberta.sqlite3"),
    history: Annotated[bool, typer.Option("--historico", help="Mostra também o histórico de observações.")] = False,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Exibe um registro e a prova de origem usada pela biblioteca."""
    with Suzano(database=database) as suzano:
        record = suzano.get(record_id)
        changes = suzano.history(record_id) if history else []
    if record is None:
        console.print("Registro não encontrado.")
        raise typer.Exit(code=1)
    if as_json:
        payload = {"record": record.model_dump(mode="json")}
        if history:
            payload["history"] = [item.model_dump(mode="json") for item in changes]
        _print_json(payload)
        return
    console.print(explain(record))
    if history:
        table = Table(title="Histórico")
        table.add_column("Quando")
        table.add_column("Evento")
        table.add_column("Hash anterior")
        table.add_column("Hash atual")
        for item in changes:
            table.add_row(
                item.observed_at.isoformat(timespec="seconds"),
                item.change_type,
                (item.previous_hash or "—")[:12],
                (item.current_hash or "—")[:12],
            )
        console.print(table)


@app.command("panorama")
def snapshot(
    database: Annotated[Path, typer.Option("--db")] = Path("suzano-aberta.sqlite3"),
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Mostra um retrato do acervo local ativo."""
    with Suzano(database=database) as suzano:
        counts = suzano.snapshot()
    if as_json:
        _print_json(counts)
        return
    table = Table(title="Suzano Aberta — panorama local")
    table.add_column("Tipo")
    table.add_column("Registros", justify="right")
    for kind, count in counts.items():
        table.add_row(kind, str(count))
    table.add_section()
    table.add_row("TOTAL", str(sum(counts.values())))
    console.print(table)


@app.command("mudancas")
def changes(
    database: Annotated[Path, typer.Option("--db")] = Path("suzano-aberta.sqlite3"),
    limit: Annotated[int, typer.Option("--limite", "-n")] = 50,
    hours: Annotated[int | None, typer.Option("--ultimas-horas", help="Mostra apenas eventos recentes.")] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Mostra registros novos, alterados, ausentes ou reativados."""
    since = datetime.now(UTC) - timedelta(hours=hours) if hours is not None else None
    with Suzano(database=database) as suzano:
        items = suzano.changes(limit=limit, since=since)
    if as_json:
        _print_json([item.model_dump(mode="json") for item in items])
        return
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
    """Verifica se os pontos de entrada oficiais continuam acessíveis."""
    with Suzano() as suzano:
        statuses = suzano.doctor()
    if as_json:
        _print_json([item.model_dump(mode="json") for item in statuses])
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
    output: Annotated[Path, typer.Argument(help="Destino .json, .jsonl ou .csv.")],
    database: Annotated[Path, typer.Option("--db")] = Path("suzano-aberta.sqlite3"),
    active_only: Annotated[bool, typer.Option("--somente-ativos")] = False,
) -> None:
    """Exporta o acervo local em formato aberto."""
    suffix = output.suffix.casefold()
    with Store(database) as store:
        if suffix == ".json":
            count = store.export_json(output, active_only=active_only)
        elif suffix == ".jsonl":
            count = store.export_jsonl(output, active_only=active_only)
        elif suffix == ".csv":
            count = store.export_csv(output, active_only=active_only)
        else:
            raise typer.BadParameter("Use uma extensão .json, .jsonl ou .csv")
    console.print(f"{count} registros exportados para {output}")


if __name__ == "__main__":
    app()

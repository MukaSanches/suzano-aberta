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
from .diagnostics import human_bytes, inspect_local_environment
from .index import SuzanoIndex
from .snapshot import SnapshotError
from .store import Store

DEFAULT_DATABASE = Path("suzano-aberta.sqlite3")

app = typer.Typer(
    name="suzano",
    help="Consulta, descobre, indexa e preserva dados públicos sobre Suzano.",
    no_args_is_help=True,
)
console = Console()


def _default_year() -> int:
    return datetime.now().year


def _format_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _parse_years(value: str | None) -> list[int] | None:
    if value is None or not value.strip():
        return None
    years: list[int] = []
    for part in value.split(","):
        try:
            year = int(part.strip())
        except ValueError as exc:
            raise typer.BadParameter("Use anos separados por vírgula, por exemplo: 2024,2025,2026") from exc
        if year < 1900 or year > 2100:
            raise typer.BadParameter(f"Ano fora do intervalo esperado: {year}")
        years.append(year)
    return years


def _print_refresh_report(title: str, report: object) -> None:
    from .models import RefreshReport

    if not isinstance(report, RefreshReport):
        raise TypeError("Relatório inesperado")
    table = Table(title=title)
    table.add_column("Métrica")
    table.add_column("Valor", justify="right")
    for key, value in (
        ("Anos", ", ".join(str(item) for item in report.years)),
        ("Registros oficiais observados", report.official_records_seen),
        ("Páginas/arquivos/históricos", report.discovered_records_seen),
        ("Novos registros", report.new_records),
        ("Registros alterados", report.changed_records),
        ("Total no índice", report.indexed_records),
        ("Falhas toleradas", report.sources_failed),
    ):
        table.add_row(key, str(value))
    console.print(table)
    for error in report.errors:
        console.print(f"[yellow]{error}[/yellow]")


@app.command("console")
def interactive_console(
    database: Annotated[Path, typer.Option("--db", help="Arquivo SQLite local.")] = DEFAULT_DATABASE,
) -> None:
    """Abre a experiência interativa navegável do Suzano Aberta."""
    from .console import run_console

    run_console(database)


@app.command("inicio")
def home(
    database: Annotated[Path, typer.Option("--db", help="Arquivo SQLite local.")] = DEFAULT_DATABASE,
) -> None:
    """Mostra um retrato rápido do ambiente local e do acervo."""
    report = inspect_local_environment(database)
    table = Table(title="Suzano Aberta — estado local")
    table.add_column("Item")
    table.add_column("Valor")
    table.add_row("Banco", str(database.resolve()))
    table.add_row("Registros", _format_int(report.records))
    table.add_row("Tamanho", human_bytes(report.database_bytes))
    table.add_row("Busca", "FTS5" if report.fts_enabled else "fallback")
    table.add_row("Última observação", report.last_seen or "—")
    table.add_row("Estado", "operacional" if report.healthy else "requer atenção")
    console.print(table)
    if not report.records:
        console.print("Execute [bold]suzano sincronizar[/bold] para instalar o snapshot público.")


@app.command("diagnostico")
def local_diagnostics(
    database: Annotated[Path, typer.Option("--db", help="Arquivo SQLite local.")] = DEFAULT_DATABASE,
    as_json: Annotated[bool, typer.Option("--json", help="Saída estruturada para automação.")] = False,
) -> None:
    """Verifica Python, diretório, disco, SQLite, FTS5 e integridade do banco local."""
    report = inspect_local_environment(database, deep=True)
    if as_json:
        payload = {
            "healthy": report.healthy,
            "database": str(report.database),
            "records": report.records,
            "database_bytes": report.database_bytes,
            "fts_enabled": report.fts_enabled,
            "last_seen": report.last_seen,
            "checks": [
                {"name": check.name, "status": check.status, "detail": check.detail}
                for check in report.checks
            ],
        }
        console.print_json(json.dumps(payload, ensure_ascii=False))
        return

    table = Table(title="Diagnóstico local")
    table.add_column("Estado")
    table.add_column("Verificação")
    table.add_column("Detalhe")
    for check in report.checks:
        label = {"ok": "OK", "warning": "AVISO", "error": "ERRO"}[check.status]
        table.add_row(label, check.name, check.detail)
    console.print(table)
    if not report.healthy:
        raise typer.Exit(code=2)


@app.command("recentes")
def recent(
    database: Annotated[Path, typer.Option("--db", help="Arquivo SQLite local.")] = DEFAULT_DATABASE,
    limit: Annotated[int, typer.Option("--limite", "-n", min=1, max=100)] = 20,
) -> None:
    """Lista os registros mais recentes do snapshot local."""
    if not database.exists():
        console.print("Banco local não encontrado. Execute 'suzano sincronizar'.")
        raise typer.Exit(code=2)
    with SuzanoIndex(database) as index:
        records = index.records(limit=limit, sort="date_desc").items
    table = Table(title="Publicações mais recentes")
    table.add_column("ID")
    table.add_column("Tipo")
    table.add_column("Título")
    table.add_column("Data")
    table.add_column("Fonte")
    for record in records:
        table.add_row(record.id, record.kind, record.title, record.date or "—", record.source.name)
    console.print(table)


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
    with Suzano(database=database, auto_sync=False) as suzano:
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


@app.command("atualizar")
def refresh(
    years: Annotated[
        str | None,
        typer.Option(
            "--anos",
            help="Anos separados por vírgula. Sem informar, usa os três anos mais recentes.",
        ),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--perfil", "-p", help="completo, legislativo ou executivo"),
    ] = "completo",
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    max_pages: Annotated[
        int,
        typer.Option("--max-paginas", help="Máximo de páginas web visitadas por execução."),
    ] = 750,
    max_depth: Annotated[
        int,
        typer.Option("--profundidade", help="Profundidade máxima do rastreador de links."),
    ] = 3,
    max_documents: Annotated[
        int,
        typer.Option("--max-arquivos", help="Máximo de arquivos cujo conteúdo será extraído nesta execução."),
    ] = 250,
    include_history: Annotated[
        bool,
        typer.Option("--historico", help="Consulta também índices públicos de preservação histórica da web."),
    ] = False,
    max_historical: Annotated[
        int,
        typer.Option("--max-historicos", help="Teto de registros históricos descobertos."),
    ] = 10_000,
    no_discovery: Annotated[
        bool,
        typer.Option("--sem-descoberta", help="Atualiza só os coletores oficiais."),
    ] = False,
    no_news: Annotated[
        bool,
        typer.Option("--sem-noticias-web", help="Não consulta o feed público de notícias da web."),
    ] = False,
) -> None:
    """Executa atualização autônoma de páginas, documentos e, opcionalmente, histórico."""
    if profile not in {"completo", "legislativo", "executivo"}:
        raise typer.BadParameter("Use: completo, legislativo ou executivo")
    if min(max_pages, max_depth, max_documents, max_historical) < 0:
        raise typer.BadParameter("Os limites de coleta não podem ser negativos")

    with Suzano(database=database, auto_sync=False) as suzano:
        report = suzano.refresh(
            years=_parse_years(years),
            profile=cast(Profile, profile),
            discover=not no_discovery,
            include_news=not no_news,
            max_pages=max_pages,
            max_depth=max_depth,
            max_documents=max_documents,
            include_history=include_history,
            max_historical_records=max_historical,
        )

    _print_refresh_report("Atualização autônoma — Suzano Aberta", report)


@app.command("acervo-maximo")
def maximum_archive(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    max_pages: Annotated[
        int,
        typer.Option("--max-paginas", help="Orçamento de páginas para o rastreamento profundo."),
    ] = 6_000,
    max_depth: Annotated[
        int,
        typer.Option("--profundidade", help="Profundidade máxima do rastreamento profundo."),
    ] = 6,
    max_documents: Annotated[
        int,
        typer.Option("--max-arquivos", help="Arquivos públicos a baixar e transformar em texto pesquisável."),
    ] = 1_800,
    max_historical: Annotated[
        int,
        typer.Option("--max-historicos", help="Registros de arquivos/URLs históricas a incorporar."),
    ] = 40_000,
    common_crawl_collections: Annotated[
        int,
        typer.Option("--colecoes-common-crawl", help="Quantidade de índices recentes do Common Crawl a consultar."),
    ] = 12,
) -> None:
    """Expande agressivamente o acervo usando web atual, documentos e arquivos históricos."""
    if min(
        max_pages,
        max_depth,
        max_documents,
        max_historical,
        common_crawl_collections,
    ) < 0:
        raise typer.BadParameter("Os limites de coleta não podem ser negativos")

    with Suzano(database=database, auto_sync=False) as suzano:
        report = suzano.max_archive(
            max_pages=max_pages,
            max_depth=max_depth,
            max_documents=max_documents,
            max_historical_records=max_historical,
            common_crawl_collections=common_crawl_collections,
        )
    _print_refresh_report("Acervo máximo — Suzano Aberta", report)


@app.command("sincronizar")
def sync(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
) -> None:
    """Baixa o snapshot público diário já indexado para pesquisa instantânea."""
    try:
        with Suzano(database=database, auto_sync=False) as suzano:
            count = suzano.sync()
    except SnapshotError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    console.print(f"Snapshot instalado com {_format_int(count)} registros pesquisáveis em {database}.")


@app.command("reindexar")
def reindex(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
) -> None:
    """Reconstrói e otimiza o índice FTS5 local."""
    with Suzano(database=database, auto_sync=False) as suzano:
        count = suzano.reindex()
    console.print(f"Índice reconstruído para {_format_int(count)} registros.")


@app.command("buscar")
def search(
    query: Annotated[str, typer.Argument(help="Palavra ou expressão para procurar.")],
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    limit: Annotated[int, typer.Option("--limite", "-n", min=1, max=500)] = 30,
    no_web: Annotated[
        bool,
        typer.Option("--sem-web", help="Não consulta a web quando o índice local não tem resultado."),
    ] = False,
) -> None:
    """Pesquisa o índice FTS local; em falta, tenta uma descoberta web rápida."""
    with Suzano(database=database) as suzano:
        records = suzano.search(query, limit=limit, live_fallback=not no_web)
        bootstrap_error = suzano.last_bootstrap_error
    table = Table(title=f'Resultados para "{query}"')
    table.add_column("ID")
    table.add_column("Tipo")
    table.add_column("Título")
    table.add_column("Data")
    table.add_column("Fonte")
    for record in records:
        table.add_row(record.id, record.kind, record.title, record.date or "—", record.source.name)
    console.print(table)
    if not records and bootstrap_error:
        console.print(f"[yellow]Snapshot remoto indisponível: {bootstrap_error}[/yellow]")


@app.command("ver")
def show(
    record_id: Annotated[str, typer.Argument(help="ID interno exato do registro.")],
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
) -> None:
    """Exibe um registro em linguagem simples e a sua fonte."""
    with Store(database) as store:
        record = store.get(record_id)
    if record is None:
        console.print("Registro não encontrado.")
        raise typer.Exit(code=1)
    console.print(explain(record))


@app.command("panorama")
def snapshot(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Mostra um retrato do que já foi coletado."""
    with Suzano(database=database, auto_sync=False) as suzano:
        counts = suzano.snapshot()
    if as_json:
        console.print_json(json.dumps(counts, ensure_ascii=False))
        return
    table = Table(title="Suzano Aberta — panorama local")
    table.add_column("Tipo")
    table.add_column("Registros", justify="right")
    for kind, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        table.add_row(kind, _format_int(count))
    console.print(table)


@app.command("mudancas")
def changes(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    limit: Annotated[int, typer.Option("--limite", "-n", min=1, max=500)] = 30,
) -> None:
    """Mostra registros novos ou alterados detectados entre coletas."""
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


@app.command("integridade")
def integrity(
    as_json: Annotated[bool, typer.Option("--json", help="Saída JSON para automação.")] = False,
    fail_on_finding: Annotated[
        bool,
        typer.Option(
            "--falhar-se-encontrar",
            help="Retorna código 3 quando houver domínio externo não reconhecido.",
        ),
    ] = False,
) -> None:
    """Revê links externos inesperados em fontes municipais selecionadas."""
    with Suzano(auto_sync=False) as suzano:
        report = suzano.integrity()

    if as_json:
        console.print_json(report.model_dump_json())
    elif report.ok:
        console.print("Nenhum domínio externo não reconhecido foi encontrado.")
    else:
        table = Table(title="Integridade de fontes — revisão recomendada")
        table.add_column("Domínio")
        table.add_column("Texto observado")
        table.add_column("Destino")
        for finding in report.findings:
            table.add_row(
                finding.host,
                finding.evidence or "—",
                finding.target_url,
            )
        console.print(table)
        console.print(
            "Os achados indicam apenas links externos fora da lista conhecida; "
            "não constituem conclusão sobre incidente ou irregularidade."
        )

    if fail_on_finding and report.findings:
        raise typer.Exit(code=3)


@app.command("doctor")
def doctor(
    as_json: Annotated[bool, typer.Option("--json", help="Saída JSON para automação.")] = False,
) -> None:
    """Verifica se as fontes oficiais catalogadas continuam acessíveis."""
    with Suzano(auto_sync=False) as suzano:
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
    console.print(f"{_format_int(count)} registros exportados para {output}")


if __name__ == "__main__":
    app()

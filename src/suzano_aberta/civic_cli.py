from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .api.repository import ApiRepository
from .content_store import ContentAddressedStore
from .contracts import validate_database_contract
from .lineage import LineageJournal
from .release import manifest_path_for, verify_snapshot_manifest, write_snapshot_manifest
from .sources.registry import default_source_registry
from .store import Store

DEFAULT_DATABASE = Path("suzano-aberta.sqlite3")
app = typer.Typer(help="Qualidade, tempo, lineage, manifests e catálogo do Civic Data Engine.")
console = Console()


def _parse_datetime(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise typer.BadParameter(f"{field} deve ser um instante ISO-8601") from exc


@app.command("quality")
def quality(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    as_json: Annotated[bool, typer.Option("--json")] = False,
    fail_on_error: Annotated[bool, typer.Option("--falhar")] = False,
) -> None:
    """Executa o contrato de dados contra o snapshot local."""
    report = validate_database_contract(database)
    if as_json:
        console.print_json(report.model_dump_json())
    else:
        table = Table(title=f"Data Contract — {report.status.upper()} · {report.score}/100")
        table.add_column("Regra")
        table.add_column("Severidade")
        table.add_column("Resultado")
        if not report.findings:
            table.add_row("core", "—", "Todas as invariantes passaram")
        for finding in report.findings:
            table.add_row(finding.code, finding.severity, finding.message)
        console.print(table)
        console.print(f"Registros: {report.records} · Fontes: {report.sources} · Contrato: {report.contract_sha256[:12]}")
    if fail_on_error and not report.ok:
        raise typer.Exit(code=3)


@app.command("timeline")
def timeline(
    record_id: Annotated[str, typer.Argument()],
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    limit: Annotated[int, typer.Option("--limite", "-n", min=1, max=500)] = 50,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Mostra todas as versões preservadas de um registro."""
    with Store(database) as store:
        versions = store.history(record_id, limit=limit)
    if as_json:
        console.print_json(json.dumps([item.model_dump(mode="json") for item in versions], ensure_ascii=False, default=str))
        return
    table = Table(title=f"Linha do tempo — {record_id}")
    table.add_column("Versão", justify="right")
    table.add_column("Observada em")
    table.add_column("Hash")
    table.add_column("Título")
    for item in versions:
        table.add_row(str(item.version), item.observed_at.isoformat(), item.content_hash[:12], item.record.title)
    console.print(table)


@app.command("at")
def record_at(
    record_id: Annotated[str, typer.Argument()],
    at: Annotated[str, typer.Option("--at", help="Instante ISO-8601")],
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
) -> None:
    """Reconstrói um registro como ele era em um instante observado."""
    moment = _parse_datetime(at, "--at")
    with Store(database) as store:
        record = store.get_at(record_id, moment)
    if record is None:
        console.print("Nenhuma versão observada até esse instante.")
        raise typer.Exit(code=1)
    console.print_json(record.model_dump_json())


@app.command("diff")
def diff(
    from_time: Annotated[str, typer.Option("--from", help="Início exclusivo ISO-8601")],
    to_time: Annotated[str, typer.Option("--to", help="Fim inclusivo ISO-8601")],
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    kind: Annotated[str | None, typer.Option("--tipo")] = None,
    limit: Annotated[int, typer.Option("--limite", "-n", min=1, max=500)] = 100,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Compara mudanças observadas em um intervalo temporal."""
    start = _parse_datetime(from_time, "--from")
    end = _parse_datetime(to_time, "--to")
    with Store(database) as store:
        result = store.diff(start, end, kind=kind, limit=limit)
    if as_json:
        console.print_json(result.model_dump_json())
        return
    table = Table(title=f"Diff · {result.from_time.isoformat()} → {result.to_time.isoformat()}")
    table.add_column("Evento")
    table.add_column("Tipo")
    table.add_column("Registro")
    table.add_column("Quando")
    for item in result.items:
        table.add_row(item.change_type, item.kind, item.record_id, item.observed_at.isoformat())
    console.print(table)
    console.print(f"Total: {result.total} · novos: {result.new} · alterados: {result.changed} · ausentes: {result.absent}")


@app.command("manifest")
def manifest(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    output: Annotated[Path | None, typer.Option("--saida")] = None,
) -> None:
    """Gera um manifesto verificável da geração local."""
    current, report, digest = write_snapshot_manifest(database, output=output)
    console.print_json(current.model_dump_json())
    console.print(f"Manifest SHA-256: {digest}")
    console.print(f"Data Contract: {report.status} ({report.score}/100)")


@app.command("verify")
def verify(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    manifest: Annotated[Path | None, typer.Option("--manifest")] = None,
) -> None:
    """Verifica se SQLite e manifesto ainda correspondem byte a byte."""
    resolved = manifest or manifest_path_for(database)
    if not resolved.exists():
        console.print("Manifesto local não encontrado. Execute `suzano data manifest` primeiro.")
        raise typer.Exit(code=2)
    result = verify_snapshot_manifest(database, resolved)
    if result.ok:
        console.print("VERIFIED: manifesto, SHA-256 e tamanho do SQLite conferem.")
        return
    console.print("FAILED: o SQLite não corresponde ao manifesto.")
    raise typer.Exit(code=3)


@app.command("lineage")
def lineage(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
    limit: Annotated[int, typer.Option("--limite", "-n", min=1, max=500)] = 30,
) -> None:
    """Mostra as execuções recentes do journal OpenLineage local."""
    events = LineageJournal(Path(f"{database}.lineage.jsonl")).tail(limit=limit)
    table = Table(title="Lineage local")
    table.add_column("Quando")
    table.add_column("Evento")
    table.add_column("Job")
    table.add_column("Run ID")
    for event in events:
        run = event.get("run") if isinstance(event.get("run"), dict) else {}
        job = event.get("job") if isinstance(event.get("job"), dict) else {}
        table.add_row(
            str(event.get("eventTime") or "—"),
            str(event.get("eventType") or "—"),
            str(job.get("name") or "—"),
            str(run.get("runId") or "—"),
        )
    console.print(table)


@app.command("catalog")
def catalog(
    database: Annotated[Path, typer.Option("--db")] = DEFAULT_DATABASE,
) -> None:
    """Mostra datasets locais e adaptadores de fonte disponíveis."""
    with ApiRepository(database) as repository:
        stats = repository.stats()
        sources = repository.source_catalog(limit=200)
    console.print(f"Dataset: {repository.dataset_version() if database.exists() else 'indisponível'}")
    console.print(f"Registros: {stats['records']} · fontes observadas: {len(sources)} · temporal: {stats.get('temporal_enabled', False)}")
    table = Table(title="Source SDK")
    table.add_column("Chave")
    table.add_column("Fonte")
    table.add_column("Origem")
    for item in default_source_registry().registrations():
        table.add_row(item.definition.key, item.definition.name, item.origin)
    console.print(table)


@app.command("archive")
def archive(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    store: Annotated[Path, typer.Option("--store")] = Path(".suzano"),
) -> None:
    """Coloca um arquivo no armazenamento imutável endereçado por SHA-256."""
    item = ContentAddressedStore(store).put_file(path)
    console.print(f"{item.sha256}  {item.bytes} bytes  {item.path}")

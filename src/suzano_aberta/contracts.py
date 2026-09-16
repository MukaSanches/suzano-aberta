from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ContractSeverity = Literal["warning", "error"]
ContractStatus = Literal["pass", "warn", "fail"]


class ContractFinding(BaseModel):
    code: str
    severity: ContractSeverity
    message: str
    observed: str | int | float | None = None
    expected: str | int | float | None = None


class DataContract(BaseModel):
    """Contrato mínimo e reproduzível para um snapshot do Suzano Aberta."""

    name: str = "suzano-aberta-core"
    version: str = "1.0.0"
    minimum_records: int = Field(default=1, ge=1)
    minimum_sources: int = Field(default=1, ge=1)
    minimum_previous_ratio: float = Field(default=0.85, gt=0, le=1)
    maximum_missing_title_ratio: float = Field(default=0.0, ge=0, le=1)
    maximum_missing_source_url_ratio: float = Field(default=0.0, ge=0, le=1)
    maximum_stale_seconds: int = Field(default=172_800, ge=60)
    require_fts_consistency: bool = True

    def digest(self) -> str:
        raw = self.model_dump_json(exclude_none=True)
        return sha256(raw.encode("utf-8")).hexdigest()


class ContractReport(BaseModel):
    contract: str
    contract_version: str
    contract_sha256: str
    status: ContractStatus
    score: int = Field(ge=0, le=100)
    checked_at: datetime
    database: str
    records: int = Field(ge=0)
    sources: int = Field(ge=0)
    last_seen: str | None = None
    fts_records: int | None = Field(default=None, ge=0)
    findings: list[ContractFinding] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status != "fail"


DEFAULT_CONTRACT = DataContract()


def _finding(
    findings: list[ContractFinding],
    code: str,
    severity: ContractSeverity,
    message: str,
    *,
    observed: str | int | float | None = None,
    expected: str | int | float | None = None,
) -> None:
    findings.append(
        ContractFinding(
            code=code,
            severity=severity,
            message=message,
            observed=observed,
            expected=expected,
        )
    )


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def validate_database_contract(
    database: str | Path,
    *,
    contract: DataContract = DEFAULT_CONTRACT,
    previous_records: int | None = None,
    now: datetime | None = None,
) -> ContractReport:
    """Valida o snapshot sem modificá-lo.

    As regras são intencionalmente pequenas e determinísticas para que o gate de
    confiança não dependa de serviços externos nem de IA.
    """

    path = Path(database)
    checked_at = (now or datetime.now(UTC)).astimezone(UTC)
    findings: list[ContractFinding] = []
    records = 0
    sources = 0
    last_seen: str | None = None
    fts_records: int | None = None

    if not path.exists():
        _finding(findings, "database_missing", "error", "O snapshot não existe.")
        return _report(path, contract, checked_at, records, sources, last_seen, fts_records, findings)

    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        try:
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or str(quick[0]).casefold() != "ok":
                _finding(
                    findings,
                    "sqlite_integrity",
                    "error",
                    "PRAGMA quick_check não retornou ok.",
                    observed=str(quick[0]) if quick else None,
                    expected="ok",
                )

            has_records = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='records'"
            ).fetchone()
            if has_records is None:
                _finding(findings, "records_table_missing", "error", "Tabela records ausente.")
                return _report(path, contract, checked_at, records, sources, last_seen, fts_records, findings)

            row = connection.execute(
                """
                SELECT COUNT(*) AS records,
                       COUNT(DISTINCT source_name) AS sources,
                       MAX(last_seen) AS last_seen,
                       SUM(CASE WHEN trim(title)='' THEN 1 ELSE 0 END) AS missing_title,
                       SUM(CASE WHEN trim(source_url)='' THEN 1 ELSE 0 END) AS missing_source_url
                FROM records
                WHERE active=1
                """
            ).fetchone()
            if row is not None:
                records = int(row["records"] or 0)
                sources = int(row["sources"] or 0)
                last_seen = str(row["last_seen"]) if row["last_seen"] else None
                missing_title = int(row["missing_title"] or 0)
                missing_source_url = int(row["missing_source_url"] or 0)
            else:
                missing_title = 0
                missing_source_url = 0

            if records < contract.minimum_records:
                _finding(
                    findings,
                    "minimum_records",
                    "error",
                    "Quantidade de registros abaixo do contrato.",
                    observed=records,
                    expected=contract.minimum_records,
                )
            if sources < contract.minimum_sources:
                _finding(
                    findings,
                    "minimum_sources",
                    "error",
                    "Diversidade de fontes abaixo do contrato.",
                    observed=sources,
                    expected=contract.minimum_sources,
                )
            if previous_records and previous_records > 0:
                ratio = records / previous_records
                if ratio < contract.minimum_previous_ratio:
                    _finding(
                        findings,
                        "coverage_regression",
                        "error",
                        "O snapshot perdeu cobertura além do limite permitido.",
                        observed=round(ratio, 6),
                        expected=contract.minimum_previous_ratio,
                    )

            if records:
                title_ratio = missing_title / records
                if title_ratio > contract.maximum_missing_title_ratio:
                    _finding(
                        findings,
                        "missing_titles",
                        "error",
                        "Há títulos vazios acima do limite do contrato.",
                        observed=round(title_ratio, 6),
                        expected=contract.maximum_missing_title_ratio,
                    )
                url_ratio = missing_source_url / records
                if url_ratio > contract.maximum_missing_source_url_ratio:
                    _finding(
                        findings,
                        "missing_source_urls",
                        "error",
                        "Há URLs de origem vazias acima do limite do contrato.",
                        observed=round(url_ratio, 6),
                        expected=contract.maximum_missing_source_url_ratio,
                    )

            duplicate = connection.execute(
                "SELECT COUNT(*) FROM (SELECT id FROM records WHERE active=1 GROUP BY id HAVING COUNT(*)>1)"
            ).fetchone()
            duplicate_count = int(duplicate[0]) if duplicate else 0
            if duplicate_count:
                _finding(
                    findings,
                    "duplicate_ids",
                    "error",
                    "IDs ativos duplicados encontrados.",
                    observed=duplicate_count,
                    expected=0,
                )

            last_seen_dt = _parse_timestamp(last_seen)
            if last_seen_dt is None and records:
                _finding(findings, "freshness_unknown", "warning", "Não foi possível determinar a atualização mais recente.")
            elif last_seen_dt is not None:
                age = max(0, int((checked_at - last_seen_dt).total_seconds()))
                if age > contract.maximum_stale_seconds:
                    _finding(
                        findings,
                        "stale_dataset",
                        "warning",
                        "O snapshot está mais antigo que a janela de frescor esperada.",
                        observed=age,
                        expected=contract.maximum_stale_seconds,
                    )

            has_fts = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='records_fts'"
            ).fetchone()
            if has_fts is not None:
                row_fts = connection.execute("SELECT COUNT(*) FROM records_fts").fetchone()
                fts_records = int(row_fts[0]) if row_fts else 0
                if contract.require_fts_consistency and fts_records != records:
                    _finding(
                        findings,
                        "fts_mismatch",
                        "error",
                        "FTS5 não representa exatamente os registros ativos.",
                        observed=fts_records,
                        expected=records,
                    )
            elif contract.require_fts_consistency:
                _finding(findings, "fts_missing", "error", "Tabela FTS5 ausente do snapshot.")
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        _finding(
            findings,
            "sqlite_error",
            "error",
            f"SQLite recusou o snapshot: {exc}",
        )

    return _report(path, contract, checked_at, records, sources, last_seen, fts_records, findings)


def _report(
    path: Path,
    contract: DataContract,
    checked_at: datetime,
    records: int,
    sources: int,
    last_seen: str | None,
    fts_records: int | None,
    findings: list[ContractFinding],
) -> ContractReport:
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    status: ContractStatus = "fail" if errors else "warn" if warnings else "pass"
    score = max(0, 100 - errors * 20 - warnings * 5)
    return ContractReport(
        contract=contract.name,
        contract_version=contract.version,
        contract_sha256=contract.digest(),
        status=status,
        score=score,
        checked_at=checked_at,
        database=str(path),
        records=records,
        sources=sources,
        last_seen=last_seen,
        fts_records=fts_records,
        findings=findings,
    )

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, Field

LineageEventType = Literal["START", "RUNNING", "COMPLETE", "FAIL", "ABORT", "OTHER"]
PRODUCER = "https://github.com/MukaSanches/suzano-aberta"
SCHEMA_URL = "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent"


class LineageDataset(BaseModel):
    namespace: str
    name: str
    facets: dict[str, object] = Field(default_factory=dict)


class LineageEvent(BaseModel):
    event_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: LineageEventType
    run_id: str
    job_namespace: str = "suzano-aberta"
    job_name: str
    inputs: list[LineageDataset] = Field(default_factory=list)
    outputs: list[LineageDataset] = Field(default_factory=list)
    run_facets: dict[str, object] = Field(default_factory=dict)

    def openlineage_payload(self) -> dict[str, object]:
        return {
            "eventTime": self.event_time.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "eventType": self.event_type,
            "run": {"runId": self.run_id, "facets": self.run_facets},
            "job": {"namespace": self.job_namespace, "name": self.job_name, "facets": {}},
            "inputs": [item.model_dump(mode="json") for item in self.inputs],
            "outputs": [item.model_dump(mode="json") for item in self.outputs],
            "producer": PRODUCER,
            "schemaURL": SCHEMA_URL,
        }


class LineageJournal:
    """Diário append-only de eventos compatíveis com OpenLineage.

    O journal local é o fallback de confiança. Se um endpoint OpenLineage estiver
    configurado, o mesmo evento também pode ser enviado por HTTP, sem tornar o
    serviço remoto obrigatório para a execução do pipeline.
    """

    def __init__(self, path: str | Path = ".suzano/lineage.jsonl") -> None:
        self.path = Path(path)

    def emit(self, event: LineageEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event.openlineage_payload(), ensure_ascii=False, sort_keys=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def tail(self, *, limit: int = 50) -> list[dict[str, object]]:
        if limit < 1:
            return []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        result: list[dict[str, object]] = []
        for line in lines[-limit:]:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                result.append(payload)
        return result


def new_run_id() -> str:
    return str(uuid.uuid4())


def emit_lineage(
    event: LineageEvent,
    *,
    journal: LineageJournal | None = None,
    endpoint: str | None = None,
    timeout: float = 5.0,
) -> None:
    """Persiste localmente e, opcionalmente, envia ao backend OpenLineage."""

    resolved_journal = journal or LineageJournal()
    resolved_journal.emit(event)
    target = endpoint or os.getenv("SUZANO_OPENLINEAGE_URL", "").strip()
    if not target:
        return
    url = target.rstrip("/")
    if not url.endswith("/api/v1/lineage"):
        url += "/api/v1/lineage"
    try:
        response = httpx.post(url, json=event.openlineage_payload(), timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError:
        # O journal local é a fonte de recuperação; observabilidade remota não
        # pode derrubar coleta ou promoção de dados.
        return

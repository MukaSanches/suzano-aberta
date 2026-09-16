from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from opentelemetry import metrics, trace

_TRACER = trace.get_tracer("suzano_aberta", "1.0.0")
_METER = metrics.get_meter("suzano_aberta", "1.0.0")
_OPERATION_COUNTER = _METER.create_counter(
    "suzano.operations",
    unit="{operation}",
    description="Quantidade de operações instrumentadas do Suzano Aberta.",
)
_OPERATION_DURATION = _METER.create_histogram(
    "suzano.operation.duration",
    unit="ms",
    description="Duração das operações instrumentadas do Suzano Aberta.",
)


@contextmanager
def operation_span(
    name: str,
    *,
    attributes: Mapping[str, str | int | float | bool] | None = None,
) -> Iterator[Any]:
    """Cria um span OpenTelemetry sem exigir um backend de observabilidade.

    Sem SDK/exporter configurado, a API oficial do OpenTelemetry é no-op. Isso
    permite instrumentar a biblioteca sem transformar telemetria em dependência
    operacional do caminho de confiança.
    """

    started = time.perf_counter()
    attrs = dict(attributes or {})
    with _TRACER.start_as_current_span(name, attributes=attrs) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            attrs["result"] = "error"
            raise
        else:
            attrs["result"] = "ok"
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            _OPERATION_COUNTER.add(1, attrs)
            _OPERATION_DURATION.record(elapsed_ms, attrs)


def add_span_event(name: str, attributes: Mapping[str, object] | None = None) -> None:
    span = trace.get_current_span()
    if not span.is_recording():
        return
    normalized: dict[str, str | int | float | bool] = {}
    for key, value in (attributes or {}).items():
        if isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        elif value is not None:
            normalized[key] = str(value)
    span.add_event(name, attributes=normalized)

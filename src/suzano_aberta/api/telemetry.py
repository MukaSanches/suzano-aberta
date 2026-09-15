from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from threading import Lock


@dataclass(slots=True)
class ApiMetrics:
    """Métricas locais sem dependência externa.

    Servem para uma instância única e para exposição em formato Prometheus. Em
    implantação horizontal, a agregação pertence ao stack de observabilidade do
    ambiente, não a estado compartilhado dentro da aplicação.
    """

    requests_total: Counter[tuple[str, str, int]] = field(default_factory=Counter)
    duration_micros_sum: Counter[tuple[str, str]] = field(default_factory=Counter)
    duration_count: Counter[tuple[str, str]] = field(default_factory=Counter)
    _lock: Lock = field(default_factory=Lock)

    def observe(self, *, method: str, route: str, status: int, duration_ms: float) -> None:
        safe_route = route or "unknown"
        key = (method.upper(), safe_route)
        with self._lock:
            self.requests_total[(key[0], key[1], int(status))] += 1
            self.duration_micros_sum[key] += max(0, int(duration_ms * 1000))
            self.duration_count[key] += 1

    def prometheus(self) -> str:
        lines = [
            "# HELP suzano_api_requests_total Total de requisições HTTP processadas.",
            "# TYPE suzano_api_requests_total counter",
        ]
        with self._lock:
            request_items = list(self.requests_total.items())
            duration_sum = list(self.duration_micros_sum.items())
            duration_count = list(self.duration_count.items())

        for (method, route, status), count in sorted(request_items):
            lines.append(
                f'suzano_api_requests_total{{method="{_escape(method)}",route="{_escape(route)}",status="{status}"}} {count}'
            )

        lines.extend(
            [
                "# HELP suzano_api_request_duration_seconds_sum Soma da duração das requisições em segundos.",
                "# TYPE suzano_api_request_duration_seconds_sum counter",
            ]
        )
        for (method, route), value_micros in sorted(duration_sum):
            lines.append(
                f'suzano_api_request_duration_seconds_sum{{method="{_escape(method)}",route="{_escape(route)}"}} {value_micros / 1_000_000:.6f}'
            )

        lines.extend(
            [
                "# HELP suzano_api_request_duration_seconds_count Quantidade de observações de duração.",
                "# TYPE suzano_api_request_duration_seconds_count counter",
            ]
        )
        for (method, route), count in sorted(duration_count):
            lines.append(
                f'suzano_api_request_duration_seconds_count{{method="{_escape(method)}",route="{_escape(route)}"}} {count}'
            )
        return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

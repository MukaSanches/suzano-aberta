from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from threading import Lock


@dataclass(slots=True)
class ApiMetrics:
    """Métricas locais sem dependência externa.

    A intenção é fornecer sinais operacionais básicos e um endpoint Prometheus
    compatível. Em implantação distribuída, a agregação deve ser feita pelo
    observability stack do ambiente, não por memória compartilhada do processo.
    """

    requests_total: Counter[tuple[str, str, int]] = field(default_factory=Counter)
    duration_ms_sum: Counter[tuple[str, str]] = field(default_factory=Counter)
    duration_ms_count: Counter[tuple[str, str]] = field(default_factory=Counter)
    _lock: Lock = field(default_factory=Lock)

    def observe(self, *, method: str, route: str, status: int, duration_ms: float) -> None:
        safe_route = route or "unknown"
        key = (method.upper(), safe_route)
        with self._lock:
            self.requests_total[(key[0], key[1], int(status))] += 1
            self.duration_ms_sum[key] += max(0, int(duration_ms * 1000))
            self.duration_ms_count[key] += 1000

    def prometheus(self) -> str:
        lines = [
            "# HELP suzano_api_requests_total Total de requisições HTTP processadas.",
            "# TYPE suzano_api_requests_total counter",
        ]
        with self._lock:
            request_items = list(self.requests_total.items())
            duration_sum = list(self.duration_ms_sum.items())
            duration_count = list(self.duration_ms_count.items())

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
        for (method, route), value_millis in sorted(duration_count):
            lines.append(
                f'suzano_api_request_duration_seconds_count{{method="{_escape(method)}",route="{_escape(route)}"}} {value_millis // 1000}'
            )
        return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")

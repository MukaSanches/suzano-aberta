from __future__ import annotations

import ipaddress
import time
from dataclasses import dataclass
from threading import Lock
from types import TracebackType
from urllib.parse import urljoin, urlsplit

import httpx

from .parsing import decode_bytes


DEFAULT_USER_AGENT = (
    "SuzanoAberta/0.5 (+https://github.com/MukaSanches/suzano-aberta; "
    "indice civico publico, baixa frequencia, contato via repositorio)"
)
DEFAULT_MAX_RESPONSE_BYTES = 64 * 1024 * 1024
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})


class UnsafeUrlError(ValueError):
    """URL não é apropriada para um coletor público."""


class ResponseTooLargeError(RuntimeError):
    """Resposta excedeu o orçamento configurado de bytes."""


@dataclass(slots=True)
class HttpResult:
    url: str
    status_code: int
    content: bytes
    content_type: str
    encoding: str | None
    elapsed_ms: int

    @property
    def text(self) -> str:
        return decode_bytes(self.content, self.encoding)


class PoliteHttpClient:
    """Cliente HTTP defensivo para fontes públicas.

    Aplica intervalo entre requisições, timeouts, redirects validados, limite de
    resposta e retry somente para falhas transitórias. Endereços locais e IPs
    privados literais são recusados por padrão para reduzir risco de SSRF quando
    URLs descobertas na web passam pelo coletor.
    """

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        min_interval: float = 0.15,
        user_agent: str = DEFAULT_USER_AGENT,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        allow_private_networks: bool = False,
        max_redirects: int = 5,
    ) -> None:
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=min(timeout, 10.0)),
            follow_redirects=False,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json,text/csv,application/pdf;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
            },
        )
        self._min_interval = max(0.0, min_interval)
        self._max_response_bytes = max(1024, int(max_response_bytes))
        self._allow_private_networks = allow_private_networks
        self._max_redirects = max(0, int(max_redirects))
        self._last_request = 0.0
        self._lock = Lock()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteHttpClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def get(self, url: str, *, attempts: int = 3) -> HttpResult:
        error: Exception | None = None
        resolved_attempts = max(1, attempts)
        for attempt in range(1, resolved_attempts + 1):
            self._wait_for_slot()
            try:
                return self._request_bytes("GET", url, max_bytes=self._max_response_bytes)
            except (UnsafeUrlError, ResponseTooLargeError):
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                error = exc
                if isinstance(exc, httpx.HTTPStatusError):
                    status = exc.response.status_code
                    if status not in RETRYABLE_STATUS:
                        raise
                    retry_after = self._retry_after(exc.response)
                else:
                    retry_after = None
                if attempt == resolved_attempts:
                    break
                delay = retry_after if retry_after is not None else min(0.5 * (2 ** (attempt - 1)), 2.0)
                time.sleep(delay)
        assert error is not None
        raise error

    def head_or_get(self, url: str) -> tuple[bool, int | None, int, str | None]:
        self._wait_for_slot()
        started = time.perf_counter()
        try:
            result = self._request_bytes("HEAD", url, max_bytes=1024)
            return True, result.status_code, result.elapsed_ms, None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {400, 403, 405, 501}:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                return False, exc.response.status_code, elapsed_ms, str(exc)
        except (httpx.HTTPError, UnsafeUrlError, ResponseTooLargeError) as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return False, None, elapsed_ms, str(exc)

        self._wait_for_slot()
        started = time.perf_counter()
        try:
            result = self._request_bytes(
                "GET",
                url,
                max_bytes=1024 * 1024,
                headers={"Range": "bytes=0-65535"},
            )
            return True, result.status_code, result.elapsed_ms, None
        except httpx.HTTPStatusError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return False, exc.response.status_code, elapsed_ms, str(exc)
        except (httpx.HTTPError, UnsafeUrlError, ResponseTooLargeError) as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return False, None, elapsed_ms, str(exc)

    def _request_bytes(
        self,
        method: str,
        url: str,
        *,
        max_bytes: int,
        headers: dict[str, str] | None = None,
    ) -> HttpResult:
        current = url
        started = time.perf_counter()
        for redirect_count in range(self._max_redirects + 1):
            self._validate_public_url(current)
            with self._client.stream(method, current, headers=headers) as response:
                if response.status_code in REDIRECT_STATUS and response.headers.get("location"):
                    if redirect_count >= self._max_redirects:
                        raise httpx.TooManyRedirects(
                            "Número máximo de redirecionamentos excedido.",
                            request=response.request,
                        )
                    current = urljoin(str(response.url), response.headers["location"])
                    continue

                response.raise_for_status()
                declared = response.headers.get("content-length")
                if declared:
                    try:
                        if int(declared) > max_bytes:
                            raise ResponseTooLargeError(
                                f"Resposta declara {declared} bytes; limite configurado é {max_bytes}."
                            )
                    except ValueError:
                        pass

                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise ResponseTooLargeError(
                            f"Resposta excedeu o limite configurado de {max_bytes} bytes."
                        )
                    chunks.append(chunk)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                return HttpResult(
                    url=str(response.url),
                    status_code=response.status_code,
                    content=b"".join(chunks),
                    content_type=response.headers.get("content-type", ""),
                    encoding=response.encoding,
                    elapsed_ms=elapsed_ms,
                )
        raise RuntimeError("Fluxo de redirects terminou de forma inesperada.")

    def _validate_public_url(self, url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
            raise UnsafeUrlError("Somente URLs HTTP/HTTPS absolutas são permitidas.")
        if self._allow_private_networks:
            return
        host = parts.hostname.casefold().rstrip(".")
        if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local")):
            raise UnsafeUrlError("Endereço local não é permitido pelo coletor público.")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise UnsafeUrlError("Endereço IP não público não é permitido pelo coletor público.")

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("retry-after")
        if not raw:
            return None
        try:
            return min(max(float(raw), 0.0), 5.0)
        except ValueError:
            return None

    def _wait_for_slot(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_request
            remaining = self._min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_request = time.monotonic()

from __future__ import annotations

import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from hashlib import sha256
from threading import Lock
from types import TracebackType

import httpx

from .parsing import decode_bytes


DEFAULT_USER_AGENT = (
    "SuzanoAberta/0.1.0 (+https://github.com/MukaSanches/suzano-aberta; "
    "dados-publicos-municipais; contato-via-github)"
)
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


@dataclass(slots=True, frozen=True)
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

    @property
    def sha256(self) -> str:
        return sha256(self.content).hexdigest()


class PoliteHttpClient:
    """HTTP síncrono com timeout, retry limitado e espaçamento entre requisições."""

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        min_interval: float = 0.20,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=min(timeout, 10.0)),
            follow_redirects=True,
            headers={
                "User-Agent": user_agent,
                "Accept": (
                    "text/html,application/xhtml+xml,application/json,text/csv,"
                    "application/pdf;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.4",
                "Cache-Control": "no-cache",
            },
        )
        self._min_interval = max(0.0, min_interval)
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
        if attempts < 1:
            raise ValueError("attempts deve ser maior ou igual a 1")

        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            self._wait_for_slot()
            started = time.perf_counter()
            try:
                response = self._client.get(url)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                if response.status_code in RETRYABLE_STATUS and attempt < attempts:
                    self._sleep_before_retry(response, attempt)
                    continue
                response.raise_for_status()
                return HttpResult(
                    url=str(response.url),
                    status_code=response.status_code,
                    content=response.content,
                    content_type=response.headers.get("content-type", ""),
                    encoding=response.encoding,
                    elapsed_ms=elapsed_ms,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(min(0.5 * (2 ** (attempt - 1)), 2.0))
                    continue
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                break

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Falha HTTP sem resposta para {url}")

    def head_or_get(self, url: str) -> tuple[bool, int | None, int, str | None]:
        self._wait_for_slot()
        started = time.perf_counter()
        try:
            response = self._client.head(url)
            if response.status_code in {403, 405} or not response.is_success:
                self._wait_for_slot()
                response = self._client.get(url, headers={"Range": "bytes=0-4095"})
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            detail = None if response.is_success else f"HTTP {response.status_code}"
            return response.is_success, response.status_code, elapsed_ms, detail
        except httpx.HTTPError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return False, None, elapsed_ms, str(exc)

    def _wait_for_slot(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_request
            remaining = self._min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_request = time.monotonic()

    @staticmethod
    def _sleep_before_retry(response: httpx.Response, attempt: int) -> None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                seconds = float(retry_after)
            except ValueError:
                try:
                    target = parsedate_to_datetime(retry_after)
                    seconds = max(0.0, target.timestamp() - time.time())
                except (TypeError, ValueError, OverflowError):
                    seconds = 0.0
            time.sleep(min(max(seconds, 0.0), 10.0))
            return
        time.sleep(min(0.5 * (2 ** (attempt - 1)), 2.0))

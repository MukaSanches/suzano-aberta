from __future__ import annotations

import httpx
import pytest
import respx

from suzano_aberta.http import PoliteHttpClient, ResponseTooLargeError, UnsafeUrlError


def test_public_client_rejects_private_literal_addresses() -> None:
    with PoliteHttpClient(min_interval=0) as client:
        with pytest.raises(UnsafeUrlError):
            client.get("http://127.0.0.1/private")
        with pytest.raises(UnsafeUrlError):
            client.get("http://169.254.169.254/latest/meta-data/")
        with pytest.raises(UnsafeUrlError):
            client.get("http://localhost/admin")


@respx.mock
def test_public_client_refuses_oversized_response() -> None:
    respx.get("https://example.test/large").mock(
        return_value=httpx.Response(200, content=b"a" * 4096)
    )
    with PoliteHttpClient(min_interval=0, max_response_bytes=2048) as client:
        with pytest.raises(ResponseTooLargeError):
            client.get("https://example.test/large", attempts=1)


@respx.mock
def test_non_retryable_http_error_fails_fast() -> None:
    route = respx.get("https://example.test/missing").mock(return_value=httpx.Response(404))
    with PoliteHttpClient(min_interval=0) as client:
        with pytest.raises(httpx.HTTPStatusError):
            client.get("https://example.test/missing", attempts=3)
    assert route.call_count == 1


@respx.mock
def test_redirect_target_is_validated_before_following() -> None:
    respx.get("https://example.test/start").mock(
        return_value=httpx.Response(302, headers={"Location": "http://127.0.0.1/internal"})
    )
    with PoliteHttpClient(min_interval=0) as client:
        with pytest.raises(UnsafeUrlError):
            client.get("https://example.test/start", attempts=1)

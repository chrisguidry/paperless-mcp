"""Tests for the paperless HTTP client."""

import httpx
import pytest
import respx
from conftest import paginated

from client import PaperlessClient


async def test_sends_token_and_api_version_headers(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("http://paperless.test/api/tags/").respond(json=paginated([]))

    client = PaperlessClient(base_url="http://paperless.test/", token="secret")
    await client.list_tags({})

    request = respx_mock.calls.last.request
    assert request.headers["Authorization"] == "Token secret"
    assert request.headers["Accept"] == "application/json; version=9"


async def test_raises_on_http_errors(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("http://paperless.test/api/tags/").respond(500)

    client = PaperlessClient(base_url="http://paperless.test", token="secret")

    with pytest.raises(httpx.HTTPStatusError):
        await client.list_tags({})

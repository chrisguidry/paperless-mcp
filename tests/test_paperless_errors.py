"""Tests for how Paperless errors and unexpected errors reach the client."""

import re

import fastmcp
import httpx
import pytest
import respx
from conftest import document_json
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import MCPError

from paperless_errors import describe_status_error


def status_error(
    status: int, json: object = None, text: str | None = None
) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "http://paperless.test/api/documents/")
    response = httpx.Response(status, request=request, json=json, text=text)
    return httpx.HTTPStatusError("error", request=request, response=response)


@pytest.mark.parametrize(
    ("error", "description"),
    [
        (
            status_error(401, json={"detail": "Invalid token."}),
            "Paperless did not accept the token. Check PAPERLESS_TOKEN.",
        ),
        (
            status_error(404, json={"detail": "No Document matches the given query."}),
            "Paperless returned 404: No Document matches the given query.",
        ),
        (
            status_error(400, json={"query": ["Unparsable date.", "Unknown field."]}),
            "Paperless returned 400: query: Unparsable date. Unknown field.",
        ),
        (
            status_error(400, json={"ordering": "Unknown field.", "page": ["Bad."]}),
            "Paperless returned 400: ordering: Unknown field.; page: Bad.",
        ),
        (
            status_error(400, json=["Invalid page."]),
            "Paperless returned 400: Invalid page.",
        ),
        (
            status_error(
                400,
                json={"custom_field_query": {"1": {"0": {"1": ["Bad op.", "Bad."]}}}},
            ),
            "Paperless returned 400: custom_field_query: Bad op. Bad.",
        ),
        (
            status_error(403, text="Invalid more_like_id"),
            "Paperless returned 403: Invalid more_like_id",
        ),
        (
            status_error(500, text="<html>Server Error</html>"),
            "Paperless returned 500: Internal Server Error",
        ),
        (
            status_error(502, text=""),
            "Paperless returned 502: Bad Gateway",
        ),
        (
            status_error(503, text="x" * 201),
            "Paperless returned 503: Service Unavailable",
        ),
    ],
)
def test_describe_status_error(error: httpx.HTTPStatusError, description: str) -> None:
    assert describe_status_error(error) == description


NOT_FOUND = "Paperless returned 404: No Document matches the given query."


async def test_status_errors_reach_the_client_with_paperless_detail(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/999/").respond(
        404, json={"detail": "No Document matches the given query."}
    )

    with pytest.raises(ToolError, match=re.escape(NOT_FOUND)):
        await mcp_client.call_tool("get_document", {"document_id": 999})


async def test_status_errors_reach_resource_readers_with_paperless_detail(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/999/").respond(
        404, json={"detail": "No Document matches the given query."}
    )

    with pytest.raises(MCPError, match=re.escape(NOT_FOUND)):
        await mcp_client.read_resource("paperless://documents/999")


@pytest.mark.parametrize(
    ("failure", "description"),
    [
        (
            httpx.ReadTimeout("timed out"),
            "Paperless did not respond within 30 seconds.",
        ),
        (
            httpx.ConnectError("connection refused"),
            "Could not connect to Paperless. Check PAPERLESS_URL.",
        ),
    ],
)
async def test_transport_errors_reach_the_client_as_descriptions(
    mcp_client: fastmcp.Client[FastMCPTransport],
    respx_mock: respx.MockRouter,
    failure: httpx.TransportError,
    description: str,
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/").mock(side_effect=failure)

    with pytest.raises(ToolError, match=description):
        await mcp_client.call_tool("get_document", {"document_id": 1})


@pytest.mark.parametrize("variable", ["PAPERLESS_URL", "PAPERLESS_TOKEN"])
async def test_missing_configuration_is_named(
    mcp_client: fastmcp.Client[FastMCPTransport],
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    monkeypatch.delenv(variable)

    with pytest.raises(ToolError, match=f"{variable} is not set"):
        await mcp_client.call_tool("get_document", {"document_id": 1})


async def test_unexpected_errors_reach_the_client_without_detail(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/").respond(
        json=document_json(created="not a date")
    )

    with pytest.raises(ToolError) as raised:
        await mcp_client.call_tool("get_document", {"document_id": 1})

    assert "not a date" not in str(raised.value)


async def test_unexpected_errors_reach_resource_readers_without_detail(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/").mock(
        side_effect=RuntimeError("internal secret")
    )

    with pytest.raises(MCPError) as raised:
        await mcp_client.read_resource("paperless://documents/1")

    assert "internal secret" not in str(raised.value)

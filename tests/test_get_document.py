"""Tests for the get_document tool."""

import fastmcp
import pytest
import respx
from conftest import document_json
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError


async def test_gets_metadata_without_content(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/").respond(
        json=document_json(
            notes=[
                {"id": 1, "note": "Paid on time", "created": "2026-06-03T08:00:00Z"}
            ],
            custom_fields=[{"field": 6, "value": "2027-01-01"}],
        )
    )

    result = await mcp_client.call_tool("get_document", {"document_id": 1})

    assert result.structured_content is not None
    document = result.structured_content
    assert document["id"] == 1
    assert document["title"] == "Electric Bill"
    assert document["uri"] == "paperless://documents/1"
    assert document["content"] is None
    assert document["page_count"] == 2
    assert document["mime_type"] == "application/pdf"
    assert document["notes"] == [
        {"id": 1, "note": "Paid on time", "created": "2026-06-03T08:00:00Z"}
    ]
    assert document["custom_fields"] == [{"field": 6, "value": "2027-01-01"}]


async def test_includes_content_when_asked(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/").respond(
        json=document_json()
    )

    result = await mcp_client.call_tool(
        "get_document", {"document_id": 1, "include_content": True}
    )

    assert result.structured_content is not None
    content = result.structured_content["content"]
    assert content == "Your electric service statement for June 2026."


async def test_errors_on_missing_document(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/999/").respond(404)

    with pytest.raises(ToolError, match="404"):
        await mcp_client.call_tool("get_document", {"document_id": 999})


async def test_includes_web_url(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/").respond(
        json=document_json()
    )

    result = await mcp_client.call_tool("get_document", {"document_id": 1})

    assert result.structured_content is not None
    assert result.structured_content["web_url"] == "http://paperless.test/documents/1"

"""Tests for the document resources."""

import base64
import json
import re

import fastmcp
import pytest
import respx
from conftest import document_json
from fastmcp.client.transports import FastMCPTransport
from mcp.shared.exceptions import MCPError
from mcp.types import BlobResourceContents, TextResourceContents


async def test_reads_document_content(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/").respond(
        json=document_json()
    )

    contents = await mcp_client.read_resource("paperless://documents/1")

    assert len(contents) == 1
    assert isinstance(contents[0], TextResourceContents)
    assert contents[0].text == "Your electric service statement for June 2026."
    assert contents[0].mime_type == "text/plain"


async def test_reads_empty_text_for_documents_without_content(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/").respond(
        json=document_json(content=None)
    )

    contents = await mcp_client.read_resource("paperless://documents/1")

    assert isinstance(contents[0], TextResourceContents)
    assert contents[0].text == ""


async def test_reads_document_thumbnail(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/thumb/").respond(
        content=b"webp image bytes", content_type="image/webp"
    )

    contents = await mcp_client.read_resource("paperless://documents/1/thumbnail")

    assert len(contents) == 1
    assert isinstance(contents[0], BlobResourceContents)
    assert base64.b64decode(contents[0].blob) == b"webp image bytes"
    assert contents[0].mime_type == "image/webp"


def note_json(**overrides: object) -> dict[str, object]:
    note: dict[str, object] = {
        "id": 1,
        "note": "Paid on time",
        "created": "2026-06-03T08:00:00Z",
        "user": {"id": 1, "username": "chris", "first_name": "", "last_name": ""},
    }
    return note | overrides


async def test_reads_document_notes(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/notes/").respond(
        json=[note_json(), note_json(id=2, note="Reimbursed")]
    )

    contents = await mcp_client.read_resource("paperless://documents/1/notes")

    assert len(contents) == 1
    assert isinstance(contents[0], TextResourceContents)
    assert contents[0].mime_type == "application/json"
    assert json.loads(contents[0].text) == [
        {"id": 1, "note": "Paid on time", "created": "2026-06-03T08:00:00Z"},
        {"id": 2, "note": "Reimbursed", "created": "2026-06-03T08:00:00Z"},
    ]


async def test_reads_an_empty_list_for_documents_without_notes(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/notes/").respond(json=[])

    contents = await mcp_client.read_resource("paperless://documents/1/notes")

    assert isinstance(contents[0], TextResourceContents)
    assert json.loads(contents[0].text) == []


async def test_reports_when_the_token_cannot_read_notes(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/1/notes/").respond(
        403, text="Insufficient permissions to view notes"
    )

    message = "Paperless returned 403: Insufficient permissions to view notes"
    with pytest.raises(MCPError, match=re.escape(message)):
        await mcp_client.read_resource("paperless://documents/1/notes")

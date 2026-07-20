"""Tests for the document resources."""

import base64

import fastmcp
import respx
from conftest import document_json
from fastmcp.client.transports import FastMCPTransport
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
    assert contents[0].mimeType == "text/plain"


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
    assert contents[0].mimeType == "image/webp"

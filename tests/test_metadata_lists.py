"""Tests for the metadata listing tools."""

from collections.abc import Callable
from typing import Any

import fastmcp
import pytest
import respx
from conftest import (
    correspondent_json,
    custom_field_json,
    document_type_json,
    paginated,
    storage_path_json,
    tag_json,
)
from fastmcp.client.transports import FastMCPTransport

METADATA_TOOLS = [
    pytest.param("list_tags", "/api/tags/", tag_json, "tags", id="tags"),
    pytest.param(
        "list_correspondents",
        "/api/correspondents/",
        correspondent_json,
        "correspondents",
        id="correspondents",
    ),
    pytest.param(
        "list_document_types",
        "/api/document_types/",
        document_type_json,
        "document_types",
        id="document_types",
    ),
    pytest.param(
        "list_storage_paths",
        "/api/storage_paths/",
        storage_path_json,
        "storage_paths",
        id="storage_paths",
    ),
    pytest.param(
        "list_custom_fields",
        "/api/custom_fields/",
        custom_field_json,
        "custom_fields",
        id="custom_fields",
    ),
]


@pytest.mark.parametrize(
    ("tool_name", "path", "factory", "response_key"), METADATA_TOOLS
)
async def test_lists_with_defaults(
    tool_name: str,
    path: str,
    factory: Callable[..., dict[str, Any]],
    response_key: str,
    mcp_client: fastmcp.Client[FastMCPTransport],
    respx_mock: respx.MockRouter,
) -> None:
    item = factory()
    respx_mock.get(f"http://paperless.test{path}").respond(json=paginated([item]))

    result = await mcp_client.call_tool(tool_name, {})

    params = dict(respx_mock.calls.last.request.url.params)
    assert params == {"page": "1", "page_size": "100"}

    assert result.structured_content is not None
    items = result.structured_content[response_key]
    assert len(items) == 1
    assert items[0]["id"] == item["id"]
    assert items[0]["name"] == item["name"]

    assert result.structured_content["pagination"] == {
        "total_count": 1,
        "page": 1,
        "page_size": 100,
        "has_more": False,
    }


@pytest.mark.parametrize(
    ("tool_name", "path", "factory", "response_key"), METADATA_TOOLS
)
async def test_filters_by_name(
    tool_name: str,
    path: str,
    factory: Callable[..., dict[str, Any]],
    response_key: str,
    mcp_client: fastmcp.Client[FastMCPTransport],
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get(f"http://paperless.test{path}").respond(json=paginated([]))

    await mcp_client.call_tool(tool_name, {"name_contains": "elec"})

    params = dict(respx_mock.calls.last.request.url.params)
    assert params["name__icontains"] == "elec"


async def test_tags_include_organizing_details(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/tags/").respond(
        json=paginated([tag_json(is_inbox_tag=True)])
    )

    result = await mcp_client.call_tool("list_tags", {})

    assert result.structured_content is not None
    tag = result.structured_content["tags"][0]
    assert tag["color"] == "#00ff00"
    assert tag["is_inbox_tag"] is True
    assert tag["document_count"] == 12


async def test_storage_paths_include_the_path(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/storage_paths/").respond(
        json=paginated([storage_path_json()])
    )

    result = await mcp_client.call_tool("list_storage_paths", {})

    assert result.structured_content is not None
    storage_path = result.structured_content["storage_paths"][0]
    assert storage_path["path"] == "household/{created_year}"

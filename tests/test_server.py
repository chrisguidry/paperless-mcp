"""Tests for what the server declares about its tools and resources."""

import fastmcp
from fastmcp.client.transports import FastMCPTransport
from mcp.types import Annotations, ToolAnnotations

from effects import READ


async def test_every_tool_is_titled(
    mcp_client: fastmcp.Client[FastMCPTransport],
) -> None:
    tools = await mcp_client.list_tools()

    assert tools
    assert [tool.name for tool in tools if not tool.title] == []


async def test_every_tool_is_tagged_read(
    mcp_client: fastmcp.Client[FastMCPTransport],
) -> None:
    tools = await mcp_client.list_tools()

    untagged = [
        tool.name
        for tool in tools
        if tool.meta is None or READ not in tool.meta["fastmcp"]["tags"]
    ]
    assert untagged == []


async def test_every_tool_is_annotated_as_a_closed_world_read(
    mcp_client: fastmcp.Client[FastMCPTransport],
) -> None:
    tools = await mcp_client.list_tools()

    closed_world_read = ToolAnnotations(read_only_hint=True, open_world_hint=False)
    assert [tool.name for tool in tools if tool.annotations != closed_world_read] == []


async def test_no_tool_exposes_the_paperless_client(
    mcp_client: fastmcp.Client[FastMCPTransport],
) -> None:
    tools = await mcp_client.list_tools()

    exposed = [
        tool.name for tool in tools if "client" in tool.input_schema["properties"]
    ]
    assert exposed == []


async def test_document_resources_are_titled_tagged_and_annotated(
    mcp_client: fastmcp.Client[FastMCPTransport],
) -> None:
    templates = await mcp_client.list_resource_templates()

    declared = {
        template.uri_template: (
            template.title,
            READ in (template.meta or {}).get("fastmcp", {}).get("tags", []),
            template.annotations,
        )
        for template in templates
    }
    everyone = Annotations(audience=["user", "assistant"])
    assert declared == {
        "paperless://documents/{document_id}": ("Document text", True, everyone),
        "paperless://documents/{document_id}/thumbnail": (
            "Document thumbnail",
            True,
            everyone,
        ),
        "paperless://documents/{document_id}/notes": ("Document notes", True, everyone),
    }


async def test_parameter_descriptions_carry_no_docstring_indentation(
    mcp_client: fastmcp.Client[FastMCPTransport],
) -> None:
    """A wrapped Args line needs a 4-space hanging indent.  Aligned
    indentation survives FastMCP's docstring parsing and reaches the model."""
    tools = await mcp_client.list_tools()

    indented = [
        f"{tool.name}.{name}: {schema['description']!r}"
        for tool in tools
        for name, schema in tool.input_schema["properties"].items()
        if "\n " in schema.get("description", "")
    ]
    assert indented == []


async def test_every_parameter_is_described(
    mcp_client: fastmcp.Client[FastMCPTransport],
) -> None:
    tools = await mcp_client.list_tools()

    undescribed = [
        f"{tool.name}.{name}"
        for tool in tools
        for name, schema in tool.input_schema["properties"].items()
        if not schema.get("description")
    ]
    assert undescribed == []

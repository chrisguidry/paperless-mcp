"""Tests for search_documents's custom_field_query filter."""

import json
import re

import fastmcp
import pytest
import respx
from conftest import paginated
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError


def condition(field: int | str, operator: str, value: object) -> dict[str, object]:
    return {"field": field, "operator": operator, "value": value}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        pytest.param(
            {"conditions": [condition("Amount", "gt", 100)]},
            ["AND", [["Amount", "gt", 100]]],
            id="comparison",
        ),
        pytest.param(
            {"conditions": [condition(6, "lte", "2027-01-01")]},
            ["AND", [[6, "lte", "2027-01-01"]]],
            id="field-by-id",
        ),
        pytest.param(
            {"conditions": [condition("Paid", "exact", True)]},
            ["AND", [["Paid", "exact", True]]],
            id="boolean-value",
        ),
        pytest.param(
            {"conditions": [condition("Total", "gte", 12.5)]},
            ["AND", [["Total", "gte", 12.5]]],
            id="decimal-value",
        ),
        pytest.param(
            {"conditions": [condition("Vendor", "icontains", "hardware")]},
            ["AND", [["Vendor", "icontains", "hardware"]]],
            id="substring",
        ),
        pytest.param(
            {"conditions": [condition("Due", "range", ["2026-08-01", "2026-09-01"])]},
            ["AND", [["Due", "range", ["2026-08-01", "2026-09-01"]]]],
            id="range",
        ),
        pytest.param(
            {"conditions": [condition("Animal", "in", ["cat", "dog"])]},
            ["AND", [["Animal", "in", ["cat", "dog"]]]],
            id="membership",
        ),
        pytest.param(
            {"conditions": [condition("Address", "isnull", True)]},
            ["AND", [["Address", "isnull", True]]],
            id="isnull",
        ),
        pytest.param(
            {"conditions": [condition("Warranty", "exists", False)]},
            ["AND", [["Warranty", "exists", False]]],
            id="exists",
        ),
        pytest.param(
            {"conditions": [condition("References", "contains", [3, 7])]},
            ["AND", [["References", "contains", [3, 7]]]],
            id="document-links",
        ),
        pytest.param(
            {
                "match": "all",
                "conditions": [
                    condition("Amount", "gt", 100),
                    condition("Paid", "exact", False),
                ],
            },
            ["AND", [["Amount", "gt", 100], ["Paid", "exact", False]]],
            id="all-conditions",
        ),
        pytest.param(
            {
                "match": "any",
                "conditions": [
                    condition("Address", "isnull", True),
                    condition("Address", "exact", ""),
                ],
            },
            ["OR", [["Address", "isnull", True], ["Address", "exact", ""]]],
            id="any-condition",
        ),
    ],
)
async def test_sends_paperless_custom_field_query_json(
    mcp_client: fastmcp.Client[FastMCPTransport],
    respx_mock: respx.MockRouter,
    query: dict[str, object],
    expected: list[object],
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(json=paginated([]))

    await mcp_client.call_tool("search_documents", {"custom_field_query": query})

    params = dict(respx_mock.calls.last.request.url.params)
    assert json.loads(params["custom_field_query"]) == expected


async def test_combines_custom_field_query_with_other_filters(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(json=paginated([]))

    await mcp_client.call_tool(
        "search_documents",
        {
            "query": "invoice",
            "correspondent_id": 3,
            "custom_field_query": {"conditions": [condition("Amount", "gt", 100)]},
        },
    )

    params = dict(respx_mock.calls.last.request.url.params)
    assert params["query"] == "invoice"
    assert params["correspondent__id"] == "3"
    assert "custom_field_query" in params


@pytest.mark.parametrize(
    "query",
    [
        pytest.param({"conditions": []}, id="no-conditions"),
        pytest.param(
            {"conditions": [condition("Amount", "gt", 1)] * 21},
            id="more-than-paperless-allows",
        ),
        pytest.param(
            {"match": "none", "conditions": [condition("Amount", "gt", 1)]},
            id="unknown-match",
        ),
        pytest.param(
            {"conditions": [condition("Amount", "regex", "1.*")]},
            id="unknown-operator",
        ),
        pytest.param(
            {"conditions": [condition("Amount", "gt", [1, 2])]},
            id="comparison-with-a-list",
        ),
        pytest.param(
            {"conditions": [condition("Animal", "in", [])]},
            id="empty-membership",
        ),
        pytest.param(
            {"conditions": [condition("Due", "range", ["2026-08-01"])]},
            id="range-with-one-bound",
        ),
        pytest.param(
            {"conditions": [condition("Warranty", "exists", "maybe")]},
            id="exists-without-a-boolean",
        ),
        pytest.param(
            {"conditions": [condition("References", "contains", ["three"])]},
            id="document-links-without-ids",
        ),
    ],
)
async def test_rejects_malformed_custom_field_queries(
    mcp_client: fastmcp.Client[FastMCPTransport],
    respx_mock: respx.MockRouter,
    query: dict[str, object],
) -> None:
    with pytest.raises(ToolError):
        await mcp_client.call_tool("search_documents", {"custom_field_query": query})

    assert not respx_mock.calls


async def test_reports_paperless_objections_to_a_custom_field_query(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(
        400,
        json={
            "custom_field_query": {
                "1": {"0": {"0": ["'Nope' is not a valid custom field."]}}
            }
        },
    )

    message = "Paperless returned 400: custom_field_query: 'Nope' is not a valid"
    with pytest.raises(ToolError, match=re.escape(message)):
        await mcp_client.call_tool(
            "search_documents",
            {"custom_field_query": {"conditions": [condition("Nope", "gt", 1)]}},
        )

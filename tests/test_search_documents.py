"""Tests for the search_documents tool."""

import fastmcp
import pytest
import respx
from conftest import document_json, paginated
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError


async def test_searches_with_defaults(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(
        json=paginated([document_json()])
    )

    result = await mcp_client.call_tool("search_documents", {})

    params = respx_mock.calls.last.request.url.params
    assert dict(params) == {"page": "1", "page_size": "25"}

    assert result.structured_content is not None
    documents = result.structured_content["documents"]
    assert len(documents) == 1
    assert documents[0]["id"] == 1
    assert documents[0]["title"] == "Electric Bill"
    assert documents[0]["uri"] == "paperless://documents/1"
    assert documents[0]["tags"] == [1, 2]
    assert documents[0]["search_hit"] is None

    pagination = result.structured_content["pagination"]
    assert pagination == {
        "total_count": 1,
        "page": 1,
        "page_size": 25,
        "has_more": False,
    }


async def test_maps_all_filters_to_api_parameters(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(json=paginated([]))

    await mcp_client.call_tool(
        "search_documents",
        {
            "query": "electric",
            "title_contains": "bill",
            "content_contains": "june",
            "tag_ids": [1, 2],
            "correspondent_id": 3,
            "document_type_id": 4,
            "storage_path_id": 5,
            "created_after": "2026-01-01",
            "created_before": "2026-06-30",
            "added_after": "2026-01-01T00:00:00Z",
            "added_before": "2026-07-01T00:00:00Z",
            "ordering": "-created",
            "page": 2,
            "page_size": 10,
        },
    )

    params = dict(respx_mock.calls.last.request.url.params)
    assert params["query"] == "electric"
    assert params["title__icontains"] == "bill"
    assert params["content__icontains"] == "june"
    assert params["tags__id__all"] == "1,2"
    assert params["correspondent__id"] == "3"
    assert params["document_type__id"] == "4"
    assert params["storage_path__id"] == "5"
    assert params["created__gte"] == "2026-01-01"
    assert params["created__lte"] == "2026-06-30"
    assert params["added__gte"] == "2026-01-01T00:00:00+00:00"
    assert params["added__lte"] == "2026-07-01T00:00:00+00:00"
    assert params["ordering"] == "-created"
    assert params["page"] == "2"
    assert params["page_size"] == "10"


# Each structured filter maps to the exact query parameter paperless-ngx's
# django-filter DocumentFilterSet registers.  The `__exact` lookup is the
# implicit default, so its filters have no `__exact` suffix (e.g.
# `correspondent__id`, not `correspondent__id__exact`); sending the suffixed
# name is silently ignored by the API.
FILTER_PARAMS = [
    ({"title_contains": "bill"}, "title__icontains", "bill"),
    ({"content_contains": "june"}, "content__icontains", "june"),
    ({"tag_ids": [1, 2]}, "tags__id__all", "1,2"),
    ({"any_tag_ids": [1, 2]}, "tags__id__in", "1,2"),
    ({"excluded_tag_ids": [8, 9]}, "tags__id__none", "8,9"),
    ({"correspondent_id": 3}, "correspondent__id", "3"),
    ({"document_type_id": 4}, "document_type__id", "4"),
    ({"storage_path_id": 5}, "storage_path__id", "5"),
    ({"created_after": "2026-01-01"}, "created__gte", "2026-01-01"),
    ({"created_before": "2026-06-30"}, "created__lte", "2026-06-30"),
    (
        {"added_after": "2026-01-01T00:00:00Z"},
        "added__gte",
        "2026-01-01T00:00:00+00:00",
    ),
    (
        {"added_before": "2026-07-01T00:00:00Z"},
        "added__lte",
        "2026-07-01T00:00:00+00:00",
    ),
    ({"more_like_document_id": 7}, "more_like_id", "7"),
    ({"has_correspondent": True}, "correspondent__isnull", "false"),
    ({"has_correspondent": False}, "correspondent__isnull", "true"),
    ({"has_document_type": True}, "document_type__isnull", "false"),
    ({"has_document_type": False}, "document_type__isnull", "true"),
    ({"has_storage_path": True}, "storage_path__isnull", "false"),
    ({"has_storage_path": False}, "storage_path__isnull", "true"),
    ({"is_in_inbox": True}, "is_in_inbox", "true"),
    ({"is_in_inbox": False}, "is_in_inbox", "false"),
]


@pytest.mark.parametrize(("arguments", "param", "expected"), FILTER_PARAMS)
async def test_maps_each_filter_to_its_api_parameter(
    mcp_client: fastmcp.Client[FastMCPTransport],
    respx_mock: respx.MockRouter,
    arguments: dict[str, object],
    param: str,
    expected: str,
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(json=paginated([]))

    await mcp_client.call_tool("search_documents", arguments)

    params = dict(respx_mock.calls.last.request.url.params)
    assert params[param] == expected


@pytest.mark.parametrize(("arguments", "param", "expected"), FILTER_PARAMS)
async def test_keeps_each_filter_when_ordering_is_present(
    mcp_client: fastmcp.Client[FastMCPTransport],
    respx_mock: respx.MockRouter,
    arguments: dict[str, object],
    param: str,
    expected: str,
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(json=paginated([]))

    await mcp_client.call_tool("search_documents", {**arguments, "ordering": "created"})

    params = dict(respx_mock.calls.last.request.url.params)
    assert params[param] == expected
    assert params["ordering"] == "created"


async def test_combines_similar_documents_with_other_filters(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(json=paginated([]))

    await mcp_client.call_tool(
        "search_documents",
        {"more_like_document_id": 7, "correspondent_id": 3, "has_document_type": False},
    )

    params = dict(respx_mock.calls.last.request.url.params)
    assert params["more_like_id"] == "7"
    assert params["correspondent__id"] == "3"
    assert params["document_type__isnull"] == "true"


async def test_refuses_a_query_with_similar_documents(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    with pytest.raises(
        ToolError, match="cannot combine query and more_like_document_id"
    ):
        await mcp_client.call_tool(
            "search_documents", {"query": "electric", "more_like_document_id": 7}
        )

    assert not respx_mock.calls


async def test_ignores_empty_tag_list(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(json=paginated([]))

    await mcp_client.call_tool("search_documents", {"tag_ids": []})

    params = dict(respx_mock.calls.last.request.url.params)
    assert "tags__id__all" not in params


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param({"ordering": "original_filename"}, id="unsortable-field"),
        pytest.param({"page": 0}, id="page-zero"),
        pytest.param({"page_size": 0}, id="empty-page"),
    ],
)
async def test_rejects_arguments_paperless_would_ignore_or_refuse(
    mcp_client: fastmcp.Client[FastMCPTransport],
    respx_mock: respx.MockRouter,
    arguments: dict[str, object],
) -> None:
    with pytest.raises(ToolError):
        await mcp_client.call_tool("search_documents", arguments)

    assert not respx_mock.calls


async def test_returns_search_hits_for_full_text_queries(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    hit = {"score": 0.75, "rank": 1, "highlights": "your <span>electric</span> bill"}
    respx_mock.get("http://paperless.test/api/documents/").respond(
        json=paginated([document_json(__search_hit__=hit)])
    )

    result = await mcp_client.call_tool("search_documents", {"query": "electric"})

    assert result.structured_content is not None
    search_hit = result.structured_content["documents"][0]["search_hit"]
    assert search_hit == hit


async def test_reports_when_more_pages_exist(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(
        json=paginated(
            [document_json()],
            count=100,
            next_url="http://paperless.test/api/documents/?page=2",
        )
    )

    result = await mcp_client.call_tool("search_documents", {})

    assert result.structured_content is not None
    pagination = result.structured_content["pagination"]
    assert pagination["total_count"] == 100
    assert pagination["has_more"] is True


async def test_includes_web_url(
    mcp_client: fastmcp.Client[FastMCPTransport], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("http://paperless.test/api/documents/").respond(
        json=paginated([document_json(id=7)])
    )

    result = await mcp_client.call_tool("search_documents", {})

    assert result.structured_content is not None
    documents = result.structured_content["documents"]
    assert documents[0]["web_url"] == "http://paperless.test/documents/7"

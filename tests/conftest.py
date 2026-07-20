"""Shared fixtures and paperless-ngx API response factories."""

from collections.abc import AsyncGenerator
from typing import Any

import fastmcp
import pytest
from fastmcp.client.transports import FastMCPTransport

import server


@pytest.fixture
async def mcp_client() -> AsyncGenerator[fastmcp.Client[FastMCPTransport]]:
    async with fastmcp.Client(server.mcp) as client:
        yield client


def paginated(
    results: list[dict[str, Any]],
    count: int | None = None,
    next_url: str | None = None,
) -> dict[str, Any]:
    return {
        "count": len(results) if count is None else count,
        "next": next_url,
        "previous": None,
        "results": results,
        "all": [item["id"] for item in results],
    }


def document_json(**overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "id": 1,
        "correspondent": 3,
        "document_type": 4,
        "storage_path": None,
        "title": "Electric Bill",
        "content": "Your electric service statement for June 2026.",
        "tags": [1, 2],
        "created": "2026-06-01",
        "modified": "2026-06-02T10:00:00Z",
        "added": "2026-06-02T09:30:00Z",
        "archive_serial_number": None,
        "original_file_name": "electric-bill.pdf",
        "archived_file_name": "0000001.pdf",
        "page_count": 2,
        "mime_type": "application/pdf",
        "notes": [],
        "custom_fields": [],
        "owner": 1,
    }
    return document | overrides


def tag_json(**overrides: Any) -> dict[str, Any]:
    tag: dict[str, Any] = {
        "id": 1,
        "slug": "utilities",
        "name": "Utilities",
        "color": "#00ff00",
        "text_color": "#000000",
        "is_inbox_tag": False,
        "document_count": 12,
    }
    return tag | overrides


def correspondent_json(**overrides: Any) -> dict[str, Any]:
    correspondent: dict[str, Any] = {
        "id": 3,
        "slug": "electric-company",
        "name": "Electric Company",
        "document_count": 24,
        "last_correspondence": "2026-06-02T09:30:00Z",
    }
    return correspondent | overrides


def document_type_json(**overrides: Any) -> dict[str, Any]:
    document_type: dict[str, Any] = {
        "id": 4,
        "slug": "bill",
        "name": "Bill",
        "document_count": 40,
    }
    return document_type | overrides


def storage_path_json(**overrides: Any) -> dict[str, Any]:
    storage_path: dict[str, Any] = {
        "id": 5,
        "slug": "household",
        "name": "Household",
        "path": "household/{created_year}",
        "document_count": 7,
    }
    return storage_path | overrides


def custom_field_json(**overrides: Any) -> dict[str, Any]:
    custom_field: dict[str, Any] = {
        "id": 6,
        "name": "Warranty Expires",
        "data_type": "date",
    }
    return custom_field | overrides

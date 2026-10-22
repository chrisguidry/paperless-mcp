"""A thin async client for the paperless-ngx REST API."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

import httpx

# Full-text search over a large archive, and the text of a long document, can
# take Paperless longer than httpx's default of five seconds.
REQUEST_TIMEOUT_SECONDS = 30.0


class PaperlessNotConfigured(Exception):
    """PAPERLESS_URL or PAPERLESS_TOKEN is missing from the environment."""


class PaperlessClient:
    """Read-only access to a paperless-ngx instance, authenticated by token."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Token {token}",
                "Accept": "application/json; version=9",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get_json(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        response = await self._http.get(path, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def list_documents(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get_json("/api/documents/", params)

    async def get_document(self, document_id: int) -> dict[str, Any]:
        return await self._get_json(f"/api/documents/{document_id}/")

    async def get_thumbnail(self, document_id: int) -> bytes:
        response = await self._http.get(f"/api/documents/{document_id}/thumb/")
        response.raise_for_status()
        return response.content

    async def list_tags(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get_json("/api/tags/", params)

    async def list_correspondents(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get_json("/api/correspondents/", params)

    async def list_document_types(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get_json("/api/document_types/", params)

    async def list_storage_paths(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get_json("/api/storage_paths/", params)

    async def list_custom_fields(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get_json("/api/custom_fields/", params)


@asynccontextmanager
async def paperless_client() -> AsyncIterator[PaperlessClient]:
    """Build the client for the archive this server is configured for.

    Tools and resources receive it through FastMCP's Shared dependency, so the
    server keeps one connection pool for its whole lifetime and closes it at
    shutdown.
    """
    try:
        base_url = os.environ["PAPERLESS_URL"]
        token = os.environ["PAPERLESS_TOKEN"]
    except KeyError as missing:
        raise PaperlessNotConfigured(f"{missing.args[0]} is not set") from None

    client = PaperlessClient(base_url=base_url, token=token)
    try:
        yield client
    finally:
        await client.aclose()


def query_params(**values: Any) -> dict[str, Any]:
    """Build query parameters, dropping unset values and formatting the rest.

    Paperless reads a list of IDs as one comma-separated value, and dates in
    ISO 8601 form.
    """
    params: dict[str, Any] = {}
    for name, value in values.items():
        if value is None or value == []:
            continue
        if isinstance(value, list):
            value = ",".join(str(item) for item in value)
        elif isinstance(value, date):
            value = value.isoformat()
        params[name] = value
    return params

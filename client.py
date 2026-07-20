"""A thin async client for the paperless-ngx REST API."""

from typing import Any

import httpx


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
        )

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

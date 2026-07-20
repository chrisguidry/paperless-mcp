"""Read-only MCP server for a paperless-ngx document archive."""

import os
from datetime import date, datetime
from typing import Any

from fastmcp import FastMCP
from fastmcp.resources import ResourceContent, ResourceResult

from client import PaperlessClient
from models import (
    Correspondent,
    CorrespondentsResponse,
    CustomField,
    CustomFieldsResponse,
    Document,
    DocumentSearchResponse,
    DocumentSummary,
    DocumentType,
    DocumentTypesResponse,
    Pagination,
    StoragePath,
    StoragePathsResponse,
    Tag,
    TagsResponse,
)

mcp: FastMCP[None] = FastMCP(
    name="Paperless",
    instructions="""Search and read documents in a paperless-ngx archive.

Start with search_documents for anything content- or metadata-related.  Use
the list_* tools to resolve tag, correspondent, document type, and storage
path names to the IDs that search_documents filters on.  Every document
result carries a `uri` — read it as an MCP resource to get the document's
full text.  This server is read-only and cannot modify the archive.""",
)

client = PaperlessClient(
    base_url=os.environ["PAPERLESS_URL"],
    token=os.environ["PAPERLESS_TOKEN"],
)


def _query_params(**values: Any) -> dict[str, Any]:
    """Build query parameters, dropping unset values and formatting the rest."""
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


@mcp.tool()
async def search_documents(
    query: str | None = None,
    title_contains: str | None = None,
    content_contains: str | None = None,
    tag_ids: list[int] | None = None,
    correspondent_id: int | None = None,
    document_type_id: int | None = None,
    storage_path_id: int | None = None,
    created_after: date | None = None,
    created_before: date | None = None,
    added_after: datetime | None = None,
    added_before: datetime | None = None,
    ordering: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> DocumentSearchResponse:
    """Search and filter documents in the archive.

    All parameters combine as AND conditions.  `query` is full-text search
    over document contents using whoosh syntax: plain terms ("electric bill"),
    boolean operators ("chase AND (mortgage OR escrow)"), field prefixes
    ("correspondent:university", "type:invoice", "tag:unpaid",
    "created:[2020 to 2023]"), and wildcards ("electr*").  Full-text results
    are ranked by relevance and include a search_hit with highlights.

    `tag_ids` matches documents carrying ALL of the given tags.  `ordering`
    sorts by one of: id, title, created, added, modified, original_filename,
    archive_serial_number (prefix with "-" for descending, e.g. "-created");
    it has no effect on full-text queries, which rank by relevance.

    Each result carries a `uri` — read it as an MCP resource for the
    document's full text, or call get_document for complete metadata.
    """
    params = _query_params(
        query=query,
        title__icontains=title_contains,
        content__icontains=content_contains,
        tags__id__all=tag_ids,
        correspondent__id__exact=correspondent_id,
        document_type__id__exact=document_type_id,
        storage_path__id__exact=storage_path_id,
        created__gte=created_after,
        created__lte=created_before,
        added__gte=added_after,
        added__lte=added_before,
        ordering=ordering,
        page=page,
        page_size=page_size,
    )
    data = await client.list_documents(params)
    return DocumentSearchResponse(
        documents=[DocumentSummary.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@mcp.tool()
async def get_document(document_id: int, include_content: bool = False) -> Document:
    """Get a single document's full metadata.

    The preferred way to read a document's text is its MCP resource at
    paperless://documents/{document_id}; pass include_content=True only if
    you cannot read MCP resources.
    """
    data = await client.get_document(document_id)
    if not include_content:
        data["content"] = None
    return Document.model_validate(data)


def _list_params(
    name_contains: str | None, page: int, page_size: int
) -> dict[str, Any]:
    return _query_params(name__icontains=name_contains, page=page, page_size=page_size)


@mcp.tool()
async def list_tags(
    name_contains: str | None = None, page: int = 1, page_size: int = 100
) -> TagsResponse:
    """List tags, optionally filtering by a case-insensitive name substring.

    Use the returned IDs with search_documents(tag_ids=[...]).
    """
    data = await client.list_tags(_list_params(name_contains, page, page_size))
    return TagsResponse(
        tags=[Tag.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@mcp.tool()
async def list_correspondents(
    name_contains: str | None = None, page: int = 1, page_size: int = 100
) -> CorrespondentsResponse:
    """List correspondents (who documents are from or to), optionally filtering
    by a case-insensitive name substring.

    Use the returned IDs with search_documents(correspondent_id=...).
    """
    data = await client.list_correspondents(
        _list_params(name_contains, page, page_size)
    )
    return CorrespondentsResponse(
        correspondents=[Correspondent.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@mcp.tool()
async def list_document_types(
    name_contains: str | None = None, page: int = 1, page_size: int = 100
) -> DocumentTypesResponse:
    """List document types (like invoice or receipt), optionally filtering by a
    case-insensitive name substring.

    Use the returned IDs with search_documents(document_type_id=...).
    """
    data = await client.list_document_types(
        _list_params(name_contains, page, page_size)
    )
    return DocumentTypesResponse(
        document_types=[DocumentType.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@mcp.tool()
async def list_storage_paths(
    name_contains: str | None = None, page: int = 1, page_size: int = 100
) -> StoragePathsResponse:
    """List storage paths (filing locations), optionally filtering by a
    case-insensitive name substring.

    Use the returned IDs with search_documents(storage_path_id=...).
    """
    data = await client.list_storage_paths(_list_params(name_contains, page, page_size))
    return StoragePathsResponse(
        storage_paths=[StoragePath.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@mcp.tool()
async def list_custom_fields(
    name_contains: str | None = None, page: int = 1, page_size: int = 100
) -> CustomFieldsResponse:
    """List custom fields defined in the archive, optionally filtering by a
    case-insensitive name substring."""
    data = await client.list_custom_fields(_list_params(name_contains, page, page_size))
    return CustomFieldsResponse(
        custom_fields=[CustomField.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@mcp.resource(
    "paperless://documents/{document_id}",
    name="document-content",
    description="The full text content of a document",
    mime_type="text/plain",
)
async def document_content(document_id: int) -> str:
    data = await client.get_document(document_id)
    content: str = data["content"] or ""
    return content


@mcp.resource(
    "paperless://documents/{document_id}/thumbnail",
    name="document-thumbnail",
    description="A thumbnail image of a document's first page",
    mime_type="image/webp",
)
async def document_thumbnail(document_id: int) -> ResourceResult:
    thumbnail = await client.get_thumbnail(document_id)
    return ResourceResult([ResourceContent(thumbnail, mime_type="image/webp")])


if __name__ == "__main__":
    mcp.run()

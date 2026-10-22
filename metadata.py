"""
Metadata: the tags, correspondents, document types, storage paths, and custom
fields that documents refer to by ID.

Each list tool resolves names to the IDs that search_documents filters on, and
resolves the IDs on a document back to names.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

from fastmcp.dependencies import Shared
from fastmcp.tools import tool
from pydantic import AliasPath, BaseModel, Field

from client import PaperlessClient, paperless_client, query_params
from effects import READ, READS
from pagination import PageNumber, PageSize, Pagination


class Tag(BaseModel):
    """A tag for organizing documents."""

    id: int
    name: str
    color: str | None = None
    is_inbox_tag: bool = False
    document_count: int = Field(description="Number of documents with this tag")


class Correspondent(BaseModel):
    """A person or organization that documents come from or go to."""

    id: int
    name: str
    document_count: int
    last_correspondence: date | None = Field(
        default=None, description="The date of the newest document from or to them"
    )


class DocumentType(BaseModel):
    """A kind of document, like an invoice or a receipt."""

    id: int
    name: str
    document_count: int


class StoragePath(BaseModel):
    """A filing location for documents within the archive."""

    id: int
    name: str
    path: str
    document_count: int


class SelectOption(BaseModel):
    """One choice of a select custom field."""

    id: str = Field(description="The value a document stores for this choice")
    label: str


class CustomField(BaseModel):
    """A user-defined field that documents may carry values for."""

    id: int
    name: str
    data_type: str = Field(
        description=(
            "One of string, longtext, url, date, boolean, integer, float, "
            "monetary, documentlink, or select"
        )
    )
    select_options: list[SelectOption] = Field(
        default_factory=list,
        validation_alias=AliasPath("extra_data", "select_options"),
        description="For a select field, the choices its values refer to by id",
    )


class TagsResponse(BaseModel):
    """One page of tags."""

    tags: list[Tag]
    pagination: Pagination


class CorrespondentsResponse(BaseModel):
    """One page of correspondents."""

    correspondents: list[Correspondent]
    pagination: Pagination


class DocumentTypesResponse(BaseModel):
    """One page of document types."""

    document_types: list[DocumentType]
    pagination: Pagination


class StoragePathsResponse(BaseModel):
    """One page of storage paths."""

    storage_paths: list[StoragePath]
    pagination: Pagination


class CustomFieldsResponse(BaseModel):
    """One page of custom fields."""

    custom_fields: list[CustomField]
    pagination: Pagination


def _list_params(
    name_contains: str | None, ids: list[int] | None, page: int, page_size: int
) -> dict[str, Any]:
    return query_params(
        name__icontains=name_contains, id__in=ids, page=page, page_size=page_size
    )


@tool(title="List tags", tags={"metadata", READ}, annotations=READS)
async def list_tags(
    name_contains: str | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 100,
    ids: list[int] | None = None,
    client: PaperlessClient = Shared(paperless_client),
) -> TagsResponse:
    """List tags.

    Use the returned IDs with search_documents(tag_ids=[...]).

    Args:
        name_contains: Case-insensitive substring of the name (default: none)
        page: Page number, starting at 1 (default: 1)
        page_size: Number of tags per page (default: 100)
        ids: Return only the tags with these IDs, such as the tags on a
            document (default: none)
    """
    data = await client.list_tags(_list_params(name_contains, ids, page, page_size))
    return TagsResponse(
        tags=[Tag.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@tool(title="List correspondents", tags={"metadata", READ}, annotations=READS)
async def list_correspondents(
    name_contains: str | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 100,
    ids: list[int] | None = None,
    client: PaperlessClient = Shared(paperless_client),
) -> CorrespondentsResponse:
    """List correspondents: the people and organizations that documents are
    from or to.

    Use the returned IDs with search_documents(correspondent_id=...).

    Args:
        name_contains: Case-insensitive substring of the name (default: none)
        page: Page number, starting at 1 (default: 1)
        page_size: Number of correspondents per page (default: 100)
        ids: Return only the correspondents with these IDs (default: none)
    """
    params = _list_params(name_contains, ids, page, page_size)
    # Paperless computes each correspondent's last_correspondence only when
    # the request asks for it.
    params["last_correspondence"] = "true"
    data = await client.list_correspondents(params)
    return CorrespondentsResponse(
        correspondents=[Correspondent.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@tool(title="List document types", tags={"metadata", READ}, annotations=READS)
async def list_document_types(
    name_contains: str | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 100,
    ids: list[int] | None = None,
    client: PaperlessClient = Shared(paperless_client),
) -> DocumentTypesResponse:
    """List document types, like invoice or receipt.

    Use the returned IDs with search_documents(document_type_id=...).

    Args:
        name_contains: Case-insensitive substring of the name (default: none)
        page: Page number, starting at 1 (default: 1)
        page_size: Number of document types per page (default: 100)
        ids: Return only the document types with these IDs (default: none)
    """
    data = await client.list_document_types(
        _list_params(name_contains, ids, page, page_size)
    )
    return DocumentTypesResponse(
        document_types=[DocumentType.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@tool(title="List storage paths", tags={"metadata", READ}, annotations=READS)
async def list_storage_paths(
    name_contains: str | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 100,
    ids: list[int] | None = None,
    client: PaperlessClient = Shared(paperless_client),
) -> StoragePathsResponse:
    """List storage paths: the filing locations of documents.

    Use the returned IDs with search_documents(storage_path_id=...).

    Args:
        name_contains: Case-insensitive substring of the name (default: none)
        page: Page number, starting at 1 (default: 1)
        page_size: Number of storage paths per page (default: 100)
        ids: Return only the storage paths with these IDs (default: none)
    """
    data = await client.list_storage_paths(
        _list_params(name_contains, ids, page, page_size)
    )
    return StoragePathsResponse(
        storage_paths=[StoragePath.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


@tool(title="List custom fields", tags={"metadata", READ}, annotations=READS)
async def list_custom_fields(
    name_contains: str | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 100,
    ids: list[int] | None = None,
    client: PaperlessClient = Shared(paperless_client),
) -> CustomFieldsResponse:
    """List the custom fields defined in the archive.

    get_document returns a document's custom field values by field ID.  A
    select field's value is the id of one of the field's select_options.
    Search custom field values with search_documents, using a query like
    "custom_fields.value:overdue".

    Args:
        name_contains: Case-insensitive substring of the name (default: none)
        page: Page number, starting at 1 (default: 1)
        page_size: Number of custom fields per page (default: 100)
        ids: Return only the custom fields with these IDs (default: none)
    """
    data = await client.list_custom_fields(
        _list_params(name_contains, ids, page, page_size)
    )
    return CustomFieldsResponse(
        custom_fields=[CustomField.model_validate(item) for item in data["results"]],
        pagination=Pagination.from_api(data, page, page_size),
    )


TOOLS: list[Callable[..., object]] = [
    list_tags,
    list_correspondents,
    list_document_types,
    list_storage_paths,
    list_custom_fields,
]

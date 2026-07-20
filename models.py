"""Response models for the paperless-ngx MCP server."""

from datetime import date, datetime
from typing import Any, Self

from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    computed_field,
    model_validator,
)


class Pagination(BaseModel):
    """Where a page of results sits within the full result set."""

    total_count: int = Field(description="Total number of matching items")
    page: int = Field(description="The current page number, starting at 1")
    page_size: int = Field(description="Number of items requested per page")
    has_more: bool = Field(description="Whether another page of results exists")

    @classmethod
    def from_api(cls, data: dict[str, Any], page: int, page_size: int) -> Self:
        return cls(
            total_count=data["count"],
            page=page,
            page_size=page_size,
            has_more=data["next"] is not None,
        )


class SearchHit(BaseModel):
    """Relevance details for a document matched by a full-text query."""

    score: float | None = Field(
        default=None, description="Relative quality of the match"
    )
    rank: int | None = Field(
        default=None, description="Position in the ranked results, starting at 0"
    )
    highlights: str | None = Field(
        default=None,
        description="Content excerpt with matching terms wrapped in <span> tags",
    )


class DocumentSummary(BaseModel):
    """A document's core metadata, without its full text content."""

    id: int
    title: str
    created: date = Field(description="The date on the document itself")
    added: datetime = Field(description="When the document entered the archive")
    correspondent: int | None = Field(
        description="Correspondent ID, resolvable with list_correspondents"
    )
    document_type: int | None = Field(
        description="Document type ID, resolvable with list_document_types"
    )
    storage_path: int | None = Field(
        description="Storage path ID, resolvable with list_storage_paths"
    )
    tags: list[int] = Field(description="Tag IDs, resolvable with list_tags")
    archive_serial_number: int | None = None
    original_file_name: str | None = None
    page_count: int | None = None
    mime_type: str | None = None
    search_hit: SearchHit | None = Field(
        default=None,
        validation_alias="__search_hit__",
        description="Present only on results of a full-text query",
    )
    web_url: str | None = Field(
        default=None,
        description="Link to open this document in the Paperless web UI",
    )

    @model_validator(mode="before")
    @classmethod
    def _resolve_web_url(cls, data: Any, info: ValidationInfo) -> Any:
        base_url = (info.context or {}).get("base_url")
        if base_url and isinstance(data, dict) and data.get("id") is not None:
            data = {**data, "web_url": f"{base_url}/documents/{data['id']}"}
        return data

    @computed_field(  # type: ignore[prop-decorator]
        description="MCP resource URI for the document's full text content"
    )
    @property
    def uri(self) -> str:
        return f"paperless://documents/{self.id}"


class Note(BaseModel):
    """A note attached to a document."""

    id: int
    note: str
    created: datetime


class CustomFieldValue(BaseModel):
    """A custom field's value on a document."""

    field: int = Field(
        description="Custom field ID, resolvable with list_custom_fields"
    )
    value: Any = None


class Document(DocumentSummary):
    """A document's full metadata."""

    modified: datetime
    content: str | None = Field(
        default=None,
        description="Full text content, included only when requested",
    )
    notes: list[Note] = Field(default_factory=list)
    custom_fields: list[CustomFieldValue] = Field(default_factory=list)


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
    last_correspondence: datetime | None = None


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


class CustomField(BaseModel):
    """A user-defined field that documents may carry values for."""

    id: int
    name: str
    data_type: str


class DocumentSearchResponse(BaseModel):
    """One page of documents matching a search."""

    documents: list[DocumentSummary]
    pagination: Pagination


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

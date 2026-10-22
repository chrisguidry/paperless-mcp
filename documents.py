"""
Documents: searching the archive, reading one document's metadata, and reading
its text, thumbnail, and notes as MCP resources.
"""

from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Literal

from fastmcp.dependencies import Shared
from fastmcp.exceptions import ToolError
from fastmcp.resources import ResourceContent, ResourceResult, resource
from fastmcp.tools import tool
from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationInfo,
    computed_field,
    model_validator,
)

from client import PaperlessClient, paperless_client, query_params
from custom_field_query import CustomFieldQuery
from effects import FOR_USER_AND_ASSISTANT, READ, READS
from pagination import PageNumber, PageSize, Pagination

# The fields Paperless can sort documents by.  It ignores any other value
# without an error, so the schema offers only these.
DocumentOrdering = Literal[
    "id",
    "-id",
    "title",
    "-title",
    "correspondent__name",
    "-correspondent__name",
    "document_type__name",
    "-document_type__name",
    "storage_path__name",
    "-storage_path__name",
    "created",
    "-created",
    "added",
    "-added",
    "modified",
    "-modified",
    "archive_serial_number",
    "-archive_serial_number",
    "num_notes",
    "-num_notes",
    "page_count",
    "-page_count",
]


class SearchHit(BaseModel):
    """Relevance details for a document matched by a full-text query."""

    score: float | None = Field(
        default=None, description="Relative quality of the match"
    )
    rank: int | None = Field(
        default=None, description="Position of the document in the ranked results"
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
        description="Correspondent ID, resolvable with list_correspondents(ids=[...])"
    )
    document_type: int | None = Field(
        description="Document type ID, resolvable with list_document_types(ids=[...])"
    )
    storage_path: int | None = Field(
        description="Storage path ID, resolvable with list_storage_paths(ids=[...])"
    )
    tags: list[int] = Field(description="Tag IDs, resolvable with list_tags(ids=[...])")
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


NOTES = TypeAdapter(list[Note])


class CustomFieldValue(BaseModel):
    """A custom field's value on a document."""

    field: int = Field(
        description="Custom field ID, resolvable with list_custom_fields(ids=[...])"
    )
    value: Any = Field(
        default=None,
        description=(
            "The value, typed by the field's data_type.  A select field's value "
            "is the id of one of the field's select_options, a documentlink "
            "field's value is a list of document IDs, and a monetary value is a "
            'currency code and an amount, like "USD12.50"'
        ),
    )


class Document(DocumentSummary):
    """A document's full metadata."""

    modified: datetime
    content: str | None = Field(
        default=None,
        description="Full text content, included only when requested",
    )
    notes: list[Note] = Field(default_factory=list)
    custom_fields: list[CustomFieldValue] = Field(default_factory=list)


class DocumentSearchResponse(BaseModel):
    """One page of documents matching a search."""

    documents: list[DocumentSummary]
    pagination: Pagination


def _is_missing(has: bool | None) -> bool | None:
    """Turn a has_* filter into the value of Paperless's __isnull filter."""
    return None if has is None else not has


@tool(title="Search documents", tags={"documents", READ}, annotations=READS)
async def search_documents(
    query: str | None = None,
    more_like_document_id: int | None = None,
    title_contains: str | None = None,
    content_contains: str | None = None,
    tag_ids: list[int] | None = None,
    any_tag_ids: list[int] | None = None,
    excluded_tag_ids: list[int] | None = None,
    has_tags: bool | None = None,
    is_in_inbox: bool | None = None,
    correspondent_id: int | None = None,
    has_correspondent: bool | None = None,
    document_type_id: int | None = None,
    has_document_type: bool | None = None,
    storage_path_id: int | None = None,
    has_storage_path: bool | None = None,
    custom_field_query: CustomFieldQuery | None = None,
    created_after: date | None = None,
    created_before: date | None = None,
    added_after: datetime | None = None,
    added_before: datetime | None = None,
    ordering: DocumentOrdering | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 25,
    client: PaperlessClient = Shared(paperless_client),
) -> DocumentSearchResponse:
    """Search and filter documents in the archive.

    All parameters combine as AND conditions, except that `query` and
    `more_like_document_id` cannot be used together.  `query` is full-text
    search over document contents using tantivy syntax: plain terms ("electric
    bill"), boolean operators ("chase AND (mortgage OR escrow)"), field
    prefixes ("correspondent:university", "type:invoice", "tag:unpaid",
    "created:[2020 to 2023]"), and wildcards ("electr*").  Notes and custom
    fields are structured fields with dotted paths: "notes.note:reimbursed",
    "custom_fields.value:overdue", "custom_fields.name:warranty".  Plain terms
    do NOT match them, only titles and content.  Full-text results include a
    search_hit with highlights.

    `more_like_document_id` finds documents whose text is similar to one
    document's, ranked by similarity in search_hit.rank.  The results leave
    out that document itself, and the other filters narrow them.  Leave
    `ordering` unset to keep the ranking.

    To find unfiled documents, use is_in_inbox=true, or has_tags,
    has_correspondent, has_document_type, or has_storage_path set to false.

    `custom_field_query` compares custom field values, like "Amount over 100"
    or "Warranty Expires before 2027-01-01".  Every field type supports exact,
    in, exists, and isnull.  Date, integer, float, and monetary fields add gt,
    gte, lt, lte, and range.  String, URL, long text, and monetary fields add
    icontains, istartswith, and iendswith.  Document link fields add contains.
    Paperless refuses an operator that the field's type does not support.

    Each result carries a `uri`, which you can read as an MCP resource for the
    document's full text, and a `web_url` that links to the document in the
    Paperless web UI.  Read paperless://documents/{id}/notes for a document's
    notes, or call get_document for its notes and custom field values.

    Args:
        query: Full-text query in tantivy syntax, described above (default: none)
        more_like_document_id: Match documents similar to the document with this
            ID.  Cannot be combined with query (default: none)
        title_contains: Case-insensitive substring of the title (default: none)
        content_contains: Case-insensitive substring of the text content
            (default: none)
        tag_ids: Match documents that have ALL of these tags (default: none)
        any_tag_ids: Match documents that have at least one of these tags
            (default: none)
        excluded_tag_ids: Match documents that have NONE of these tags
            (default: none)
        has_tags: true matches documents with at least one tag, and false
            matches documents with no tags (default: none)
        is_in_inbox: true matches documents with at least one inbox tag, and
            false matches documents with none (default: none)
        correspondent_id: Match documents from or to this correspondent
            (default: none)
        has_correspondent: true matches documents with a correspondent, and
            false matches documents without one (default: none)
        document_type_id: Match documents of this type (default: none)
        has_document_type: true matches documents with a document type, and
            false matches documents without one (default: none)
        storage_path_id: Match documents filed under this storage path
            (default: none)
        has_storage_path: true matches documents with a storage path, and
            false matches documents without one (default: none)
        custom_field_query: Conditions on custom field values, described
            above.  Name each field by its ID or exact name from
            list_custom_fields (default: none)
        created_after: Match documents dated on or after this date, as
            YYYY-MM-DD (default: none)
        created_before: Match documents dated on or before this date, as
            YYYY-MM-DD (default: none)
        added_after: Match documents added to the archive at or after this
            ISO 8601 date and time (default: none)
        added_before: Match documents added to the archive at or before this
            ISO 8601 date and time (default: none)
        ordering: Field to sort by.  Prefix it with "-" for descending order,
            like "-created".  Without it, full-text results are ranked by
            relevance (default: none)
        page: Page number, starting at 1 (default: 1)
        page_size: Number of documents per page (default: 25)
    """
    if query is not None and more_like_document_id is not None:
        raise ToolError(
            "Paperless cannot combine query and more_like_document_id.  "
            "Pass one of them, and narrow the results with the other filters."
        )
    params = query_params(
        query=query,
        more_like_id=more_like_document_id,
        title__icontains=title_contains,
        content__icontains=content_contains,
        tags__id__all=tag_ids,
        tags__id__in=any_tag_ids,
        tags__id__none=excluded_tag_ids,
        is_tagged=has_tags,
        is_in_inbox=is_in_inbox,
        correspondent__id=correspondent_id,
        correspondent__isnull=_is_missing(has_correspondent),
        document_type__id=document_type_id,
        document_type__isnull=_is_missing(has_document_type),
        storage_path__id=storage_path_id,
        storage_path__isnull=_is_missing(has_storage_path),
        custom_field_query=(
            custom_field_query.to_paperless() if custom_field_query else None
        ),
        created__gte=created_after,
        created__lte=created_before,
        added__gte=added_after,
        added__lte=added_before,
        ordering=ordering,
        page=page,
        page_size=page_size,
    )
    data = await client.list_documents(params)
    context = {"base_url": client.base_url}
    return DocumentSearchResponse(
        documents=[
            DocumentSummary.model_validate(item, context=context)
            for item in data["results"]
        ],
        pagination=Pagination.from_api(data, page, page_size),
    )


@tool(title="Get document", tags={"documents", READ}, annotations=READS)
async def get_document(
    document_id: int,
    include_content: bool = False,
    client: PaperlessClient = Shared(paperless_client),
) -> Document:
    """Get a single document's full metadata, with its notes and custom fields.

    The preferred way to read a document's text is its MCP resource at
    paperless://documents/{document_id}.

    Args:
        document_id: The document's ID, from search_documents (required)
        include_content: Whether to include the full text content.  Pass true
            only if you cannot read MCP resources (default: false)
    """
    data = await client.get_document(document_id)
    if not include_content:
        data["content"] = None
    return Document.model_validate(data, context={"base_url": client.base_url})


@resource(
    "paperless://documents/{document_id}",
    name="document-content",
    title="Document text",
    description="The full text content of a document",
    mime_type="text/plain",
    tags={"documents", READ},
    annotations=FOR_USER_AND_ASSISTANT,
)
async def document_content(
    document_id: int, client: PaperlessClient = Shared(paperless_client)
) -> str:
    data = await client.get_document(document_id)
    content: str = data["content"] or ""
    return content


@resource(
    "paperless://documents/{document_id}/thumbnail",
    name="document-thumbnail",
    title="Document thumbnail",
    description="A thumbnail image of a document's first page",
    mime_type="image/webp",
    tags={"documents", READ},
    annotations=FOR_USER_AND_ASSISTANT,
)
async def document_thumbnail(
    document_id: int, client: PaperlessClient = Shared(paperless_client)
) -> ResourceResult:
    thumbnail = await client.get_thumbnail(document_id)
    return ResourceResult([ResourceContent(thumbnail, mime_type="image/webp")])


@resource(
    "paperless://documents/{document_id}/notes",
    name="document-notes",
    title="Document notes",
    description="The notes on a document, as a JSON list",
    mime_type="application/json",
    tags={"documents", READ},
    annotations=FOR_USER_AND_ASSISTANT,
)
async def document_notes(
    document_id: int, client: PaperlessClient = Shared(paperless_client)
) -> ResourceResult:
    notes = NOTES.validate_python(await client.get_notes(document_id))
    return ResourceResult(
        [ResourceContent(NOTES.dump_json(notes).decode(), mime_type="application/json")]
    )


TOOLS: list[Callable[..., object]] = [search_documents, get_document]
RESOURCES: list[Callable[..., object]] = [
    document_content,
    document_thumbnail,
    document_notes,
]

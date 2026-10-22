"""Read-only MCP server for a paperless-ngx document archive."""

from fastmcp import FastMCP

import documents
import metadata
from paperless_errors import PaperlessErrorMiddleware

INSTRUCTIONS = """Search and read documents in a paperless-ngx archive.

Start with search_documents for anything content- or metadata-related.  Use
the list_* tools to resolve tag, correspondent, document type, and storage
path names to the IDs that search_documents filters on, and to resolve the IDs
on a document back to names with their `ids` filter.

Every document result carries a `uri` and a `web_url`.  Read the `uri` as an
MCP resource to get the document's full text.  Give the `web_url` to the user
to open the document in Paperless.

A document's `created` date is the date on the document itself, and its
`added` date is when it entered the archive.  This server is read-only and
cannot modify the archive."""

mcp: FastMCP[None] = FastMCP(
    name="Paperless",
    instructions=INSTRUCTIONS,
    middleware=[PaperlessErrorMiddleware()],
    mask_error_details=True,
    tools=[*documents.TOOLS, *metadata.TOOLS],
)
for document_resource in documents.RESOURCES:
    mcp.add_resource(document_resource)


if __name__ == "__main__":
    mcp.run()

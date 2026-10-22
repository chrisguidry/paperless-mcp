# paperless-mcp

A read-only [MCP](https://modelcontextprotocol.io) server for your
[paperless-ngx](https://docs.paperless-ngx.com) document archive.  It lets an
AI assistant search your documents by full text, tags, correspondents, and
dates, and read the text of any document.  It cannot change or delete
anything.

## Setup

```bash
uv sync
```

You'll need an API token from your paperless-ngx instance: log in, open
your profile (the person icon in the top right), and copy or generate the
API token there.

The server is configured entirely through environment variables:

```bash
export PAPERLESS_URL=https://paperless.example.com
export PAPERLESS_TOKEN=your-api-token
```

## Connecting a client

For Claude Code:

```bash
claude mcp add paperless \
  -e PAPERLESS_URL=https://paperless.example.com \
  -e PAPERLESS_TOKEN=your-api-token \
  -- uv run --directory /path/to/paperless-mcp paperless-mcp
```

For Claude Desktop, add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "paperless": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/paperless-mcp", "paperless-mcp"],
      "env": {
        "PAPERLESS_URL": "https://paperless.example.com",
        "PAPERLESS_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Tools

| Tool | What it does |
| --- | --- |
| `search_documents` | Full-text search (tantivy syntax) plus filters for title, content, tags (all, any, or none of them), correspondent, document type, storage path, and dates |
| `get_document` | One document's full metadata, with its notes, custom field values, and optional inline text content |
| `list_tags` | Tags, filterable by name or IDs |
| `list_correspondents` | Correspondents with the date of their newest document, filterable by name or IDs |
| `list_document_types` | Document types, filterable by name or IDs |
| `list_storage_paths` | Storage paths, filterable by name or IDs |
| `list_custom_fields` | Custom field definitions with the options of select fields, filterable by name or IDs |

Every tool declares itself read-only to the client, with the MCP
`read_only_hint` annotation and a `read` tag.  The `ids` filter on the list
tools resolves the IDs on a document back to names.

Every document result includes a `uri` like `paperless://documents/42` that
can be read as an MCP resource, and a `web_url` that opens the document in the
Paperless web UI.

When Paperless refuses a request, the tool's error carries Paperless's own
explanation, such as `Paperless returned 404: No Document matches the given
query.`  Other unexpected errors reach the client without their details.  The
server gives up on a request to Paperless after 30 seconds.

## Resources

| Resource | Contents |
| --- | --- |
| `paperless://documents/{id}` | The document's full text |
| `paperless://documents/{id}/thumbnail` | A WebP thumbnail of the first page |

## Security

This server is read-only by construction: it only ever issues GET requests
to paperless-ngx, and it exposes no way to create, modify, or delete
documents.  It performs no authentication of its own.  Anyone who can reach
the running server can read whatever the configured token can read, so treat
the token accordingly and run the server close to where you use it.

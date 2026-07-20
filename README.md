# paperless-mcp

A read-only [MCP](https://modelcontextprotocol.io) server for your
[paperless-ngx](https://docs.paperless-ngx.com) document archive.  It lets an
AI assistant search your documents by full text, tags, correspondents, and
dates, and read the text of any document — without being able to change or
delete anything.

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
| `search_documents` | Full-text search (whoosh syntax) plus filters for title, content, tags, correspondent, document type, storage path, and dates |
| `get_document` | One document's full metadata, with optional inline text content |
| `list_tags` | Tags, filterable by name |
| `list_correspondents` | Correspondents, filterable by name |
| `list_document_types` | Document types, filterable by name |
| `list_storage_paths` | Storage paths, filterable by name |
| `list_custom_fields` | Custom field definitions |

Every document result includes a `uri` like `paperless://documents/42` that
can be read as an MCP resource.

## Resources

| Resource | Contents |
| --- | --- |
| `paperless://documents/{id}` | The document's full text |
| `paperless://documents/{id}/thumbnail` | A WebP thumbnail of the first page |

## Security

This server is read-only by construction: it only ever issues GET requests
to paperless-ngx, and it exposes no way to create, modify, or delete
documents.  It performs no authentication of its own — anyone who can reach
the running server can read whatever the configured token can read, so treat
the token accordingly and run the server close to where you use it.

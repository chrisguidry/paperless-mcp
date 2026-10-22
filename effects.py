"""
What each tool and resource does to the archive, declared the same way for all.

MCP clients read tool annotations to decide when to ask the user before a call.
This server only reads the archive, so every tool is read-only, and every tool
and resource carries the "read" tag.

Every tool works on one paperless-ngx archive and nothing else, so none of them
is "open world" in the MCP sense.
"""

from mcp.types import Annotations, ToolAnnotations

READ = "read"

# Only reads the archive.
READS = ToolAnnotations(read_only_hint=True, open_world_hint=False)

# A document's text and thumbnail are useful to the model, and a client can
# also show them to the user.
FOR_USER_AND_ASSISTANT = Annotations(audience=["user", "assistant"])

"""
Turning Paperless API errors into messages a model can act on.

The server masks the details of unexpected errors, so that a stack trace never
leaks internal state to the client.  A Paperless API error is different:
Paperless writes its error detail for the caller ("No Document matches the
given query."), and the model needs that detail to correct its next call.  This
middleware passes the detail through as a ToolError or ResourceError, which the
server never masks.

FastMCP masks an exception before middleware sees it, but it chains the
original exception as the masked error's cause, so that is where this looks.
"""

import logging

import httpx
import mcp.types as mt
from fastmcp.exceptions import ResourceError, ToolError
from fastmcp.resources import ResourceResult
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult

from client import REQUEST_TIMEOUT_SECONDS, PaperlessNotConfigured

logger = logging.getLogger(__name__)


def _messages(value: object) -> str:
    if isinstance(value, list):
        return " ".join(map(str, value))
    return str(value)


def describe_status_error(error: httpx.HTTPStatusError) -> str:
    """Describe a Paperless error response in one sentence, without the token."""
    response = error.response
    if response.status_code == 401:
        return "Paperless did not accept the token. Check PAPERLESS_TOKEN."

    try:
        body = response.json()
    except ValueError:
        body = None

    # Paperless answers with {"detail": "..."}, with {"field": ["...", ...]}
    # for invalid parameters, or with a bare list of messages.
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        detail = body["detail"]
    elif isinstance(body, dict):
        detail = "; ".join(
            f"{field}: {_messages(messages)}" for field, messages in body.items()
        )
    elif isinstance(body, list):
        detail = _messages(body)
    else:
        detail = response.reason_phrase
    return f"Paperless returned {response.status_code}: {detail}"


def describe(error: BaseException) -> str | None:
    """Describe an error the model can act on, or None for any other error."""
    if isinstance(error, PaperlessNotConfigured):
        return f"{error} in the server's environment."
    if isinstance(error, httpx.HTTPStatusError):
        return describe_status_error(error)
    if isinstance(error, httpx.TimeoutException):
        return f"Paperless did not respond within {REQUEST_TIMEOUT_SECONDS:g} seconds."
    if isinstance(error, httpx.TransportError):
        return "Could not connect to Paperless. Check PAPERLESS_URL."
    return None


def describe_cause(error: BaseException) -> str | None:
    """Describe the first error in a chain of causes that the model can act on.

    A failure while building the client reaches the middleware two causes
    deep, behind FastMCP's dependency resolution error.
    """
    cause = error.__cause__
    while cause is not None:
        description = describe(cause)
        if description is not None:
            return description
        cause = cause.__cause__
    return None


class PaperlessErrorMiddleware(Middleware):
    """Report Paperless errors from any tool or resource with their detail."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        try:
            return await call_next(context)
        except ToolError as error:
            description = describe_cause(error)
            if description is None:
                raise
            logger.warning("Paperless error in tool %s", context.message.name)
            raise ToolError(description) from error

    async def on_read_resource(
        self,
        context: MiddlewareContext[mt.ReadResourceRequestParams],
        call_next: CallNext[mt.ReadResourceRequestParams, ResourceResult],
    ) -> ResourceResult:
        try:
            return await call_next(context)
        except ResourceError as error:
            description = describe_cause(error)
            if description is None:
                raise
            logger.warning("Paperless error reading %s", context.message.uri)
            raise ResourceError(description) from error

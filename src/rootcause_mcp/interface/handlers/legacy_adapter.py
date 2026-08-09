"""
Legacy Handler Adapter.

Provides a unified `handle(tool_name, arguments)` interface for legacy handlers
that use individual `handle_*` methods.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from mcp.types import TextContent


class LegacyHandlerProtocol(Protocol):
    """Protocol for legacy handlers with individual handle_* methods."""

    pass


def create_dispatcher(handler: Any, method_map: dict[str, str]) -> callable:
    """
    Create a dispatcher function for legacy handlers.

    Args:
        handler: The legacy handler instance
        method_map: Mapping of tool_name → method_name

    Returns:
        Async dispatcher function

    Example:
        >>> hfacs_map = {
        ...     "rc_suggest_hfacs": "handle_suggest_hfacs",
        ...     "rc_confirm_classification": "handle_confirm_classification",
        ... }
        >>> dispatcher = create_dispatcher(hfacs_handlers, hfacs_map)
        >>> result = await dispatcher("rc_suggest_hfacs", {"description": "..."})
    """

    async def dispatch(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch tool call to appropriate handler method."""
        if tool_name not in method_map:
            raise ValueError(f"Unknown tool: {tool_name}")

        method_name = method_map[tool_name]
        method = getattr(handler, method_name, None)

        if method is None:
            raise AttributeError(f"Handler {handler.__class__.__name__} has no method {method_name}")

        # Call the method
        result = await method(arguments)

        # Convert Sequence[TextContent] to dict
        if isinstance(result, (list, tuple)):
            # Extract text from TextContent objects
            texts = []
            for item in result:
                if isinstance(item, TextContent):
                    texts.append(item.text)
                else:
                    texts.append(str(item))

            combined_text = "\n".join(texts)

            # Try to parse as JSON, otherwise return as text
            try:
                return json.loads(combined_text)
            except (json.JSONDecodeError, ValueError):
                return {"result": combined_text}

        # Already a dict
        return result

    return dispatch

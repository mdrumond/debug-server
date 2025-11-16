"""Application context helpers shared across routers."""

from dataclasses import dataclass
from typing import cast

from fastapi import Request, WebSocket

from debug_server.db import MetadataStore
from debug_server.api.streams import DebugBroker, LogManager


@dataclass(slots=True)
class AppContext:
    """Container for shared application dependencies."""

    metadata_store: MetadataStore
    log_manager: LogManager | None = None
    debug_broker: DebugBroker | None = None


def get_app_context(request: Request) -> AppContext:
    """Return the configured :class:`AppContext`."""

    context = getattr(request.app.state, "context", None)
    if context is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Application context missing")
    return cast(AppContext, context)


def get_websocket_context(websocket: WebSocket) -> AppContext:
    """Return the configured :class:`AppContext` from a WebSocket."""

    context = getattr(websocket.app.state, "context", None)
    if context is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Application context missing")
    return cast(AppContext, context)


__all__ = ["AppContext", "get_app_context", "get_websocket_context"]

"""Application context helpers shared across routers."""

from dataclasses import dataclass
from typing import cast

from fastapi import Request

from debug_server.db import MetadataStore


@dataclass(slots=True)
class AppContext:
    """Container for shared application dependencies."""

    metadata_store: MetadataStore


def get_app_context(request: Request) -> AppContext:
    """Return the configured :class:`AppContext`."""

    context = getattr(request.app.state, "context", None)
    if context is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Application context missing")
    return cast(AppContext, context)


__all__ = ["AppContext", "get_app_context"]

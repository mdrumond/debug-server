"""Custom FastAPI middleware for the server API."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from debug_server.db import AuthToken


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    """Emit structured audit logs for each HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("debug_server.api.audit")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        token: AuthToken | None = getattr(request.state, "token", None)
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration = time.perf_counter() - start
            self.logger.info(
                "api.request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code if response else None,
                    "duration_ms": round(duration * 1000, 3),
                    "token_id": token.id if token else None,
                    "token_name": token.name if token else None,
                },
            )


__all__ = ["AuditLoggerMiddleware"]

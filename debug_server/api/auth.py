# ruff: noqa: B008
"""Bearer-token authentication helpers for the FastAPI surface."""

from collections.abc import Sequence

from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPBearer

from debug_server.db import AuthToken

from .context import AppContext, get_app_context


class BearerTokenAuth:
    """FastAPI dependency that validates bearer tokens via the metadata store."""

    def __init__(self, scopes: Sequence[str] | None = None) -> None:
        self.required_scopes = set(scopes or [])
        self.scheme = HTTPBearer(auto_error=False)

    async def __call__(self, request: Request) -> AuthToken:
        credentials = await self.scheme(request)
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        context = get_app_context(request)
        token = context.metadata_store.authenticate(credentials.credentials)
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
            )
        if self.required_scopes and not _has_scopes(token, self.required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient token scope",
            )
        request.state.token = token
        return token


async def require_websocket_token(
    websocket: WebSocket,
    context: AppContext,
    *,
    scopes: Sequence[str] | None = None,
) -> AuthToken:
    """Authenticate a WebSocket upgrade using the same bearer flow."""

    authorization = websocket.headers.get("authorization")
    token_value = _extract_bearer_value(authorization)
    if token_value is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = context.metadata_store.authenticate(token_value)
    if token is None or (scopes and not _has_scopes(token, scopes)):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized WebSocket upgrade")
    return token


def current_token(
    request: Request, context: AppContext = Depends(get_app_context)
) -> AuthToken | None:
    """Return the authenticated token stored on the request."""

    _ = context  # unused but keeps dependency symmetrical
    return getattr(request.state, "token", None)


def _has_scopes(token: AuthToken, scopes: set[str] | Sequence[str]) -> bool:
    token_scopes = set(token.scopes or [])
    if "admin" in token_scopes:
        return True
    return set(scopes).issubset(token_scopes)


def _extract_bearer_value(header: str | None) -> str | None:
    if header is None:
        return None
    prefix = "bearer "
    if not header.lower().startswith(prefix):
        return None
    return header[len(prefix) :].strip()


__all__ = ["BearerTokenAuth", "current_token", "require_websocket_token"]

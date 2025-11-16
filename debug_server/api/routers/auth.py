# ruff: noqa: B008
"""Authentication and token management endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from debug_server.api.auth import BearerTokenAuth
from debug_server.api.context import AppContext, get_app_context
from debug_server.api.schemas import (
    APIMessage,
    TokenCreateRequest,
    TokenResponse,
    TokenSecretResponse,
    token_to_response,
)
from debug_server.db import AuthToken

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/tokens", response_model=TokenSecretResponse, status_code=status.HTTP_201_CREATED)
def create_token(
    payload: TokenCreateRequest,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["admin"])),
) -> TokenSecretResponse:
    expires_at = _compute_expiry(payload.expires_in)
    record, secret = context.metadata_store.create_token(
        name=payload.name,
        scopes=payload.scopes,
        expires_at=expires_at,
    )
    token = token_to_response(record)
    return TokenSecretResponse(**token.model_dump(), token=secret)


@router.get("/tokens", response_model=list[TokenResponse])
def list_tokens(
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["admin"])),
) -> list[TokenResponse]:
    return [token_to_response(token) for token in context.metadata_store.list_tokens()]


@router.delete("/tokens/{token_id}", response_model=APIMessage)
def revoke_token(
    token_id: int,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["admin"])),
) -> APIMessage:
    token = context.metadata_store.revoke_token(token_id)
    if token.revoked_at is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke token")
    return APIMessage(message="token revoked")


def _compute_expiry(expires_in: int | None) -> datetime | None:
    if expires_in is None:
        return None
    return datetime.now(UTC) + timedelta(seconds=expires_in)


__all__ = ["router"]

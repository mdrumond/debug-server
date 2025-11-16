# ruff: noqa: B008
"""Repository lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from debug_server.api.auth import BearerTokenAuth
from debug_server.api.context import AppContext, get_app_context
from debug_server.api.schemas import (
    RepositoryInitRequest,
    RepositoryResponse,
    repository_to_response,
)
from debug_server.db import AuthToken

router = APIRouter(prefix="/repository", tags=["repository"])


@router.post("/init", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def init_repository(
    payload: RepositoryInitRequest,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["admin"])),
) -> RepositoryResponse:
    repository = context.metadata_store.upsert_repository(
        name=payload.name,
        remote_url=payload.remote_url,
        default_branch=payload.default_branch,
        description=payload.description,
        settings=payload.settings,
    )
    return repository_to_response(repository)


@router.get("", response_model=list[RepositoryResponse])
def list_repositories(
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["sessions:read"])),
) -> list[RepositoryResponse]:
    return [repository_to_response(repo) for repo in context.metadata_store.list_repositories()]


@router.get("/{name}", response_model=RepositoryResponse)
def get_repository(
    name: str,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["sessions:read"])),
) -> RepositoryResponse:
    repository = context.metadata_store.get_repository_by_name(name)
    if repository is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repository_to_response(repository)

# ruff: noqa: B008
"""Session lifecycle endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse

from debug_server.api.auth import BearerTokenAuth
from debug_server.api.context import AppContext, get_app_context
from debug_server.api.schemas import (
    APIMessage,
    ArtifactResponse,
    SessionCreateRequest,
    SessionResponse,
    artifact_to_response,
    compute_patch_hash,
    session_to_response,
)
from debug_server.db import AuthToken, SessionStatus

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    context: AppContext = Depends(get_app_context),
    token: AuthToken = Depends(BearerTokenAuth(["sessions:write"])),
) -> SessionResponse:
    repository = context.metadata_store.get_repository_by_name(payload.repository)
    if repository is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Repository not initialized")
    expires_at = _compute_expiration(payload.expires_in)
    patch_hash = compute_patch_hash(payload.patch)
    session = context.metadata_store.create_session(
        repository_id=repository.id or 0,
        commit_sha=payload.commit_sha,
        worktree_id=None,
        requested_by=payload.requested_by or token.name,
        token_id=token.id,
        patch_hash=patch_hash,
        metadata=payload.metadata,
        expires_at=expires_at,
    )
    return session_to_response(session)


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["sessions:read"])),
) -> list[SessionResponse]:
    return [session_to_response(item) for item in context.metadata_store.list_sessions()]


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["sessions:read"])),
) -> SessionResponse:
    session = context.metadata_store.get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_to_response(session)


@router.delete("/{session_id}", response_model=APIMessage)
def cancel_session(
    session_id: str,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["sessions:write"])),
) -> APIMessage:
    session = context.metadata_store.get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found")
    context.metadata_store.update_session_status(
        session_id,
        status=SessionStatus.CANCELLED,
        completed_at=datetime.now(UTC),
    )
    return APIMessage(message="session cancelled")


@router.get("/{session_id}/artifacts", response_model=list[ArtifactResponse])
def list_artifacts(
    session_id: str,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["artifacts:read", "sessions:read"])),
) -> list[ArtifactResponse]:
    session = context.metadata_store.get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found")
    artifacts = context.metadata_store.list_artifacts(session_id)
    return [artifact_to_response(item) for item in artifacts]


@router.get("/{session_id}/artifacts/{artifact_id}")
def download_artifact(
    session_id: str,
    artifact_id: int,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["artifacts:read", "sessions:read"])),
) -> Response:
    session = context.metadata_store.get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found")
    artifact = context.metadata_store.get_artifact(artifact_id)
    if artifact is None or artifact.session_id != session_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    path = Path(artifact.path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artifact file missing")
    media_type = artifact.content_type or "application/octet-stream"
    filename = path.name
    return FileResponse(path, media_type=media_type, filename=filename)


def _compute_expiration(expires_in: int | None) -> datetime | None:
    if expires_in is None:
        return None
    return datetime.now(UTC) + timedelta(seconds=expires_in)


__all__ = ["router"]

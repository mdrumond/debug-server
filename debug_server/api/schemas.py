"""Pydantic schemas shared across API routers."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from debug_server.db.models import (
    Artifact,
    ArtifactKind,
    AuthToken,
    Command,
    CommandStatus,
    Repository,
    Session,
    SessionStatus,
)


class APIMessage(BaseModel):
    """Simple message envelope."""

    message: str


class RepositoryInitRequest(BaseModel):
    name: str
    remote_url: str
    default_branch: str
    description: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class RepositoryResponse(BaseModel):
    id: int
    name: str
    remote_url: str
    default_branch: str
    description: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SessionCreateRequest(BaseModel):
    repository: str = Field(description="Repository name")
    commit_sha: str = Field(min_length=7, max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)
    requested_by: str | None = None
    patch: str | None = Field(default=None, description="Unified diff to apply")
    expires_in: int | None = Field(default=None, ge=60, description="TTL in seconds")


class SessionResponse(BaseModel):
    id: str
    repository_id: int
    worktree_id: int | None
    status: SessionStatus
    commit_sha: str
    patch_hash: str | None
    requested_by: str | None
    expires_at: datetime | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CommandCreateRequest(BaseModel):
    argv: list[str] = Field(min_length=1)
    cwd: str | None = None
    env: dict[str, str] = Field(default_factory=dict)


class CommandResponse(BaseModel):
    id: int
    session_id: str
    sequence: int
    command: str
    status: CommandStatus
    exit_code: int | None
    created_at: datetime
    updated_at: datetime


class ArtifactResponse(BaseModel):
    id: int
    session_id: str
    command_id: int | None
    kind: ArtifactKind
    path: str
    content_type: str | None
    description: str | None
    size_bytes: int | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class TokenCreateRequest(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=lambda: ["sessions:read", "sessions:write"])
    expires_in: int | None = Field(default=None, ge=60)


class TokenResponse(BaseModel):
    id: int
    name: str
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TokenSecretResponse(TokenResponse):
    token: str


def repository_to_response(repository: Repository) -> RepositoryResponse:
    return RepositoryResponse(
        id=repository.id or 0,
        name=repository.name,
        remote_url=repository.remote_url,
        default_branch=repository.default_branch,
        description=repository.description,
        settings=repository.settings,
        created_at=repository.created_at,
        updated_at=repository.updated_at,
    )


def session_to_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        repository_id=session.repository_id,
        worktree_id=session.worktree_id,
        status=session.status,
        commit_sha=session.commit_sha,
        patch_hash=session.patch_hash,
        requested_by=session.requested_by,
        expires_at=session.expires_at,
        metadata=session.metadata_json,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def command_to_response(command: Command) -> CommandResponse:
    return CommandResponse(
        id=command.id or 0,
        session_id=command.session_id,
        sequence=command.sequence,
        command=command.command,
        status=command.status,
        exit_code=command.exit_code,
        created_at=command.created_at,
        updated_at=command.updated_at,
    )


def artifact_to_response(artifact: Artifact) -> ArtifactResponse:
    return ArtifactResponse(
        id=artifact.id or 0,
        session_id=artifact.session_id,
        command_id=artifact.command_id,
        kind=artifact.kind,
        path=artifact.path,
        content_type=artifact.content_type,
        description=artifact.description,
        size_bytes=artifact.size_bytes,
        metadata=artifact.metadata_json,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


def token_to_response(token: AuthToken) -> TokenResponse:
    return TokenResponse(
        id=token.id or 0,
        name=token.name,
        scopes=list(token.scopes or []),
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        revoked_at=token.revoked_at,
        created_at=token.created_at,
        updated_at=token.updated_at,
    )


def compute_patch_hash(patch: str | None) -> str | None:
    if not patch:
        return None
    digest = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    return digest


__all__ = [
    "APIMessage",
    "ArtifactResponse",
    "CommandCreateRequest",
    "CommandResponse",
    "RepositoryInitRequest",
    "RepositoryResponse",
    "SessionCreateRequest",
    "SessionResponse",
    "TokenCreateRequest",
    "TokenResponse",
    "TokenSecretResponse",
    "artifact_to_response",
    "command_to_response",
    "compute_patch_hash",
    "repository_to_response",
    "session_to_response",
    "token_to_response",
]

"""SQLModel schema definitions for the metadata database."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, String
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship, SQLModel


class TimestampMixin(SQLModel):
    """Common timestamp fields."""

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class VersionedMixin(SQLModel):
    """Adds an integer version column for optimistic locking."""

    version: int = Field(default=1, nullable=False)


class Repository(SQLModel, table=True):
    """Tracked upstream repository configuration."""

    __tablename__ = "repositories"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False, sa_column=Column(String(255), unique=True))
    remote_url: str = Field(sa_column=Column(String(1024), nullable=False))
    default_branch: str = Field(sa_column=Column(String(255), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(String(1024)))
    settings: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
        description="Arbitrary repository-level metadata.",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    worktrees: list[Worktree] = Relationship(back_populates="repository")
    sessions: list[Session] = Relationship(back_populates="repository")


class WorktreeStatus(str, enum.Enum):
    """Lifecycle states for a worktree entry."""

    IDLE = "idle"
    RESERVED = "reserved"
    BUSY = "busy"


class Worktree(SQLModel, TimestampMixin, VersionedMixin, table=True):
    """Represents a reusable git worktree."""

    __tablename__ = "worktrees"

    id: int | None = Field(default=None, primary_key=True)
    repository_id: int = Field(foreign_key="repositories.id", nullable=False, index=True)
    path: str = Field(sa_column=Column(String(1024), nullable=False, unique=True))
    commit_sha: str | None = Field(default=None, sa_column=Column(String(40), index=True))
    environment_hash: str | None = Field(default=None, sa_column=Column(String(64), index=True))
    status: WorktreeStatus = Field(
        sa_column=Column(
            SAEnum(WorktreeStatus, name="worktree_status"),
            nullable=False,
            index=True,
        ),
        default=WorktreeStatus.IDLE,
    )
    lease_owner: str | None = Field(default=None, sa_column=Column(String(255)))
    lease_token: str | None = Field(default=None, sa_column=Column(String(64), unique=True))
    leased_at: datetime | None = None
    lease_expires_at: datetime | None = None
    last_heartbeat_at: datetime | None = None

    repository: Repository = Relationship(back_populates="worktrees")
    sessions: list[Session] = Relationship(back_populates="worktree")


class SessionStatus(str, enum.Enum):
    """Lifecycle states for sessions."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Session(SQLModel, TimestampMixin, table=True):
    """Represents an execution session tied to a worktree."""

    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True, index=True)
    repository_id: int = Field(foreign_key="repositories.id", nullable=False)
    worktree_id: int | None = Field(default=None, foreign_key="worktrees.id")
    token_id: int | None = Field(default=None, foreign_key="auth_tokens.id")
    requested_by: str | None = Field(default=None, sa_column=Column(String(255)))
    commit_sha: str = Field(sa_column=Column(String(40), nullable=False))
    patch_hash: str | None = Field(default=None, sa_column=Column(String(64)))
    status: SessionStatus = Field(
        sa_column=Column(SAEnum(SessionStatus, name="session_status"), nullable=False, index=True),
        default=SessionStatus.PENDING,
    )
    expires_at: datetime | None = Field(default=None, index=True)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
        description="Structured metadata provided by clients.",
    )

    repository: Repository = Relationship(back_populates="sessions")
    worktree: Worktree | None = Relationship(back_populates="sessions")
    commands: list[Command] = Relationship(back_populates="session")
    artifacts: list[Artifact] = Relationship(back_populates="session")
    token: AuthToken | None = Relationship(back_populates="sessions")
    debugger_state: DebuggerState | None = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"uselist": False},
    )


class CommandStatus(str, enum.Enum):
    """Command execution phases."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Command(SQLModel, TimestampMixin, table=True):
    """Stored command invocation details."""

    __tablename__ = "commands"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", nullable=False, index=True)
    sequence: int = Field(default=0, nullable=False)
    command: str = Field(sa_column=Column(String(1024), nullable=False))
    cwd: str | None = Field(default=None, sa_column=Column(String(512)))
    env: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: CommandStatus = Field(
        sa_column=Column(SAEnum(CommandStatus, name="command_status"), nullable=False, index=True),
        default=CommandStatus.PENDING,
    )
    exit_code: int | None = Field(default=None)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    log_path: str | None = Field(default=None, sa_column=Column(String(1024)))

    session: Session = Relationship(back_populates="commands")


class ArtifactKind(str, enum.Enum):
    """Artifact categories."""

    LOG = "log"
    COVERAGE = "coverage"
    JUNIT = "junit"
    CORE_DUMP = "core-dump"
    CUSTOM = "custom"


class Artifact(SQLModel, TimestampMixin, table=True):
    """Artifact metadata entries."""

    __tablename__ = "artifacts"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", nullable=False, index=True)
    command_id: int | None = Field(default=None, foreign_key="commands.id")
    kind: ArtifactKind = Field(
        sa_column=Column(
            SAEnum(ArtifactKind, name="artifact_kind"),
            nullable=False,
            index=True,
        )
    )
    path: str = Field(sa_column=Column(String(1024), nullable=False))
    content_type: str | None = Field(default=None, sa_column=Column(String(255)))
    description: str | None = Field(default=None, sa_column=Column(String(1024)))
    size_bytes: int | None = Field(default=None)
    checksum_sha256: str | None = Field(default=None, sa_column=Column(String(64)))
    metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

    session: Session = Relationship(back_populates="artifacts")


class AuthToken(SQLModel, TimestampMixin, table=True):
    """Bearer token metadata."""

    __tablename__ = "auth_tokens"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(255), nullable=False, unique=True))
    token_hash: str = Field(sa_column=Column(String(128), nullable=False, unique=True))
    scopes: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None

    sessions: list[Session] = Relationship(back_populates="token")


class DebuggerState(SQLModel, TimestampMixin, table=True):
    """Debugger metadata for sessions."""

    __tablename__ = "debugger_state"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", nullable=False, unique=True)
    last_event: str | None = Field(default=None, sa_column=Column(String(255)))
    breakpoints: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

    session: Session = Relationship(back_populates="debugger_state")


__all__ = [
    "Artifact",
    "ArtifactKind",
    "AuthToken",
    "Command",
    "CommandStatus",
    "DebuggerState",
    "Repository",
    "Session",
    "SessionStatus",
    "Worktree",
    "WorktreeStatus",
]

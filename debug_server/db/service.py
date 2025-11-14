"""Persistence service for the metadata database."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hmac import compare_digest

from sqlalchemy import and_, or_
from sqlmodel import Session, select

from .models import (
    Artifact,
    ArtifactKind,
    AuthToken,
    Command,
    CommandStatus,
    Repository,
    SessionStatus,
    Worktree,
    WorktreeStatus,
)
from .models import (
    Session as SessionModel,
)


class MetadataError(RuntimeError):
    """Raised when an optimistic locking check fails or data is missing."""


@dataclass
class LeaseResult:
    worktree: Worktree
    lease_token: str


def _ensure_aware(value: datetime | None) -> datetime | None:
    """Return the datetime with UTC tzinfo when missing."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class MetadataStore:
    """High-level helper for interacting with the metadata database."""

    def __init__(self, engine):
        self.engine = engine

    def _session(self) -> Session:
        return Session(self.engine)

    # Repository helpers -------------------------------------------------
    def upsert_repository(
        self,
        name: str,
        remote_url: str,
        default_branch: str,
        description: str | None = None,
    ) -> Repository:
        with self._session() as session:
            statement = select(Repository).where(Repository.name == name)
            repository = session.exec(statement).one_or_none()
            if repository is None:
                repository = Repository(
                    name=name,
                    remote_url=remote_url,
                    default_branch=default_branch,
                    description=description,
                )
                session.add(repository)
            else:
                repository.remote_url = remote_url
                repository.default_branch = default_branch
                repository.description = description
                repository.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(repository)
            return repository

    def list_repositories(self) -> list[Repository]:
        with self._session() as session:
            return list(session.exec(select(Repository)).all())

    # Worktree helpers ---------------------------------------------------
    def register_worktree(
        self,
        repository_id: int,
        path: str,
        commit_sha: str | None = None,
        environment_hash: str | None = None,
    ) -> Worktree:
        with self._session() as session:
            worktree = Worktree(
                repository_id=repository_id,
                path=path,
                commit_sha=commit_sha,
                environment_hash=environment_hash,
            )
            session.add(worktree)
            session.commit()
            session.refresh(worktree)
            return worktree

    def reserve_worktree(
        self,
        repository_id: int,
        owner: str,
        lease_ttl: timedelta,
    ) -> LeaseResult:
        with self._session() as session:
            now = datetime.now(UTC)
            statement = (
                select(Worktree)
                .where(
                    Worktree.repository_id == repository_id,
                    or_(
                        Worktree.status == WorktreeStatus.IDLE,
                        and_(
                            Worktree.lease_expires_at.is_not(None),
                            Worktree.lease_expires_at < now,
                        ),
                    ),
                )
                .order_by(Worktree.updated_at)
                .with_for_update(skip_locked=True)
            )
            worktree = session.exec(statement).first()
            if worktree is None:
                raise MetadataError("No worktree available for reservation")
            lease_token = secrets.token_hex(16)
            worktree.status = WorktreeStatus.RESERVED
            worktree.lease_owner = owner
            worktree.lease_token = lease_token
            worktree.leased_at = now
            worktree.lease_expires_at = now + lease_ttl
            worktree.version += 1
            worktree.updated_at = now
            session.add(worktree)
            session.commit()
            session.refresh(worktree)
            return LeaseResult(worktree=worktree, lease_token=lease_token)

    def release_worktree(self, worktree_id: int, lease_token: str) -> Worktree:
        with self._session() as session:
            worktree = session.get(Worktree, worktree_id)
            if worktree is None:
                raise MetadataError("Unknown worktree")
            if worktree.lease_token != lease_token:
                raise MetadataError("Lease token mismatch")
            worktree.status = WorktreeStatus.IDLE
            worktree.lease_owner = None
            worktree.lease_token = None
            worktree.leased_at = None
            worktree.lease_expires_at = None
            worktree.version += 1
            worktree.updated_at = datetime.now(UTC)
            session.add(worktree)
            session.commit()
            session.refresh(worktree)
            return worktree

    # Session helpers ----------------------------------------------------
    def create_session(
        self,
        repository_id: int,
        commit_sha: str,
        worktree_id: int | None,
        requested_by: str | None,
        token_id: int | None,
        patch_hash: str | None = None,
        metadata: dict[str, object] | None = None,
        expires_at: datetime | None = None,
    ) -> SessionModel:
        with self._session() as session:
            db_session = SessionModel(
                repository_id=repository_id,
                worktree_id=worktree_id,
                requested_by=requested_by,
                token_id=token_id,
                commit_sha=commit_sha,
                patch_hash=patch_hash,
                metadata=metadata or {},
                expires_at=expires_at,
            )
            session.add(db_session)
            session.commit()
            session.refresh(db_session)
            return db_session

    def update_session_status(
        self,
        session_id: str,
        status: SessionStatus,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> SessionModel:
        with self._session() as session:
            db_session = session.get(SessionModel, session_id)
            if db_session is None:
                raise MetadataError("Unknown session")
            db_session.status = status
            if started_at is not None:
                db_session.started_at = started_at
            if completed_at is not None:
                db_session.completed_at = completed_at
            db_session.updated_at = datetime.now(UTC)
            session.add(db_session)
            session.commit()
            session.refresh(db_session)
            return db_session

    # Command helpers ----------------------------------------------------
    def create_command(
        self,
        session_id: str,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        sequence: int = 0,
    ) -> Command:
        with self._session() as session:
            db_command = Command(
                session_id=session_id,
                command=command,
                cwd=cwd,
                env=env or {},
                sequence=sequence,
            )
            session.add(db_command)
            session.commit()
            session.refresh(db_command)
            return db_command

    def record_command_result(
        self,
        command_id: int,
        *,
        status: CommandStatus,
        exit_code: int | None,
        log_path: str | None = None,
    ) -> Command:
        with self._session() as session:
            db_command = session.get(Command, command_id)
            if db_command is None:
                raise MetadataError("Unknown command")
            now = datetime.now(UTC)
            if status == CommandStatus.RUNNING:
                db_command.started_at = now
            if status in {CommandStatus.SUCCEEDED, CommandStatus.FAILED, CommandStatus.CANCELLED}:
                db_command.completed_at = now
            db_command.status = status
            db_command.exit_code = exit_code
            db_command.log_path = log_path
            db_command.updated_at = now
            session.add(db_command)
            session.commit()
            session.refresh(db_command)
            return db_command

    def record_artifact(
        self,
        session_id: str,
        kind: ArtifactKind,
        path: str,
        *,
        command_id: int | None = None,
        content_type: str | None = None,
        description: str | None = None,
        size_bytes: int | None = None,
        checksum_sha256: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Artifact:
        with self._session() as session:
            artifact = Artifact(
                session_id=session_id,
                command_id=command_id,
                kind=kind,
                path=path,
                content_type=content_type,
                description=description,
                size_bytes=size_bytes,
                checksum_sha256=checksum_sha256,
                metadata=metadata or {},
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            return artifact

    # Auth helpers -------------------------------------------------------
    def create_token(
        self,
        name: str,
        *,
        scopes: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[AuthToken, str]:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        with self._session() as session:
            record = AuthToken(
                name=name,
                token_hash=token_hash,
                scopes=list(scopes or ("admin",)),
                expires_at=expires_at,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record, raw_token

    def authenticate(self, token_value: str) -> AuthToken | None:
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()
        with self._session() as session:
            statement = select(AuthToken).where(AuthToken.token_hash == token_hash)
            record = session.exec(statement).one_or_none()
            if record is None:
                return None
            if not compare_digest(record.token_hash, token_hash):
                return None
            now = datetime.now(UTC)
            expires_at = _ensure_aware(record.expires_at)
            expired = expires_at is not None and expires_at <= now
            revoked = record.revoked_at is not None
            if expired or revoked:
                return None
            record.last_used_at = now
            session.add(record)
            session.commit()
            session.refresh(record)
            return record


__all__ = ["LeaseResult", "MetadataError", "MetadataStore"]

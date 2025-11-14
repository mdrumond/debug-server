"""Lightweight dataclasses shared by the Debug Server SDK."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:  # pragma: no cover - Python 3.11+ exposes datetime.UTC
    from datetime import UTC
except ImportError:  # pragma: no cover - fallback for older runtimes
    from datetime import timezone as _timezone

    UTC = _timezone.utc  # noqa: UP017


def _to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass
class RepositoryInitRequest:
    remote_url: str
    default_branch: str | None = None
    dependency_manifests: list[str] = field(default_factory=list)
    allow_self_signed: bool = False

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "remote_url": self.remote_url,
            "dependency_manifests": list(self.dependency_manifests),
            "allow_self_signed": self.allow_self_signed,
        }
        if self.default_branch:
            payload["default_branch"] = self.default_branch
        return payload


@dataclass
class RepositoryInitResponse:
    repository_id: str
    default_branch: str
    worktree_count: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepositoryInitResponse:
        return cls(
            repository_id=str(data["repository_id"]),
            default_branch=str(data["default_branch"]),
            worktree_count=int(data["worktree_count"]),
        )


@dataclass
class SessionCreateRequest:
    commit: str
    commands: list[str] = field(default_factory=list)
    patch: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "commit": self.commit,
            "commands": list(self.commands),
            "metadata": dict(self.metadata),
        }
        if self.patch:
            payload["patch"] = self.patch
        return payload


@dataclass
class Session:
    session_id: str
    status: str
    commit: str
    commands: list[str]
    created_at: datetime
    metadata: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        created_value = data.get("created_at")
        created_at = _from_iso(str(created_value)) if created_value else datetime.now(UTC)
        raw_metadata = data.get("metadata") or {}
        metadata_items = raw_metadata.items() if isinstance(raw_metadata, dict) else []
        metadata = {str(k): str(v) for k, v in metadata_items}
        raw_commands = data.get("commands") or []
        commands = [str(cmd) for cmd in raw_commands] if isinstance(raw_commands, Iterable) else []
        return cls(
            session_id=str(data["session_id"]),
            status=str(data["status"]),
            commit=str(data.get("commit", "")),
            commands=commands,
            created_at=created_at,
            metadata=metadata,
        )


@dataclass
class LogEntry:
    message: str
    stream: str
    timestamp: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogEntry:
        return cls(
            message=str(data.get("message", "")),
            stream=str(data.get("stream", "stdout")),
            timestamp=_from_iso(str(data.get("timestamp", datetime.now(UTC).isoformat()))),
        )

    def to_text(self) -> str:
        return f"[{self.timestamp.isoformat()}] {self.stream.upper()}: {self.message.rstrip()}"


@dataclass
class DebugActionRequest:
    action: str
    payload: dict[str, str] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"action": self.action, "payload": dict(self.payload)}


@dataclass
class DebugActionResponse:
    status: str
    detail: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DebugActionResponse:
        detail_raw = data.get("detail")
        detail = str(detail_raw) if detail_raw is not None else None
        return cls(status=str(data.get("status", "")), detail=detail)


@dataclass
class ArtifactMetadata:
    artifact_id: str
    filename: str
    content_type: str
    size: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactMetadata:
        return cls(
            artifact_id=str(data.get("artifact_id", "")),
            filename=str(data.get("filename", "")),
            content_type=str(data.get("content_type", "application/octet-stream")),
            size=int(data.get("size", 0)),
        )

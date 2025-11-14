"""Model smoke tests."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from debug_server.db import (
    ArtifactKind,
    CommandStatus,
    MetadataStore,
    SessionStatus,
    WorktreeStatus,
)


def test_repository_round_trip(metadata_store: MetadataStore) -> None:
    repo = metadata_store.upsert_repository(
        name="demo",
        remote_url="https://example.com/repo.git",
        default_branch="main",
    )
    assert repo.id is not None
    repo2 = metadata_store.upsert_repository(
        name="demo",
        remote_url="https://example.com/fork.git",
        default_branch="develop",
    )
    assert repo2.id == repo.id
    assert repo2.remote_url.endswith("fork.git")


def test_worktree_lifecycle(metadata_store: MetadataStore, tmp_path: Path) -> None:
    repo = metadata_store.upsert_repository(
        name="repo",
        remote_url="https://example.com/repo.git",
        default_branch="main",
    )
    worktree = metadata_store.register_worktree(
        repository_id=repo.id,
        path=str(tmp_path / "w1"),
    )
    assert worktree.status == WorktreeStatus.IDLE
    lease = metadata_store.reserve_worktree(
        repo.id,
        owner="worker-1",
        lease_ttl=timedelta(minutes=5),
    )
    assert lease.worktree.status == WorktreeStatus.RESERVED
    released = metadata_store.release_worktree(lease.worktree.id, lease.lease_token)
    assert released.status == WorktreeStatus.IDLE


def test_session_and_commands(metadata_store: MetadataStore, tmp_path: Path) -> None:
    repo = metadata_store.upsert_repository(
        name="repo2",
        remote_url="https://example.com/repo2.git",
        default_branch="main",
    )
    worktree = metadata_store.register_worktree(
        repository_id=repo.id,
        path=str(tmp_path / "w2"),
    )
    session = metadata_store.create_session(
        repository_id=repo.id,
        commit_sha="abcdef1234567890",
        worktree_id=worktree.id,
        requested_by="agent",
        token_id=None,
    )
    metadata_store.update_session_status(session.id, SessionStatus.RUNNING)
    command = metadata_store.create_command(session.id, "pytest", sequence=1)
    assert command.status == CommandStatus.PENDING
    metadata_store.record_command_result(
        command.id,
        status=CommandStatus.RUNNING,
        exit_code=None,
    )
    final = metadata_store.record_command_result(
        command.id,
        status=CommandStatus.SUCCEEDED,
        exit_code=0,
    )
    assert final.exit_code == 0


def test_artifact_creation(metadata_store: MetadataStore, tmp_path: Path) -> None:
    repo = metadata_store.upsert_repository("repo3", "https://example/repo3.git", "main")
    session = metadata_store.create_session(
        repository_id=repo.id,
        commit_sha="abcdef1234567890",
        worktree_id=None,
        requested_by="agent",
        token_id=None,
    )
    artifact = metadata_store.record_artifact(
        session_id=session.id,
        kind=ArtifactKind.LOG,
        path=str(tmp_path / "log.txt"),
        metadata={"format": "text"},
    )
    assert artifact.kind is ArtifactKind.LOG
    assert artifact.metadata["format"] == "text"

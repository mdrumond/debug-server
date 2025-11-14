"""Unit tests for the worktree pool."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from debug_server.db import MetadataStore, Worktree
from debug_server.worktrees.pool import WorktreePool, WorktreePoolSettings
from tests.worktrees.conftest import commit_file, init_git_repo


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "remote"
    init_git_repo(repo)
    commit_file(repo, "README.md", "initial")
    return repo


def _pool(metadata_store: MetadataStore, repo_path: Path, tmp_path: Path) -> WorktreePool:
    repository = metadata_store.upsert_repository(
        name="demo",
        remote_url=str(repo_path),
        default_branch="main",
    )
    assert repository.id is not None
    settings = WorktreePoolSettings(
        repository_id=repository.id,
        remote_url=repository.remote_url,
        bare_path=tmp_path / "bare.git",
        worktree_root=tmp_path / "worktrees",
    )
    return WorktreePool(metadata_store, settings)


def test_acquire_and_reuse_worktree(
    metadata_store: MetadataStore, sample_repo: Path, tmp_path: Path
) -> None:
    pool = _pool(metadata_store, sample_repo, tmp_path)
    commit1 = commit_file(sample_repo, "README.md", "v1")
    lease1 = pool.acquire_worktree(commit_sha=commit1, owner="worker", environment_hash="env-a")
    assert lease1.path.exists()
    assert (lease1.path / "README.md").read_text().strip() == "v1"
    assert lease1.needs_dependency_sync is True
    lease1.release()

    commit2 = commit_file(sample_repo, "README.md", "v2")
    lease2 = pool.acquire_worktree(commit_sha=commit2, owner="worker", environment_hash="env-a")
    assert lease2.needs_dependency_sync is False
    assert (lease2.path / "README.md").read_text().strip() == "v2"
    lease2.release()

    lease3 = pool.acquire_worktree(commit_sha=commit2, owner="worker", environment_hash="env-b")
    assert lease3.needs_dependency_sync is True
    lease3.release()


def test_reclaim_removes_idle_worktrees(
    metadata_store: MetadataStore, sample_repo: Path, tmp_path: Path
) -> None:
    pool = _pool(metadata_store, sample_repo, tmp_path)
    commit_hash = commit_file(sample_repo, "file.txt", "data")
    lease = pool.acquire_worktree(commit_sha=commit_hash, owner="worker", environment_hash=None)
    path = lease.path
    lease.release()

    # mark as old so reclamation triggers
    with metadata_store._session() as session:  # type: ignore[attr-defined]
        worktree = session.get(Worktree, lease.worktree.id)
        assert worktree is not None
        worktree.updated_at = worktree.updated_at - timedelta(days=2)
        session.add(worktree)
        session.commit()

    reclaimed = pool.reclaim_stale_worktrees(max_idle_age=timedelta(hours=1))
    assert path in reclaimed
    assert not path.exists()


def test_describe_returns_serializable_data(
    metadata_store: MetadataStore, sample_repo: Path, tmp_path: Path
) -> None:
    pool = _pool(metadata_store, sample_repo, tmp_path)
    commit_hash = commit_file(sample_repo, "file.txt", "data")
    lease = pool.acquire_worktree(commit_sha=commit_hash, owner="worker", environment_hash=None)
    lease.release()
    status = pool.describe()
    assert status
    record = status[0]
    assert set(record) == {"id", "path", "status", "commit", "environment_hash", "updated_at"}

"""Integration tests for the worktree/session cache."""

from __future__ import annotations

import shutil
from pathlib import Path

from debug_server.db import MetadataStore
from debug_server.worktrees.pool import WorktreePool, WorktreePoolSettings
from tests.worktrees.conftest import commit_file, init_git_repo


def _pool(metadata_store: MetadataStore, repo_path: Path, tmp_path: Path) -> WorktreePool:
    repository = metadata_store.upsert_repository(
        name="integration",
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


def test_pool_recovers_missing_checkout(metadata_store: MetadataStore, tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    init_git_repo(remote)
    commit_hash = commit_file(remote, "file.txt", "initial")
    pool = _pool(metadata_store, remote, tmp_path)

    lease = pool.acquire_worktree(commit_sha=commit_hash, owner="worker", environment_hash=None)
    checkout_path = lease.path
    lease.release()

    shutil.rmtree(checkout_path)
    lease2 = pool.acquire_worktree(commit_sha=commit_hash, owner="worker", environment_hash=None)
    assert lease2.path.exists()
    lease2.release()

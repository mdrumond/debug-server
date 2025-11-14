"""Integration tests for transactional helpers."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from debug_server.db.testing import create_test_store


def test_reserve_requires_available_worktree(tmp_path: Path) -> None:
    store = create_test_store()
    repo = store.upsert_repository("repo", "https://example/repo.git", "main")
    store.register_worktree(repo.id, path=str(tmp_path / "wt1"))
    lease = store.reserve_worktree(repo.id, owner="worker", lease_ttl=timedelta(minutes=1))
    store.release_worktree(lease.worktree.id, lease.lease_token)


def test_token_creation_and_authentication() -> None:
    store = create_test_store()
    record, token_value = store.create_token(name="ops")
    assert record.id is not None
    authenticated = store.authenticate(token_value)
    assert authenticated is not None
    assert authenticated.id == record.id

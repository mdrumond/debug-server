"""Integration tests for transactional helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

try:  # pragma: no cover - Python 3.11+ exposes datetime.UTC
    from datetime import UTC
except ImportError:  # pragma: no cover - fallback for older runtimes
    from datetime import timezone as _timezone

    UTC = _timezone.utc  # noqa: UP017

from debug_server.db.models import AuthToken
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


def test_authentication_rejects_expired_token() -> None:
    store = create_test_store()
    expired_at = datetime.now(UTC) - timedelta(minutes=5)
    record, token_value = store.create_token(name="ops", expires_at=expired_at)
    assert record.id is not None
    assert store.authenticate(token_value) is None


def test_authentication_rejects_revoked_token() -> None:
    store = create_test_store()
    record, token_value = store.create_token(name="ops")
    assert record.id is not None
    with store._session() as session:  # noqa: SLF001 - test helper
        token = session.get(AuthToken, record.id)
        token.revoked_at = datetime.now(UTC)
        session.add(token)
        session.commit()
    assert store.authenticate(token_value) is None

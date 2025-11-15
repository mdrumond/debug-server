"""Git worktree pool management for session preparation."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import TracebackType
from uuid import uuid4

from debug_server.db import (
    MetadataError,
    MetadataStore,
    Repository,
    Worktree,
    WorktreeStatus,
)

__all__ = [
    "WorktreeLease",
    "WorktreePool",
    "WorktreePoolError",
    "WorktreePoolSettings",
]


class WorktreePoolError(RuntimeError):
    """Raised when git operations or lease management fails."""


@dataclass(slots=True)
class WorktreePoolSettings:
    """Configuration for the worktree pool."""

    repository_id: int
    remote_url: str
    bare_path: Path
    worktree_root: Path
    lease_ttl: timedelta = timedelta(minutes=30)
    max_worktrees: int = 16
    clean_checkout: bool = True


@dataclass(slots=True)
class WorktreeLease:
    """Represents a reserved worktree lease."""

    worktree: Worktree
    lease_token: str
    path: Path
    commit_sha: str
    environment_hash: str | None
    needs_dependency_sync: bool
    pool: WorktreePool

    def release(self, *, clean: bool = True) -> None:
        self.pool.release(self, clean=clean)

    def __enter__(self) -> WorktreeLease:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:  # noqa: D401 - context manager hook
        self.release()


class WorktreePool:
    """Manage git checkout directories shared across sessions."""

    def __init__(
        self,
        metadata_store: MetadataStore,
        settings: WorktreePoolSettings,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.metadata_store = metadata_store
        self.settings = settings
        self._now = now or (lambda: datetime.now(UTC))
        self.settings.bare_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.worktree_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ git helpers
    def _run_git(self, *args: str, cwd: Path | None = None, git_dir: Path | None = None) -> None:
        cmd = ["git"]
        if git_dir is not None:
            cmd.extend(["--git-dir", str(git_dir)])
        cmd.extend(args)
        try:
            subprocess.run(  # noqa: S603
                cmd,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - subprocess plumbing
            raise WorktreePoolError(exc.stderr or exc.stdout or str(exc)) from exc

    def ensure_bare_repo(self) -> None:
        """Ensure that the bare mirror exists and is up to date."""

        bare = self.settings.bare_path
        if not bare.exists():
            self._run_git("clone", "--bare", self.settings.remote_url, str(bare))
        self._run_git("fetch", "--all", "--prune", git_dir=bare)

    # ------------------------------------------------------------------ leasing
    def acquire_worktree(
        self,
        *,
        commit_sha: str,
        owner: str,
        environment_hash: str | None,
    ) -> WorktreeLease:
        """Return a worktree prepared for the requested commit."""

        self.ensure_bare_repo()
        try:
            lease = self.metadata_store.reserve_worktree(
                repository_id=self.settings.repository_id,
                owner=owner,
                lease_ttl=self.settings.lease_ttl,
            )
        except MetadataError:
            self._create_worktree_record()
            lease = self.metadata_store.reserve_worktree(
                repository_id=self.settings.repository_id,
                owner=owner,
                lease_ttl=self.settings.lease_ttl,
            )
        worktree_path = Path(lease.worktree.path)
        self._prepare_checkout(worktree_path, commit_sha)
        needs_sync = environment_hash is not None and (
            lease.worktree.environment_hash != environment_hash
        )
        worktree_id = lease.worktree.id
        if worktree_id is None:  # pragma: no cover - defensive guard
            raise WorktreePoolError("Worktree missing primary key")
        updated = self.metadata_store.update_worktree_metadata(
            worktree_id,
            commit_sha=commit_sha,
            environment_hash=environment_hash,
        )
        return WorktreeLease(
            worktree=updated,
            lease_token=lease.lease_token,
            path=worktree_path,
            commit_sha=commit_sha,
            environment_hash=environment_hash,
            needs_dependency_sync=needs_sync,
            pool=self,
        )

    def release(self, lease: WorktreeLease, *, clean: bool = True) -> None:
        path = lease.path
        if clean and self.settings.clean_checkout and path.exists():
            self._run_git("reset", "--hard", "HEAD", cwd=path)
            self._run_git("clean", "-fdx", cwd=path)
        worktree_id = lease.worktree.id
        if worktree_id is None:  # pragma: no cover - defensive guard
            raise WorktreePoolError("Worktree missing primary key")
        self.metadata_store.release_worktree(worktree_id, lease.lease_token)

    # ------------------------------------------------------------------ checkout helpers
    def _prepare_checkout(self, path: Path, commit_sha: str) -> None:
        if not path.exists():
            self._clone_checkout(path)
        else:
            self._run_git("remote", "set-url", "origin", str(self.settings.bare_path), cwd=path)
        self._run_git("fetch", "origin", "--prune", cwd=path)
        self._checkout_commit(path, commit_sha)
        self._run_git("reset", "--hard", commit_sha, cwd=path)

    def _clone_checkout(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._run_git("clone", str(self.settings.bare_path), str(path))

    def _checkout_commit(self, path: Path, commit_sha: str) -> None:
        try:
            self._run_git("checkout", "--detach", commit_sha, cwd=path)
        except WorktreePoolError:
            self.ensure_bare_repo()
            self._run_git("fetch", "origin", "--prune", cwd=path)
            self._run_git(
                "fetch",
                self.settings.remote_url,
                commit_sha,
                cwd=path,
            )
            self._run_git("checkout", "--detach", commit_sha, cwd=path)

    def _create_worktree_record(self) -> Worktree:
        existing = self.metadata_store.list_worktrees(self.settings.repository_id)
        if len(existing) >= self.settings.max_worktrees:
            raise WorktreePoolError("Worktree capacity exhausted")
        new_path = self.settings.worktree_root / f"wt-{uuid4().hex[:10]}"
        return self.metadata_store.register_worktree(
            repository_id=self.settings.repository_id,
            path=str(new_path),
        )

    # ------------------------------------------------------------------ maintenance
    def reclaim_stale_worktrees(self, *, max_idle_age: timedelta) -> list[Path]:
        """Remove idle worktrees older than the requested threshold."""

        reclaimed: list[Path] = []
        now = self._now()
        for worktree in self.metadata_store.list_worktrees(self.settings.repository_id):
            if worktree.status is not WorktreeStatus.IDLE:
                continue
            if worktree.updated_at is None:
                continue
            updated_at = self._ensure_aware(worktree.updated_at)
            if updated_at + max_idle_age > now:
                continue
            path = Path(worktree.path)
            if path.exists():
                shutil.rmtree(path)
            worktree_id = worktree.id
            if worktree_id is None:  # pragma: no cover - defensive guard
                raise WorktreePoolError("Worktree missing primary key")
            self.metadata_store.update_worktree_metadata(
                worktree_id,
                commit_sha=None,
                environment_hash=None,
            )
            reclaimed.append(path)
        return reclaimed

    @staticmethod
    def _ensure_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def describe(self) -> list[dict[str, object]]:
        """Return serializable data about the pool state."""

        payload: list[dict[str, object]] = []
        for worktree in self.metadata_store.list_worktrees(self.settings.repository_id):
            payload.append(
                {
                    "id": worktree.id,
                    "path": worktree.path,
                    "status": worktree.status.value,
                    "commit": worktree.commit_sha,
                    "environment_hash": worktree.environment_hash,
                    "updated_at": worktree.updated_at.isoformat() if worktree.updated_at else None,
                }
            )
        return payload


def build_pool_from_repository(
    store: MetadataStore,
    repository: Repository,
    *,
    bare_path: Path,
    worktree_root: Path,
) -> WorktreePool:
    if repository.id is None:  # pragma: no cover - sanity guard
        raise WorktreePoolError("Repository must be persisted before creating a pool")
    settings = WorktreePoolSettings(
        repository_id=repository.id,
        remote_url=repository.remote_url,
        bare_path=bare_path,
        worktree_root=worktree_root,
    )
    return WorktreePool(store, settings)

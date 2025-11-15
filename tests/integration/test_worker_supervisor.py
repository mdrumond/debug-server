from __future__ import annotations

import sys
from pathlib import Path

import pytest

from debug_server.db import MetadataStore
from debug_server.runner import (
    CommandSpec,
    EnvironmentManager,
    EnvironmentRequest,
    RunnerPaths,
    SessionPatch,
    WorkerSupervisor,
)
from debug_server.worktrees.pool import WorktreePool, WorktreePoolSettings
from tests.worktrees.conftest import commit_file, init_git_repo


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote"
    init_git_repo(remote)
    commit_file(remote, "README.md", "base\n")
    return remote


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


def test_supervisor_end_to_end(
    metadata_store: MetadataStore, sample_repo: Path, tmp_path: Path
) -> None:
    pool = _pool(metadata_store, sample_repo, tmp_path)
    commit = commit_file(sample_repo, "README.md", "integration\n")
    lease = pool.acquire_worktree(commit_sha=commit, owner="integration", environment_hash="env-a")
    (lease.path / "requirements.txt").write_text("demo==0.1\n")
    env_manager = EnvironmentManager(tmp_path / "envs")
    supervisor = WorkerSupervisor(
        metadata_store=metadata_store,
        paths=RunnerPaths.from_root(tmp_path / "artifacts"),
        environment_manager=env_manager,
    )
    patch = SessionPatch(
        diff="""diff --git a/README.md b/README.md
index 1111111..2222222 100644
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-integration
+patched
""",
    )
    spec = CommandSpec(
        argv=[sys.executable, "-c", "print('integration run')"],
        log_name="integration",
    )
    env_request = EnvironmentRequest(
        name="session-int",
        manifests=[lease.path / "requirements.txt"],
        metadata={"python": "3.11"},
    )
    result = supervisor.run_command(
        session_id="session-int",
        spec=spec,
        lease=lease,
        env_request=env_request,
        patch=patch,
    )
    assert result.status.value == "succeeded"
    assert "integration run" in result.log_path.read_text()
    assert (lease.path / "README.md").read_text() == "patched\n"
    lease.release()

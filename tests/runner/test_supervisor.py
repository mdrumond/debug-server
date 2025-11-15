from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlmodel import select

from debug_server.db import CommandStatus, MetadataStore
from debug_server.db.models import Artifact, Command
from debug_server.runner import (
    CommandSpec,
    EnvironmentManager,
    EnvironmentRequest,
    RunnerPaths,
    SessionPatch,
    WorkerSupervisor,
)
from debug_server.runner.supervisor import CommandExecutionError


@dataclass
class FakeLease:
    path: Path
    needs_dependency_sync: bool = False


@pytest.fixture()
def supervisor(tmp_path: Path, metadata_store: MetadataStore) -> WorkerSupervisor:
    paths = RunnerPaths.from_root(tmp_path / "artifacts")
    env_manager = EnvironmentManager(paths.environments_dir)
    return WorkerSupervisor(
        metadata_store=metadata_store,
        paths=paths,
        environment_manager=env_manager,
    )


def test_run_command_streams_logs(
    supervisor: WorkerSupervisor, tmp_path: Path, metadata_store: MetadataStore
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    lease = FakeLease(path=workspace)
    events = []
    spec = CommandSpec(
        argv=[
            sys.executable,
            "-c",
            "import sys; print('hi'); sys.stderr.write('err\\n')",
        ],
        log_name="unit",
    )
    result = supervisor.run_command(
        session_id="sess-1",
        spec=spec,
        lease=lease,
        stream_observers=[events.append],
    )
    assert result.status is CommandStatus.SUCCEEDED
    assert result.log_path.exists()
    assert any(chunk.stream == "stdout" for chunk in events)
    with metadata_store._session() as session:  # type: ignore[attr-defined]
        command = session.exec(select(Command)).one()
        assert command.status is CommandStatus.SUCCEEDED
        artifact = session.exec(select(Artifact)).one()
        assert Path(artifact.path) == result.log_path


def test_patch_application_and_env_force(supervisor: WorkerSupervisor, tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    patch_file = workspace / "file.txt"
    patch_file.write_text("original\n")
    _run_git_init(workspace)
    lease = FakeLease(path=workspace, needs_dependency_sync=True)
    manager = supervisor.environment_manager
    request = EnvironmentRequest(name="sess-2")
    handle = manager.ensure(request)
    marker = handle.path / "marker"
    marker.write_text("stale")
    spec = CommandSpec(argv=[sys.executable, "-c", "print('patched')"], log_name="patch")
    patch = SessionPatch(
        diff="""diff --git a/file.txt b/file.txt
index 1111111..2222222 100644
--- a/file.txt
+++ b/file.txt
@@ -1 +1 @@
-original
+patched
""",
    )
    result = supervisor.run_command(
        session_id="sess-2",
        spec=spec,
        lease=lease,
        env_request=request,
        patch=patch,
    )
    assert result.status is CommandStatus.SUCCEEDED
    assert patch_file.read_text() == "patched\n"
    assert not marker.exists(), "force rebuild should clear the environment"


def test_timeout_marks_cancelled(supervisor: WorkerSupervisor, tmp_path: Path) -> None:
    workspace = tmp_path / "timeout"
    workspace.mkdir()
    lease = FakeLease(path=workspace)
    spec = CommandSpec(
        argv=[sys.executable, "-c", "import time; time.sleep(5)"],
        timeout=0.2,
        log_name="timeout",
    )
    result = supervisor.run_command(session_id="sess-3", spec=spec, lease=lease)
    assert result.status is CommandStatus.CANCELLED


def test_spawn_failure_records_failure(
    supervisor: WorkerSupervisor, tmp_path: Path, metadata_store: MetadataStore
) -> None:
    workspace = tmp_path / "missing"
    workspace.mkdir()
    lease = FakeLease(path=workspace)
    spec = CommandSpec(argv=["/definitely/not/a/real/binary"], log_name="missing")
    with pytest.raises(CommandExecutionError):
        supervisor.run_command(session_id="sess-4", spec=spec, lease=lease)

    with metadata_store._session() as session:  # type: ignore[attr-defined]
        command = session.exec(select(Command)).one()
        assert command.status is CommandStatus.FAILED
        artifact = session.exec(select(Artifact)).one()
        assert Path(artifact.path).exists()


def _run_git_init(path: Path) -> None:
    from tests.worktrees.conftest import _run_git, init_git_repo

    init_git_repo(path)
    _run_git("add", "file.txt", cwd=path)
    _run_git("commit", "-m", "init", cwd=path)

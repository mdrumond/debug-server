"""Worker supervisor responsible for executing commands inside workspaces."""

from __future__ import annotations

import hashlib
import os
import shlex
import subprocess
import threading
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TextIO, cast, runtime_checkable

try:  # pragma: no cover - Python 3.11+
    from datetime import UTC
except ImportError:  # pragma: no cover - fallback for <3.11
    from datetime import timezone as _timezone

    UTC = _timezone.utc  # noqa: UP017

try:  # pragma: no cover - Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for <=3.10
    import tomli as tomllib  # type: ignore[no-redef]

from debug_server.db import ArtifactKind, CommandStatus, MetadataStore
from debug_server.runner.environment import (
    EnvironmentHandle,
    EnvironmentManager,
    EnvironmentRequest,
)
from debug_server.runner.log_stream import LogChunk, LogStream

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from debug_server.worktrees.pool import WorktreeLease as WorkspaceLease
else:

    class WorkspaceLease(Protocol):
        path: Path
        needs_dependency_sync: bool


@runtime_checkable
class _EnvironmentLike(Protocol):
    path: Path
    bin_path: Path


__all__ = [
    "CommandResult",
    "CommandSpec",
    "RunnerPaths",
    "RunnerSettings",
    "SessionPatch",
    "WorkerSupervisor",
]


@dataclass(slots=True)
class RunnerPaths:
    """Filesystem layout for runner artifacts."""

    artifacts_root: Path
    logs_dir: Path
    environments_dir: Path
    patches_dir: Path

    @classmethod
    def from_root(cls, root: Path) -> RunnerPaths:
        root = Path(root)
        return cls(
            artifacts_root=root,
            logs_dir=root / "logs",
            environments_dir=root / "envs",
            patches_dir=root / "patches",
        )


@dataclass(slots=True)
class RunnerSettings:
    """User-configurable supervisor settings (parsed from TOML)."""

    paths: RunnerPaths
    default_shell: str = "/bin/bash"

    @classmethod
    def from_toml(cls, path: Path) -> RunnerSettings:
        data = tomllib.loads(Path(path).read_text("utf-8"))
        base = Path(data.get("paths", {}).get("artifacts", ".artifacts"))
        logs = Path(data.get("paths", {}).get("logs", base / "logs"))
        envs = Path(data.get("paths", {}).get("environments", base / "envs"))
        patches = Path(data.get("paths", {}).get("patches", base / "patches"))
        paths = RunnerPaths(
            artifacts_root=base,
            logs_dir=logs,
            environments_dir=envs,
            patches_dir=patches,
        )
        default_shell = data.get("runner", {}).get("default_shell", "/bin/bash")
        return cls(paths=paths, default_shell=default_shell)


@dataclass(slots=True)
class SessionPatch:
    """Represents a patch blob that should be applied before running commands."""

    diff: str
    description: str | None = None


@dataclass(slots=True)
class CommandSpec:
    """Configuration for an individual command execution."""

    argv: Sequence[str]
    env: Mapping[str, str] | None = None
    cwd: Path | None = None
    log_name: str = "command"
    timeout: float | None = None


@dataclass(slots=True)
class CommandResult:
    """Details about the finished command."""

    command_id: int
    status: CommandStatus
    exit_code: int | None
    log_path: Path


class PatchApplicationError(RuntimeError):
    """Raised when a git patch fails to apply."""


class CommandExecutionError(RuntimeError):
    """Raised when a command cannot be spawned."""


class WorkerSupervisor:
    """Coordinates environment prep, patch application, and command execution."""

    def __init__(
        self,
        *,
        metadata_store: MetadataStore,
        paths: RunnerPaths,
        environment_manager: EnvironmentManager,
        base_env: Mapping[str, str] | None = None,
    ) -> None:
        self.metadata_store = metadata_store
        self.paths = paths
        self.environment_manager = environment_manager
        self.base_env = dict(base_env or os.environ)
        self.paths.logs_dir.mkdir(parents=True, exist_ok=True)
        self.paths.patches_dir.mkdir(parents=True, exist_ok=True)
        self._sequence: MutableMapping[str, int] = {}
        self._sequence_lock = threading.Lock()

    @classmethod
    def from_settings(
        cls,
        *,
        metadata_store: MetadataStore,
        settings: RunnerSettings,
        base_env: Mapping[str, str] | None = None,
    ) -> WorkerSupervisor:
        env_manager = EnvironmentManager(settings.paths.environments_dir)
        return cls(
            metadata_store=metadata_store,
            paths=settings.paths,
            environment_manager=env_manager,
            base_env=base_env,
        )

    def run_command(
        self,
        session_id: str,
        spec: CommandSpec,
        lease: WorkspaceLease,
        *,
        env_request: EnvironmentRequest | None = None,
        patch: SessionPatch | None = None,
        stream_observers: Iterable[Callable[[LogChunk], None]] | None = None,
    ) -> CommandResult:
        workspace = Path(lease.path)
        if patch is not None:
            self._apply_patch(workspace, patch)
        env_request = env_request or EnvironmentRequest(name=session_id)
        env_handle = self.environment_manager.ensure(
            env_request,
            force=getattr(lease, "needs_dependency_sync", False),
        )
        cwd = Path(spec.cwd) if spec.cwd is not None else workspace
        env = self._build_env(env_handle, spec.env)
        argv = list(spec.argv)
        command_repr = shlex.join(argv)
        sequence = self._next_sequence(session_id)
        command_record = self.metadata_store.create_command(
            session_id=session_id,
            command=command_repr,
            cwd=str(cwd),
            env=env,
            sequence=sequence,
        )
        command_id = command_record.id
        if command_id is None:  # pragma: no cover - database invariant guard
            raise CommandExecutionError("Command record missing primary key")
        log_dir = self.paths.logs_dir / session_id
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{spec.log_name}-{command_id}.log"
        def _record_completion(status: CommandStatus, exit_code: int | None) -> None:
            self.metadata_store.record_command_result(
                command_id,
                status=status,
                exit_code=exit_code,
                log_path=str(log_path),
            )
            self.metadata_store.record_artifact(
                session_id=session_id,
                command_id=command_id,
                kind=ArtifactKind.LOG,
                path=str(log_path),
                description=f"{spec.log_name} output",
            )

        try:
            with LogStream(log_path) as stream:
                for observer in stream_observers or []:
                    stream.add_listener(observer)
                self.metadata_store.record_command_result(
                    command_id,
                    status=CommandStatus.RUNNING,
                    exit_code=None,
                    log_path=str(log_path),
                )
                exit_code, status = self._spawn_and_stream(
                    argv, cwd, env, stream, spec.timeout
                )
        except CommandExecutionError:
            _record_completion(CommandStatus.FAILED, None)
            raise

        _record_completion(status, exit_code)
        return CommandResult(
            command_id=command_id,
            status=status,
            exit_code=exit_code,
            log_path=log_path,
        )

    # ------------------------------------------------------------------ helpers
    def _spawn_and_stream(
        self,
        argv: Sequence[str],
        cwd: Path,
        env: Mapping[str, str],
        stream: LogStream,
        timeout: float | None,
    ) -> tuple[int | None, CommandStatus]:
        try:
            process = subprocess.Popen(  # noqa: S603
                argv,
                cwd=str(cwd),
                env=dict(env),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            stream.write(f"Failed to start command: {exc}\n", stream="stderr")
            raise CommandExecutionError(str(exc)) from exc

        threads: list[threading.Thread] = []

        def _pump(pipe: TextIO, label: str) -> None:
            with pipe:
                for line in iter(pipe.readline, ""):
                    stream.write(line, stream=label)

        if process.stdout is not None:
            t = threading.Thread(target=_pump, args=(process.stdout, "stdout"), daemon=True)
            t.start()
            threads.append(t)
        if process.stderr is not None:
            t = threading.Thread(target=_pump, args=(process.stderr, "stderr"), daemon=True)
            t.start()
            threads.append(t)

        try:
            exit_code = process.wait(timeout=timeout)
            status = CommandStatus.SUCCEEDED if exit_code == 0 else CommandStatus.FAILED
        except subprocess.TimeoutExpired:
            process.kill()
            stream.write("Command exceeded timeout; process killed\n", stream="stderr")
            exit_code = None
            status = CommandStatus.CANCELLED
        finally:
            for thread in threads:
                thread.join()
        return exit_code, status

    def _apply_patch(self, workspace: Path, patch: SessionPatch) -> None:
        digest = hashlib.sha256(patch.diff.encode("utf-8")).hexdigest()[:12]
        patch_path = self.paths.patches_dir / f"{digest}.patch"
        patch_path.write_text(patch.diff, encoding="utf-8")
        check_cmd = ["git", "apply", "--check", str(patch_path)]
        apply_cmd = ["git", "apply", str(patch_path)]
        try:
            subprocess.run(  # noqa: S603
                check_cmd, cwd=workspace, check=True, capture_output=True, text=True
            )
            subprocess.run(  # noqa: S603
                apply_cmd, cwd=workspace, check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - subprocess plumbing
            raise PatchApplicationError(exc.stderr or exc.stdout or str(exc)) from exc

    def _build_env(
        self,
        env_handle: EnvironmentHandle | object,
        overrides: Mapping[str, str] | None,
    ) -> dict[str, str]:
        env: dict[str, str] = dict(self.base_env)
        env_like: _EnvironmentLike | None = None
        if isinstance(env_handle, EnvironmentHandle):
            env_like = cast(_EnvironmentLike, env_handle)
        elif isinstance(env_handle, _EnvironmentLike):  # pragma: no branch - runtime check
            env_like = cast(_EnvironmentLike, env_handle)
        if env_like is not None:
            env["VIRTUAL_ENV"] = str(env_like.path)
            env["PATH"] = f"{env_like.bin_path}{os.pathsep}{env.get('PATH', '')}"
        if overrides:
            env.update({k: str(v) for k, v in overrides.items()})
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.pop("PYTHONHOME", None)
        return env

    def _next_sequence(self, session_id: str) -> int:
        with self._sequence_lock:
            current = self._sequence.get(session_id, 0)
            self._sequence[session_id] = current + 1
            return current

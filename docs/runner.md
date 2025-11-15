# Runner Supervisor

The runner supervisor owns the lifecycle of every command executed on a worker
machine. It is responsible for three things:

1. **Workspace preparation** – hydrate a worktree lease, apply optional patches,
   and wire dependency caching hints from `debug_server.worktrees`.
2. **Environment provisioning** – create/reuse Python virtual environments so
   commands run with isolated interpreters even when Docker is unavailable.
3. **Log streaming and reporting** – capture stdout/stderr in near real-time,
   persist them to disk, and update the metadata store so API/CLI clients can
   retrieve structured execution history.

## Files & Modules

| Path | Responsibility |
| ---- | -------------- |
| `debug_server/runner/environment.py` | Small venv orchestrator that hashes dependency manifests and reuses cached environments until lockfiles change. |
| `debug_server/runner/log_stream.py` | File-backed log writer with observer hooks for WebSocket/gRPC bridges. |
| `debug_server/runner/supervisor.py` | High-level worker coordinator that ties worktree leases, environments, and metadata recording together. |
| `config/runner.toml` | Default filesystem layout and shell configuration used by deployments. |

## Environment Provisioning

`EnvironmentManager` lives under `debug_server.runner.environment` and exposes an
`ensure()` method:

```python
from debug_server.runner import EnvironmentManager, EnvironmentRequest

manager = EnvironmentManager(Path(".artifacts/envs"))
request = EnvironmentRequest(
    name="session-123",
    manifests=[worktree / "requirements.txt"],
    metadata={"python": "3.11"},
)
handle = manager.ensure(request, force=lease.needs_dependency_sync)
```

- The manager computes a SHA256 fingerprint across manifests + metadata.
- If the fingerprint changes (or `force=True`), the venv is rebuilt via
  `venv.EnvBuilder` and the dependency state cache is updated so subsequent
  sessions can skip redundant work.
- Callers receive an `EnvironmentHandle` with `.path`, `.python_path`, and
  `.bin_path` helpers for wiring PATH/VIRTUAL_ENV.

## Log Streaming

`LogStream` writes every chunk to disk and fans it out to observers. Observers
are simple callables that accept a `LogChunk` object, making it trivial to pipe
output into WebSockets or gRPC streaming responses.

```python
from debug_server.runner import LogStream

with LogStream(Path(".artifacts/logs/sess-1/build.log")) as stream:
    stream.write("starting build\n")
    subscription = stream.follow()
    # Feed subscription into an asyncio task or CLI for live updates.
```

The `follow()` method returns a queue-backed iterator so streaming transports can
block on new data without busy waiting.

## Worker Supervisor

`WorkerSupervisor` glues the pieces together. Typical usage inside an API
endpoint looks like:

```python
from debug_server.runner import (
    CommandSpec,
    EnvironmentRequest,
    RunnerSettings,
    SessionPatch,
    WorkerSupervisor,
)

settings = RunnerSettings.from_toml(Path("config/runner.toml"))
supervisor = WorkerSupervisor.from_settings(
    metadata_store=metadata_store,
    settings=settings,
)

lease = worktree_pool.acquire_worktree(
    commit_sha=request.commit,
    owner=request.owner,
    environment_hash=request.environment_hash,
)

patch = SessionPatch(diff=request.patch) if request.patch else None
request = EnvironmentRequest(
    name=f"session-{session.id}",
    manifests=[lease.path / "requirements.txt"],
)
result = supervisor.run_command(
    session_id=session.id,
    spec=CommandSpec(argv=["pytest", "-q"], log_name="pytest"),
    lease=lease,
    env_request=request,
    patch=patch,
)
```

During execution the supervisor:

1. Applies the patch (if provided) via `git apply --check` to ensure deterministic
   failures.
2. Ensures the environment exists, forcing a rebuild when the worktree lease
   indicated `needs_dependency_sync=True`.
3. Creates a command record in the metadata DB and writes structured logs to
   `.artifacts/logs/<session>/...`.
4. Streams stdout/stderr to observers and updates the metadata store with
   `CommandStatus` transitions plus a log artifact entry.

## Observability Hooks

All log writes include timestamps so they can be wrapped in structured logging or
OpenTelemetry spans. The supervisor is synchronous today but `LogStream` and the
metadata updates are ready to be invoked from async contexts when we add WebSocket
bridges.

## Configuration

Deployments should customize `config/runner.toml` to point at host-specific
storage. Every path is relative to the repository root by default, meaning
`.artifacts/` remains the canonical cache for envs, logs, and patches during
local development.

# Debug/Test Server Specification

## Purpose & Scope
- Provide a long-running execution service that agents can use to build, test, and debug repositories that cannot run directly inside Codex sandboxes.
- Default to lightweight, per-worker Conda environments plus dedicated workspace folders so we can run on hosts where Docker is not available. Docker images remain optional when the operator can provision them, but the service cannot assume container privileges by default.
- Support both automated agents and human operators through a shared client interface that exposes a CLI, an MCP tool surface for LLMs, and VS Code integration.
- Maintain repository state for a single upstream project (with optional submodules/dependencies) and allow clients to run tests, arbitrary commands, and interactive debugger sessions against specific commits + patches.

## High-Level Architecture
1. **Execution Server (Python, Conda-first)**
   - Runs as a long-lived Python process on the host. When Docker is available we can still ship an image, but the primary bootstrap path is a Conda environment created from `.codex/environment.md` instructions.
   - Spawns **worker processes**. Each worker owns an isolated workspace folder plus a temporary Conda environment (or venv) seeded with the dependencies requested for that session. This keeps filesystem and interpreter state separated even without containers.
   - Exposes authenticated HTTP + WebSocket APIs implemented with FastAPI for lifecycle control: repository initialization, session creation, command execution, log streaming, and debugger control (step/run/variables/breakpoints).
   - Persists session metadata in a lightweight database (SQLite/Postgres) so the service can recover from restarts without losing in-flight sessions.
2. **Client Surfaces**
   - The CLI and MCP server ship from the same Python package, simplifying distribution (e.g., `pip install debug-server-client`). Both surfaces wrap the shared FastAPI endpoints so fixes/features land in one codebase.
   - **CLI**: Human/agent-friendly entry point that starts sessions, streams logs, attaches debuggers, downloads artifacts, packages local patches, and declares dependency metadata when initializing the server.
   - **MCP Server**: Mirrors CLI functionality for LLM agents via the Model Context Protocol (session lifecycle, log streaming, debugger control). Acts as a tool endpoint LLMs can call.
   - **VS Code Extension**: Reuses the Python client package under the hood to offer UI for starting sessions, viewing logs, and attaching VS Code's debugger to remote Python/Node/etc targets forwarded by the execution server.

## Repository Lifecycle
- The service is **single-repo scoped**. Clients must call an `initialize_repository` command that provides:
  - Git remote URL + default branch.
  - Optional submodule initialization strategy (recursive update, depth limits).
- Dependency bootstrapping instructions (user-level package managers such as Conda, pip, pipx, uv, npm/pnpm/yarn, cargo, or other supported installers). Clients must spell out which managers are required because each worker creates its own environment.
- After initialization the server maintains:
  - A **bare mirror** of the upstream repo (including submodules).
- A **working tree pool**: multiple checkout directories created via `git worktree` or overlayfs, allowing concurrent sessions without re-cloning. Eviction policy (LRU) removes idle worktrees. Each worker process binds to exactly one worktree + Conda env instance.
- Dependency caches (package managers, Conda envs, npm/pip caches, optional container layers) to avoid repeated installs.

## Session Workflow
1. **Create Session**
   - Client sends commit SHA (must exist in bare mirror) and optional `patch` blob for unpushed changes.
   - Server checks out a clean worktree, applies the patch, and validates it with `git apply --check` before mutation.
   - Server runs dependency sync if manifest changed (hash comparisons between current and cached lockfiles).
2. **Command/Test Execution**
   - Client requests commands (e.g., `pytest`, `npm test`, custom scripts). Each request is logged with structured metadata and executed inside the worker process' dedicated workspace + Conda environment (or optional container), optionally under resource quotas.
   - Logs are streamed back incrementally (chunked text + exit codes).
3. **Debug Sessions**
   - Clients can request a debugger-attached run. The server launches the command under the appropriate debugger (e.g., `debugpy`, `gdb`, `lldb`).
   - Server exposes control APIs to step, continue, inspect variables, and set breakpoints. Responses include serialized scopes/values.
   - For VS Code, the server can open a remote debug adapter (DAP) endpoint tunneled to the client.
4. **Session Management**
   - Sessions receive unique IDs returned on creation. Metadata includes commit SHA, patch hash, requested commands, user identity, and expiration TTL.
   - Clients can query status, fetch artifacts (coverage, junit, core dumps), and close sessions explicitly. Idle sessions auto-expire, releasing worktree resources.

## Remote Debugging & Tooling
- The execution server currently supports `debugpy`, `gdb`, and `lldb` for Python and native targets. Additional debuggers can be layered later, but these three are the MVP.
- Debugger adapters run inside the same worker process (Conda env by default) and forward ports over authenticated WebSocket tunnels.
- CLI/MCP provide commands like `session debug open`, `session debug step`, `session debug variables`.
- VS Code extension can attach using standard Debug Adapter Protocol via the tunnel, enabling breakpoints and variable inspection inside the remote worker environment.

## API Surface (Conceptual)
- `POST /repository/init`: Configure repo/dependency metadata.
- `POST /sessions`: Start session (commit, patch, commands, debug flag) → returns `session_id`.
- `GET /sessions/{id}`: Status (phase, exit codes, artifact pointers).
- `POST /sessions/{id}/commands`: Queue additional commands or debugger actions.
- `GET /sessions/{id}/logs` (streaming): Historical + live logs.
- `POST /sessions/{id}/debug`: Control operations (step, continue, evaluate expression).
- `DELETE /sessions/{id}`: Terminate session and reclaim resources.

## Data & State Management
- Metadata DB tables: `repositories`, `worktrees`, `sessions`, `commands`, `artifacts`, `debug_breakpoints`.
- Artifact storage (object store or local volume) retains logs, junit XML, coverage reports, coredumps. Paths are returned to clients for download.
- Patches are stored as blobs keyed by hash for reproducibility.

## Security & Isolation
- Each session runs in its own worker process with a private workspace directory and Conda environment. When cgroup/container isolation is available we can opt in, but the base design works with OS process isolation only.
- **Per-client bearer tokens** – mint opaque personal access tokens (PATs) per human/agent account, hash/store them in the metadata DB, and require them via FastAPI’s `HTTPBearer` dependency on every route (REST and WebSocket upgrades). This aligns with the “token per agent/client” requirement and avoids the CA management overhead of mTLS or SSH certificates while still letting us rotate/revoke individual credentials quickly.
- **Client distribution** – the CLI caches the token in `~/.debug-server/config`, the MCP tool reads it from environment variables, and the VS Code extension prompts once and stores it in the VS Code secret store. All three surfaces just set `Authorization: Bearer <token>` so there is no surface-specific auth logic.
- **Session scoping & auditing** – because each request ties back to a token owner, we can include user identity in the session metadata that already tracks commit, patch hash, commands, and timelines, satisfying audit requirements.
- Worktrees scrubbed after session completion (git clean + removing secrets/cache directories) before returning to pool.

## Observability
- Structured logging (JSON) for server events.
- Metrics (Prometheus) for queue depth, session counts, command latency, debugger usage.
- Tracing hooks (OpenTelemetry) to correlate client requests with underlying command execution.

## Failure Recovery
- Supervisor restarts worker processes on crash, reattaches to log streams using persisted metadata.
- Stuck sessions detected via heartbeats; resources automatically reclaimed.
- Bare repo mirror periodically `git fetch --prune` to stay current; errors reported to clients.


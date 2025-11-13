# cli: Python client + UX flows

- **ID**: T-008
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Open

## Goal
Ship a Python CLI (packaged as `debug-server-client`) that wraps the FastAPI endpoints, caches auth tokens, manages session lifecycle, streams logs/debug events, and offers ergonomics for agents/humans.

## Plan
1. Generate an OpenAPI client or shared Pydantic schemas from [`.codex/tasks/server-api-lifecycle-and-auth.md`](server-api-lifecycle-and-auth.md) to avoid duplicated models.
2. Implement CLI commands (`server init`, `session create`, `session logs`, `session debug`, `artifact download`) using Typer or Click.
3. Integrate debug streaming flows relying on [`.codex/tasks/server-api-debug-streams.md`](server-api-debug-streams.md) plus tunnel instructions from runner debugger task.
4. Provide packaging/distribution metadata and examples for storing tokens in `~/.debug-server/config`.

## Deliverables
- `client/cli/__init__.py`, `main.py`, Typer command modules.
- Shared client library under `client/sdk/` for CLI + MCP reuse.
- Packaging files (`pyproject.toml`, entry points) if not already present.

## Tests & Examples
- **Test strategy:** Unit tests for command parsing + integration tests hitting a mocked API server.
- **Commands to run tests:**
  ```bash
  pytest tests/cli
  ```
* **Examples (how to run/use the feature):**
  ```bash
  debug-server init --remote git@github.com:org/repo.git
  debug-server session create --commit main --patch /tmp/change.patch
  debug-server session logs <session-id>
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check client
  black client
  ```
* **Static analysis / type checks:**
  ```bash
  mypy client
  ```

## Documentation Updates
* [`README.md`](../../README.md)
* [`docs/cli.md`](../../docs/cli.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Need to support both interactive TTY output and JSON streaming for automation.
* Must share auth/token caching logic with MCP server.
* Provide fallback when server uses self-signed certs (CLI flag to skip TLS verify, documented clearly).

## Completion Checklist
* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**

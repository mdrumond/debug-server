# mcp: model context protocol server

- **ID**: T-009
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Done (2024-07-30)

## Goal
Implement an MCP server that exposes the same capabilities as the CLI (session lifecycle, logs, debugger control) so LLM agents can use the debug/test service through Model Context Protocol tools.

## Plan
1. Reuse the shared client SDK from [`.codex/tasks/cli-client-surface.md`](cli-client-surface.md) to interact with the FastAPI server.
2. Define MCP tool schemas for repository init, session creation, command execution, log streaming, and debugger control, mapping each to server API calls.
3. Implement streaming adapters so MCP responses can stream incremental logs (leveraging endpoints from [`.codex/tasks/server-api-debug-streams.md`](server-api-debug-streams.md)).
4. Provide packaging instructions and reference configuration for hosting the MCP server alongside the CLI.

## Deliverables
- `client/mcp/server.py`, tool definitions, and packaging metadata.
- Example MCP manifest/config files.
- Tests verifying tool contract behavior.

## Tests & Examples
- **Test strategy:** Unit tests for tool schemas + integration tests using a mock FastAPI server to exercise MCP calls.
- **Commands to run tests:**
  ```bash
  pytest tests/mcp
  ```
* **Examples (how to run/use the feature):**
  ```bash
  python -m debug_server.mcp.server --config ~/.debug-server/mcp.toml
  # Within MCP client config
  tools:
    - name: debug-server.session.create
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check client/mcp
  black client/mcp
  ```
* **Static analysis / type checks:**
  ```bash
  mypy client/mcp
  ```

## Documentation Updates
* [`docs/mcp.md`](../../docs/mcp.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Need to handle MCP auth secrets securely (environment variables) using same token flow as CLI.
* Streaming semantics must align with MCP tool expectations to avoid dropping logs.
* Provide fallbacks when server is unreachable (clear error surfaces for LLM agents).

## Completion Checklist
* [x] Code implemented
* [x] Tests written/updated and passing
* [x] Examples added/updated
* [x] Docs updated where needed
* [x] Linting/formatting clean
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**

## Completion Notes

Implemented `client/mcp/server.py` with `debug-server.*` tool schemas, `ToolResult` and
`ToolStream` helpers, stdio loop, and config loader so MCP hosts can reuse the shared
HTTP SDK. Added compatibility modules (`debug_server/mcp`) enabling
`python -m debug_server.mcp.server` plus example manifest/config files under `docs/`.

Documented the workflow in [`docs/mcp.md`](../../docs/mcp.md) and updated the global
spec to mention the new module. Tests in `tests/mcp/test_server.py` cover tool dispatch,
streaming behavior, config merging, and the manifest CLI. Packaging metadata now ships
the new namespaces.

### Test & Lint Log

- `pytest tests/mcp`
- `ruff check client tests`
- `black --check client tests`
- `mypy client`

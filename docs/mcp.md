# Model Context Protocol (MCP) Server

The Debug Server client package ships with a lightweight MCP server so LLM agents can
use the same lifecycle, logging, and debugger APIs that power the CLI. The server wraps
the HTTP SDK (`client/sdk`) and exposes each capability as an MCP tool with JSON schema
definitions and streaming semantics for logs.

## Capabilities

| Tool | Purpose |
| ---- | ------- |
| `debug-server.repository.init` | Initialize the tracked repository and dependency manifests. |
| `debug-server.session.create` | Create a session from a commit + optional patch/commands. |
| `debug-server.session.info` | Fetch metadata about an existing session. |
| `debug-server.session.logs` | Stream structured session logs (`stdout`/`stderr`). |
| `debug-server.session.commands` | List commands associated with a session. |
| `debug-server.session.debug` | Send debugger control actions (continue, step, evaluate, etc.). |

All tools share the same authentication model as the CLI (personal access tokens issued
by the execution server). The MCP server lazily instantiates the shared `DebugServerClient`
and converts responses back into JSON-friendly payloads expected by MCP clients.

## Configuration

The MCP server can reuse `~/.debug-server/config.toml` or an explicit config file. The
file mirrors the CLI format:

```toml
# docs/mcp-config.example.toml
base_url = "https://debug-server.internal:8443"
token = "pat-xxxxxxxxxxxx"
verify_tls = true
```

Pass the file to the module entry point:

```bash
python -m debug_server.mcp.server --config ~/mcp/debug-server.toml --manifest
```

If no `--config` is provided the loader falls back to `load_client_config()`, meaning the
CLI configuration and environment variables (e.g., `DEBUG_SERVER_TOKEN`) continue to
work without duplication.

## Manifest

The manifest call returns metadata suitable for MCP clients. A rendered example is
checked into [`docs/mcp-manifest.example.json`](mcp-manifest.example.json):

```json
{
  "name": "debug-server",
  "version": "0.1.0",
  "tools": [
    {
      "name": "debug-server.repository.init",
      "description": "Initialize the tracked repository and dependency manifests.",
      "input_schema": {
        "type": "object",
        "required": ["remote_url"],
        "properties": {
          "remote_url": {"type": "string", "format": "uri"},
          "default_branch": {"type": "string"},
          "dependency_manifests": {"type": "array", "items": {"type": "string"}, "default": []},
          "allow_self_signed": {"type": "boolean", "default": false}
        }
      }
    }
  ],
  "endpoints": {
    "repository": "https://debug-server.internal:8443/repository",
    "sessions": "https://debug-server.internal:8443/sessions"
  }
}
```

(Only the first tool is shown for brevity; the JSON file contains the full payload.)

## CLI Usage

The module offers three entry points for local testing and for integrating with MCP
hosts that prefer stdio:

```bash
# Print the manifest and exit.
python -m debug_server.mcp.server --manifest

# Invoke one tool (useful for smoke tests / debugging arguments).
python -m debug_server.mcp.server --tool debug-server.session.info --args '{"session_id": "sess-123"}'

# Start the stdio loop that MCP hosts can connect to.
python -m debug_server.mcp.server --stdio
```

The stdio mode speaks a simple JSON-based protocol:

1. Each line read from stdin must be a JSON object with `id`, `tool`, and optional
   `arguments` fields.
2. The server responds with JSON lines using the same `id` and `status` fields:
   - `status: "ok"` → contains `result` for standard (non-streaming) calls.
   - `status: "stream"` → emits `chunk` payloads when a tool returns a streaming result.
   - `status: "done"` → marks the end of a streaming response.
   - `status: "error"` → carries an `error` message.

This event loop gives immediate parity with CLI features while remaining transport-agnostic
so it can be embedded in a richer MCP runtime later.

## Streaming Behavior

`debug-server.session.logs` returns a `ToolStream` adapter that yields structured log
entries. Each chunk includes:

```json
{
  "message": "pytest collecting...",
  "stream": "stdout",
  "timestamp": "2024-07-30T18:41:03.851921+00:00",
  "text": "[2024-07-30T18:41:03.851921+00:00] STDOUT: pytest collecting..."
}
```

Downstream MCP clients can either display the formatted `text` field or parse
`stream`/`message` independently.

## Testing

Run the MCP-specific tests to validate schema definitions and tool dispatching:

```bash
pytest tests/mcp
```

The suite uses a dummy HTTP client so it runs quickly without requiring the real
server.

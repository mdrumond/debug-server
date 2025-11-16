# Debugger and Log Streaming Protocols

The FastAPI service exposes WebSocket routes that let clients attach debuggers and follow session logs in real time. These
protocols are intentionally lightweight so they can be reused by the CLI, MCP server, and future IDE integrations. The
runner now provisions debugger tunnels for Python (`debugpy`) and native binaries (`gdbserver`/`lldb-server`) so clients
can attach over an authenticated channel without guessing ports.

## Authentication

All WebSocket upgrades must include an `Authorization: Bearer <token>` header. Tokens must carry:

- `sessions:read` and `artifacts:read` for log streaming
- `sessions:write` for debugger control

The same bearer token validation pipeline is shared with the HTTP routes.

## Log Stream (`/sessions/{session_id}/logs`)

- **Replay:** On connect the server sends any known log history for the session.
- **Live updates:** New log chunks are forwarded as they are published by the runner.
- **Message shape:**

```json
{"stream": "stdout", "text": "line contents", "timestamp": "2024-07-30T12:00:00+00:00"}
```

### Example (CLI)

```bash
websocat -H "Authorization: Bearer $TOKEN" ws://localhost:8000/sessions/$SESSION_ID/logs
```

## Debugger Control (`/sessions/{session_id}/debug`)

- **Commands:** Clients send JSON objects representing debugger requests (e.g., `{"action": "step"}`). Each command is echoed
  with an `ack` payload so callers can correlate transmission.
- **Events:** Server-initiated debugger events (e.g., breakpoints, variable updates) are published with the `kind` value set to
  the event type and the original `payload` echoed back.
- **Message shape:**

```json
{"session_id": "abc123", "kind": "event", "payload": {"reason": "breakpoint"}, "timestamp": "..."}
```

### Example (CLI)

```bash
websocat -H "Authorization: Bearer $TOKEN" ws://localhost:8000/sessions/$SESSION_ID/debug
```

## Debugger Tunnels

- **Adapters:** `debugpy` for Python modules/scripts, `gdbserver` for GNU toolchains, and `lldb-server` for LLDB targets.
- **Port discovery:** Each launch allocates an ephemeral port and stores it in the session's debugger metadata along with a
  random bearer token.
- **Attach URIs:** The runner records a TCP URI (e.g., `tcp://127.0.0.1:12345`) and bearer token in the debugger metadata
  payload. Clients should request the session metadata before connecting so they can forward ports or open IDE tunnels.
- **Environment hints:** Commands launched under a debugger inherit `DEBUG_SESSION_TOKEN` and `DEBUG_SESSION_URI` to simplify
  adapter-side authentication.

## Error Handling

- Unknown sessions close the WebSocket immediately with code 1008 (policy violation); HTTP status codes are not used after the upgrade.
- Missing or insufficient scopes close the connection before any data is exchanged.

These semantics mirror the HTTP API to keep client implementations consistent.

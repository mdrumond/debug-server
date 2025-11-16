# Debugger and Log Streaming Protocols

The FastAPI service exposes WebSocket routes that let clients attach debuggers and follow session logs in real time. These
protocols are intentionally lightweight so they can be reused by the CLI, MCP server, and future IDE integrations.

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

## Error Handling

- Unknown sessions yield a `404` and close the WebSocket with a policy violation code.
- Missing or insufficient scopes close the connection before any data is exchanged.

These semantics mirror the HTTP API to keep client implementations consistent.

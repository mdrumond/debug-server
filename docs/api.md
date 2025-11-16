# FastAPI Lifecycle API

The FastAPI service under `debug_server/api` exposes authenticated HTTP and WebSocket endpoints for repository initialization, session lifecycle management, command queueing, and artifact downloads.

## Authentication

All requests must include an `Authorization: Bearer <token>` header. Create tokens via `python -m debug_server.db.admin create-token <name> --scopes admin,sessions:write`. Tokens can also be created and revoked through the `/auth/tokens` endpoints. Scopes gate sensitive operations:

- `admin`: Full access including repository initialization and token management.
- `sessions:read` / `sessions:write`: Session inspection and lifecycle control.
- `commands:write`: Queue commands for existing sessions.
- `artifacts:read`: Download artifacts produced by sessions.

Tokens with the `admin` scope automatically satisfy any other scope check.

WebSocket upgrades reuse the same bearer token flow. Pass `Authorization: Bearer <token>` in the initial handshake headers when
connecting to streaming endpoints.

## Repository Initialization

```
POST /repository/init
```

Configure the upstream repository before creating sessions:

```bash
http POST :8000/repository/init \
  Authorization:"Bearer $TOKEN" \
  name=demo remote_url=https://github.com/example/demo.git default_branch=main
```

## Session Lifecycle

```
POST   /sessions
GET    /sessions
GET    /sessions/{session_id}
DELETE /sessions/{session_id}
```

Create a session pinned to a commit (patch uploads return a SHA-256 `patch_hash` stored in metadata):

```bash
http POST :8000/sessions \
  Authorization:"Bearer $TOKEN" \
  repository=demo commit_sha=abc1234 metadata:='{"ci": true}'
```

Use `GET /sessions` to list active sessions or `DELETE /sessions/{id}` to cancel a run.

## Command Queueing

```
POST /sessions/{session_id}/commands
GET  /sessions/{session_id}/commands
```

Queue arbitrary commands for a session:

```bash
http POST :8000/sessions/$SESSION_ID/commands \
  Authorization:"Bearer $TOKEN" \
  argv:='["pytest", "-k", "api"]'
```

The service records each command in the metadata store and returns the database identifier so log processing pipelines can correlate entries.

## Log Streaming

```
WEBSOCKET /sessions/{session_id}/logs
```

The log stream endpoint replays historical log lines for the session and then streams new chunks as they arrive. Messages are JSON
objects of the form:

```json
{"stream": "stdout", "text": "line contents", "timestamp": "2024-07-30T12:00:00+00:00"}
```

Clients must provide the `sessions:read` and `artifacts:read` scopes. Example connection using `websocat`:

```bash
websocat -H "Authorization: Bearer $TOKEN" ws://localhost:8000/sessions/$SESSION_ID/logs
```

## Debugger Control

```
WEBSOCKET /sessions/{session_id}/debug
```

Debugger streams carry control commands (step, continue, evaluate) and events raised by the backing debugger adapter. Clients must
hold the `sessions:write` scope. Each inbound message is echoed with an `ack` envelope while server-side events are emitted with
their original `kind` field:

```json
{"session_id": "abc123", "kind": "event", "payload": {"reason": "breakpoint"}, "timestamp": "..."}
```

See [`docs/debugging.md`](debugging.md) for protocol guidance shared with the CLI and MCP client surfaces.

## Artifacts

```
GET /sessions/{session_id}/artifacts
GET /sessions/{session_id}/artifacts/{artifact_id}
```

Artifacts are recorded by workers via `MetadataStore.record_artifact`. The HTTP API lists metadata and streams the referenced files back to clients:

```bash
http :8000/sessions/$SESSION_ID/artifacts Authorization:"Bearer $TOKEN"
http :8000/sessions/$SESSION_ID/artifacts/$ARTIFACT_ID Authorization:"Bearer $TOKEN" --download
```

## Health & Ready Probes

- `GET /healthz` – lightweight liveness indicator.
- `GET /readyz` – confirms the metadata store is reachable and migrations are applied.

See the auto-generated OpenAPI docs (`/docs` and `/redoc`) for the full schema, including request/response models shared with the CLI and MCP client surfaces.

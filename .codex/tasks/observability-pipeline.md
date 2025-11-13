# observability: logging, metrics, and tracing

- **ID**: T-010
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Open

## Goal
Implement structured logging, Prometheus metrics, and OpenTelemetry tracing across the FastAPI server, runner, and clients so operators can monitor session throughput, errors, and debugger usage.

## Plan
1. Introduce a shared instrumentation module that configures JSON logging, correlation IDs, and log sinks for API + runner components (depends on [`.codex/tasks/server-api-lifecycle-and-auth.md`](server-api-lifecycle-and-auth.md) and [`.codex/tasks/server-runner-worker-engine.md`](server-runner-worker-engine.md)).
2. Instrument key code paths (DB ops, worker lifecycle, WebSocket streams) with Prometheus metrics and tracing spans.
3. Provide deployment-ready exporters (Prometheus endpoint, OTLP config) plus dashboards/examples.
4. Write docs on running the observability stack locally, referencing health checks from backend tasks.

## Deliverables
- `debug_server/observability/__init__.py`, `logging.py`, `metrics.py`, `tracing.py`.
- Prometheus/OpenTelemetry configuration under `config/observability/`.
- Tests verifying logging formatters + metrics exposure.

## Tests & Examples
- **Test strategy:** Unit tests for logging helpers + integration tests hitting `/metrics` endpoint.
- **Commands to run tests:**
  ```bash
  pytest tests/observability
  ```
* **Examples (how to run/use the feature):**
  ```bash
  uvicorn debug_server.api.main:app --reload --env-file .env && curl :8000/metrics
  python -m debug_server.observability.example_traces
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check debug_server/observability
  black debug_server/observability
  ```
* **Static analysis / type checks:**
  ```bash
  mypy debug_server/observability
  ```

## Documentation Updates
* [`docs/observability.md`](../../docs/observability.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Need lightweight defaults so observability overhead doesn’t harm runner throughput.
* Provide feature flags to disable exporters when not needed.
* Ensure sensitive data is scrubbed from structured logs.

## Completion Checklist
* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**

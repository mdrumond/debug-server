# Fix failing tests and linters

## Summary
- Introduced a `MetadataAttributeMixin` so `Session` and `Artifact` instances expose their JSON metadata via `.metadata` without colliding with SQLModel's declarative `MetaData`, eliminating the `'MetaData' object is not subscriptable` failure in `tests/db/test_models.py`.
- Added a portable `UTC` fallback (with compatibility no-ops for Python < 3.11) that is reused across the ORM, client SDK, and test suites to keep every timestamp timezone-aware without depending on `datetime.UTC` being present.
- Tidied the CLI and MCP tests so their imports remain deterministic after adding the compatibility helpers, keeping the path adjustments but satisfying Ruff's expectations.

## Tests & Tooling
- `pytest`
- `ruff check .` *(fails because of long-standing security/line-length warnings in `scripts/bootstrap.py`, `client/config.py`, `tests/bootstrap/test_bootstrap.py`, and `tests/mcp/test_server.py`)*
- `black .`

### Test files covering this change
- `tests/db/test_models.py`
- `tests/integration/test_db_transactions.py`
- `tests/cli/test_cli.py`
- `tests/mcp/test_server.py`

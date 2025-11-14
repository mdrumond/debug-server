# Unified client and server packaging

## Summary
- updated the root `pyproject.toml` so a single wheel now bundles both the server (`debug_server`) and the client/CLI (`client`) packages, including the CLI entry point and dependencies they require
- removed the extra `client/pyproject.toml` to avoid conflicting build metadata and kept `client.__version__` sourced from `debug_server.version` so a single version string is published with the wheel

## Testing
- `pytest` *(fails: environment is missing third-party dependency `sqlalchemy` required for `debug_server.db` models)*
- `ruff check .` *(fails: repository already has numerous lint issues in bootstrap/tests/client modules unrelated to this packaging change)*

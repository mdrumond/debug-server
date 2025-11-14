# Separate client and server packages

## Summary
- Simplified `debug_server.__init__` so the server package exposes a single authoritative `__version__` value.
- Split the monolithic `pyproject.toml` into a server-focused configuration at the repo root and a dedicated `client/pyproject.toml` for the CLI/SDK package.
- Recorded this work and the related quality checks per the repository's Codex workflow.

## Tests
- `pytest` *(fails: environment cannot install required dependencies such as `sqlalchemy`)*
- `ruff check .` *(fails: existing repository lint issues unrelated to this change)*

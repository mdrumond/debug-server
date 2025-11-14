# Enforce mypy import checking

- Enabled missing-import checking by setting `ignore_missing_imports = false` in `pyproject.toml` so mypy reports unresolved dependencies instead of silently skipping them.
- No additional code changes were required.

## Tests
- `pytest` *(fails: RuntimeError raised during SQLModel model import because `nullable` cannot be combined with `sa_column` in `debug_server/db/models.py`)*
- `ruff check` *(fails: pre-existing lint violations across `client/`, `scripts/`, and `tests/` that need follow-up cleanup)*

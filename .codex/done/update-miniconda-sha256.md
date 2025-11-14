# Update Miniconda SHA256

## Summary
- set `conda_installer_sha256` in `config/bootstrap.toml` to the provided checksum so the bootstrapper can verify downloaded installers without requiring manual edits
- tracked the work via this log to keep Codex workflow history consistent

## Testing
- `pytest` *(fails: missing third-party dependency `sqlalchemy` required by `debug_server.db.models` during test collection)*
- `ruff check .` *(fails: pre-existing lint findings across client, bootstrap, and test modules)*

# Bootstrap environment + repo sync log

- Implemented `scripts/bootstrap.py` to automate Conda/venv provisioning, bare mirror cloning, storage prep, and smoke tests.
- Added `config/bootstrap.toml` template plus default `environment.yml` describing the Conda dependencies.
- Documented usage in `README.md`, `.codex/environment.md`, and `.codex/spec.md` so operators know exactly how to run the bootst
rap.
- Created `tests/bootstrap/test_bootstrap.py` integration tests that validate storage creation, git mirror cloning, and smoke tes
t warnings.
- Recorded smoke-test commands (`./scripts/bootstrap.py --check` and `pytest tests/bootstrap`) as mandatory checks before PRs.

## Tests touched
- `tests/bootstrap/test_bootstrap.py` (new)

## Commands executed
- `./scripts/bootstrap.py --check`
- `pytest tests/bootstrap`

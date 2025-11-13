# Bootstrap environment + repo sync log

- Implemented `scripts/bootstrap.py` to automate Conda/venv provisioning, bare mirror cloning, storage prep, and smoke tests.
- Added `config/bootstrap.toml` template plus default `environment.yml` describing the Conda dependencies.
- Documented usage in `README.md`, `.codex/environment.md`, and `.codex/spec.md` so operators know exactly how to run the bootstrap.
- Created `tests/bootstrap/test_bootstrap.py` integration tests that validate storage creation, git mirror cloning, and smoke test warnings.
- Recorded smoke-test commands (`./scripts/bootstrap.py --check` and `pytest tests/bootstrap`) as mandatory checks before PRs.
- Updated the bootstrap script to auto-install Miniconda when `conda` is missing, verify the already-cloned repository checkout instead of cloning a bare mirror, and expose the new knobs via `config/bootstrap.toml`.
- Refreshed the docs (`README.md`, `.codex/environment.md`, `.codex/spec.md`) to describe the automatic Conda install + repo verification workflow.
- Extended the bootstrap tests to cover repository fetches from an existing checkout and the automatic Conda installation flow.

## Tests touched
- `tests/bootstrap/test_bootstrap.py` (new, updated)

## Commands executed
- `./scripts/bootstrap.py --check`
- `pytest tests/bootstrap`
- `ruff check scripts/bootstrap.py`
- `black --check scripts/bootstrap.py`
- `mypy scripts/bootstrap.py`

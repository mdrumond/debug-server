# bootstrap: conda SSL verification fix

## Summary
- ensured `scripts/bootstrap.py` exports `CONDA_SSL_VERIFY` from existing certificate bundle environment variables so Conda trusts enterprise TLS proxies
- documented the behavior in `README.md` and `.codex/environment.md`
- added regression tests covering the certificate detection logic

## Testing
- `pytest tests/bootstrap/test_bootstrap.py`
- `./scripts/bootstrap.py --check`
- `ruff check scripts/bootstrap.py` *(fails: repository-wide Ruff config flags legacy style issues in this file unrelated to the certificate fix)*
- `black --check scripts/bootstrap.py` *(fails: existing formatting choices violate Black's defaults across the file)*
- `mypy scripts/bootstrap.py`

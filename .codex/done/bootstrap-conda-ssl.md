# Fix Conda SSL trust chain in bootstrapper

- **ID**: TASK-001
- **Created**: 2025-02-14
- **Owner**: gpt-5-codex
- **Status**: Done

## Goal
Ensure the bootstrap script can successfully provision the Conda environment when hosts expose proxy certificates via `REQUESTS_CA_BUNDLE`. The original flow forwarded that single path to `CONDA_SSL_VERIFY`, stripping Conda of the default CA store and causing SSL errors when the proxy certificate was not part of the upstream chain. We needed to combine the host-provided CA with the system defaults so Conda trusts both.

## Deliverables
- Updated `scripts/bootstrap.py` with helpers that merge proxy-provided CA bundles with the system trust store, persist the combined file under `.artifacts/certs/conda-ca-bundle.pem`, propagate the merged path back to `CONDA_SSL_VERIFY` *and* the originating certificate environment variable, and log the new provenance message so `conda` and other TLS-aware tooling all reuse the same trust roots. The helper now tolerates transient read/write failures and can flatten OpenSSL `capath` directories when they are the only available trust source.
- Extended tests in `tests/bootstrap/test_bootstrap.py` that validate both the proxy-only and proxy+system scenarios along with the new environment-variable propagation semantics. Added targeted cases for OpenSSL certificate directories (`test_combines_proxy_bundle_with_system_directory` and `test_detects_system_certificate_directory`) so regressions around `openssl_capath` detection are caught.
- Documentation updates in [`.codex/environment.md`](../environment.md) highlighting the new behavior and bundle location.
- Recorded lint/test executions with notes on pre-existing failures elsewhere in the repo.

## Tests & Examples
- **Test strategy:** Unit tests for the bootstrap helper that runs outside of Conda.
- **Commands to run tests:**
  ```bash
  pytest tests/bootstrap/test_bootstrap.py
  pytest
  ```
  *Result:* The targeted bootstrap suite now passes. The repository-wide `pytest` run still fails during collection because `sqlmodel.Field` rejects `nullable` when paired with `sa_column` in `debug_server/db/models.py`; this pre-existing issue is unrelated to the bootstrapper changes.

* **Examples (how to run/use the feature):**

  ```bash
  ./scripts/bootstrap.py --config config/bootstrap.local.toml
  ```

## Linting & Quality

* **Commands to lint/format:**

  ```bash
  ruff check scripts/bootstrap.py tests/bootstrap/test_bootstrap.py
  black --check .
  ```
  *Result:* `ruff` continues to flag historical violations (line length, security heuristics) scattered throughout `scripts/bootstrap.py` and `tests/bootstrap/test_bootstrap.py`. `black --check .` reports formatting drift in unrelated modules such as `debug_server/mcp/__init__.py`, though the touched files were formatted via `black scripts/bootstrap.py tests/bootstrap/test_bootstrap.py`.
* **Static analysis / type checks:**

  ```bash
  mypy
  ```
  *Result:* Existing `Any` return types in `client/sdk/client.py` trigger `no-any-return` errors. These are unrelated to this task.

## Documentation Updates

* [`.codex/environment.md`](../environment.md)

## Notes / Risks

* The combined bundle path is deterministic (`.artifacts/certs/conda-ca-bundle.pem`) so it can be cached or purged easily.
* We intentionally log only the source labels (e.g., `REQUESTS_CA_BUNDLE + system trust store`) and never the certificate contents themselves.

## Completion Checklist

* [x] Code implemented
* [x] Tests written/updated (bootstrap-focused)
* [x] Examples added/updated (bootstrap invocation remains accurate)
* [x] Docs updated where needed
* [x] Linting/formatting commands executed (failures documented)
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**

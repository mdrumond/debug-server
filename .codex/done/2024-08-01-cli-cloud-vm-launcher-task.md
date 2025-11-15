# 2024-08-01 – CLI cloud VM launcher task

## Summary
- Added [`.codex/tasks/cli-cloud-vm-launcher.md`](../tasks/cli-cloud-vm-launcher.md) defining the Terraform-based optional CLI workflow for provisioning remote debug-server hosts.

## Tests
- `pytest` (passes after installing the project editable).
- `ruff check .` (fails on pre-existing bootstrap hardcoded secret and lint warnings in `scripts/bootstrap.py` and related tests).

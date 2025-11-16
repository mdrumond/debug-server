# 2024-08-02 – CLI cloud launcher spec updates

## Summary
- Tightened [`.codex/tasks/cli-cloud-vm-launcher.md`](../tasks/cli-cloud-vm-launcher.md) so the Terraform-based workflow is human-only, persists provider addresses/tokens, and integrates with a multi-server session tracker.
- Added [`.codex/tasks/cli-cloud-session-state.md`](../tasks/cli-cloud-session-state.md) describing the secure state store and CLI UX for tracking sessions across multiple remote servers.

## Tests
- `pytest`
- `ruff check .` *(fails on existing bootstrap/test lint issues unrelated to this change — see terminal output for details.)*

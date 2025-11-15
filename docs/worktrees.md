# Worktree Pool and Session Cache

The execution server keeps a single bare clone of the upstream repository and lazily
creates working directories that are leased to runner sessions. The implementation
lives in [`debug_server/worktrees/`](../debug_server/worktrees/) and exposes a
`WorktreePool` facade that coordinates git operations with the SQLite metadata
store.

## Bare repository lifecycle

1. The pool clones the configured remote URL as a bare mirror (by default inside
   `.artifacts/repos/<repo>.bare`).
2. Every lease request triggers `git fetch --all --prune` so the mirror always
   has the latest refs.
3. New worktrees are created by cloning from the bare mirror which means the
   remote is only fetched once per acquisition.

## Leasing semantics

- `WorktreePool.acquire_worktree(...)` returns a `WorktreeLease` context manager
  tied to a metadata row. The lease reserves the worktree for the caller and
  records the requested commit SHA and dependency fingerprint.
- When released the pool cleans (`git reset --hard`, `git clean -fdx`) and marks
  the entry as idle. The metadata TTL (configured via the database) ensures other
  workers cannot hijack a worktree without a valid lease token.
- `reclaim_stale_worktrees()` implements a simple TTL eviction based on the
  metadata `updated_at` timestamp. Idle entries older than the provided delta
  have their checkout directories removed so future sessions recreate them from
  scratch.

## Dependency caching

`debug_server/worktrees.dependency_sync` provides helpers to fingerprint any
combination of lockfiles, requirements, or environment manifests. The
`DependencyStateStore` writes JSON blobs in a cache directory so sessions can
skip reinstalling dependencies unless the fingerprint changes.

## Admin commands

Two Typer-based admin entry points are available:

```bash
python -m debug_server.worktrees.inspect show-active --repository demo
python -m debug_server.worktrees.inspect reclaim --repository demo --older-than 2h
```

Use `--database-url` to point at a non-default SQLite/Postgres instance and
`--bare-path/--worktree-root` to override the filesystem layout when running on
custom infrastructure.

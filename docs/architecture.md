# Metadata Store Architecture

The execution service stores all long-lived metadata in a SQLite database that can be upgraded
via Alembic migrations. The schema is defined in `debug_server/db/models.py` and contains the
following major tables:

- `repositories`: Upstream repo configuration such as remote URL and default branch.
- `worktrees`: Git worktrees that can be leased to workers. Lease owner, token, commit SHA, and
  environment hashes are tracked with optimistic locking.
- `sessions`: Each execution session references its repository, optional worktree, and the auth
  token that created it. JSON metadata captures additional client-provided context.
- `commands`: Every requested command is stored with status, exit code, timestamps, and the
  absolute log path.
- `artifacts`: Metadata for produced files such as logs, coverage, JUnit XML, and crash dumps.
- `auth_tokens`: Stores hashed bearer tokens plus their scopes, expiry, and last usage.
- `debugger_state`: Optional debugger checkpoints for active sessions.

## Access Layer

`debug_server/db/service.py` exposes a `MetadataStore` class with helpers for repositories,
worktrees, sessions, commands, artifacts, and tokens. The helpers wrap SQLModel sessions so
callers can execute transactional workflows without managing lower-level SQLAlchemy state.
Optimistic locking is implemented through the `Worktree.version` column and lease tokens.

## Migrations and Tooling

- Run migrations: `python -m debug_server.db.migrate upgrade head`
- Show history: `python -m debug_server.db.migrate history`
- Create a token: `python -m debug_server.db.admin create-token ops`

The migration environment uses Alembic and SQLModel metadata to generate schema changes. All
commands respect the `DEBUG_SERVER_DB_URL` environment variable and default to
`sqlite:///.artifacts/data/metadata.db` when unset.

## Testing

`debug_server/db/testing.py` contains fixtures for in-memory SQLite usage. Both unit and
integration tests rely on the helpers to keep the suite fast and deterministic.

# Debug Server CLI

The Click-based CLI ships from the shared `debug-server-client` package found under [`client/`](../client/). It exposes a user-friendly surface for initializing the server, creating sessions, streaming logs, controlling debugger sessions, and downloading artifacts.

## Installation

```bash
pip install -e .
```

This registers the `debug-server` command via the entry point defined in `pyproject.toml`.

## Authentication

1. Create a token via the Debug Server operator.
2. Persist the token and base URL locally:

   ```bash
   debug-server configure --base-url https://debug.example.com --token sk-xxx
   ```

   Credentials live at `~/.debug-server/config.toml`. Set `DEBUG_SERVER_HOME` to override the location in CI.

## Common Commands

### Initialize the server repository

```bash
debug-server server init https://github.com/org/repo.git --default-branch main --manifest requirements.txt
```

### Create a session and follow logs

```bash
debug-server session create --commit main --patch /tmp/changes.patch --command "pytest -m smoke" --metadata ticket=ABC-123 --follow
```

### Tail an existing session

```bash
debug-server session logs 01H..XYZ --follow --format text
```

### Send debugger actions

```bash
debug-server session debug 01H..XYZ --action step --payload frame=top
```

### Download artifacts

```bash
debug-server artifact download 01H..XYZ coverage-xml --output ~/Downloads/coverage.xml
```

Use `debug-server --help` or `debug-server <group> --help` for option details.

"""Click-based CLI for interacting with the Debug Server."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import click
from click.core import ParameterSource

from client.cli.templates import (
    AGENT_SENTINEL_END,
    AGENT_SENTINEL_START,
    DEFAULT_SPEC_TEMPLATE,
    render_agent_installation,
)
from client.config import ClientConfig, load_client_config, save_client_config
from client.sdk import (
    DebugActionRequest,
    DebugServerClient,
    RepositoryInitRequest,
    SessionCreateRequest,
)


@dataclass
class CLIState:
    settings: ClientConfig
    client: DebugServerClient | None = None

    def ensure_client(self) -> DebugServerClient:
        if self.client is None:
            if not self.settings.token:
                message = (
                    "No auth token configured. Set DEBUG_SERVER_TOKEN or run "
                    "'debug-server configure'."
                )
                raise click.UsageError(message)
            self.client = DebugServerClient(
                base_url=self.settings.base_url,
                token=self.settings.token,
                verify_tls=self.settings.verify_tls,
            )
        return self.client

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None


def _parse_metadata(entries: Iterable[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise click.BadParameter(f"Metadata must be key=value (received '{entry}').")
        key, value = entry.split("=", 1)
        metadata[key.strip()] = value.strip()
    return metadata


@click.group()
@click.option("--base-url", help="Override the server URL for this invocation.")
@click.option("--token", help="Override the API token for this invocation.")
@click.option(
    "--insecure/--verify",
    default=False,
    show_default=True,
    help="Disable TLS verification for hosts with self-signed certificates.",
)
@click.pass_context
def app(ctx: click.Context, base_url: str | None, token: str | None, insecure: bool) -> None:
    """Interact with the Debug Server via HTTP APIs."""

    config = load_client_config()
    verify_override: bool | None = None
    if insecure:
        verify_override = False
    else:
        source = ctx.get_parameter_source("insecure")
        if source in {
            ParameterSource.COMMANDLINE,
            ParameterSource.ENVIRONMENT,
        }:
            verify_override = True
    overrides = config.merged(
        base_url=base_url,
        token=token,
        verify_tls=verify_override,
    )
    ctx.obj = CLIState(settings=overrides)


@app.command()
@click.option("--base-url", required=True, help="Debug Server base URL, e.g., https://host:8000")
@click.option("--token", required=True, help="Personal access token issued by the server operator.")
@click.option(
    "--insecure/--verify",
    default=False,
    show_default=True,
    help="Persist configuration with TLS verification disabled.",
)
def configure(base_url: str, token: str, insecure: bool) -> None:
    """Persist default CLI settings under ~/.debug-server/config.toml."""

    config = ClientConfig(base_url=base_url, token=token, verify_tls=not insecure)
    path = save_client_config(config)
    click.echo(f"Saved configuration to {path}.")


@app.group()
def server() -> None:
    """Server lifecycle commands."""


@app.group()
def session() -> None:
    """Session management commands."""


@app.group()
def artifact() -> None:
    """Artifact utilities."""


@app.group()
def agent() -> None:
    """Agent workflow helpers."""


@server.command("init")
@click.argument("remote")
@click.option(
    "--default-branch",
    default="main",
    show_default=True,
    help="Default branch to track.",
)
@click.option(
    "--manifest",
    multiple=True,
    help="Optional dependency manifest names recorded with the repository.",
)
@click.option(
    "--save-token/--no-save-token",
    default=False,
    show_default=True,
    help="Persist the current CLI overrides to ~/.debug-server/config.toml.",
)
@click.pass_obj
def server_init(
    state: CLIState,
    remote: str,
    default_branch: str,
    manifest: Iterable[str],
    save_token: bool,
) -> None:
    client = state.ensure_client()
    request = RepositoryInitRequest(
        remote_url=remote,
        default_branch=default_branch,
        dependency_manifests=list(manifest),
        allow_self_signed=not state.settings.verify_tls,
    )
    response = client.initialize_repository(request)
    summary = (
        f"Repository {response.repository_id} initialized "
        f"(default branch {response.default_branch}, worktrees {response.worktree_count})."
    )
    click.echo(summary)
    if save_token:
        save_client_config(state.settings)


@session.command("create")
@click.option("--commit", required=True, help="Commit SHA or reference for the session.")
@click.option(
    "--patch",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Optional patch applied before starting the session.",
)
@click.option(
    "--command",
    multiple=True,
    help="Commands to queue as soon as the session is ready.",
)
@click.option(
    "--metadata",
    multiple=True,
    help="Metadata key=value pairs recorded with the session.",
)
@click.option(
    "--follow/--no-follow",
    default=False,
    show_default=True,
    help="Stream logs immediately.",
)
@click.pass_obj
def session_create(
    state: CLIState,
    commit: str,
    patch: Path | None,
    command: Iterable[str],
    metadata: Iterable[str],
    follow: bool,
) -> None:
    client = state.ensure_client()
    patch_data = patch.read_text() if patch else None
    request = SessionCreateRequest(
        commit=commit,
        commands=list(command),
        patch=patch_data,
        metadata=_parse_metadata(metadata),
    )
    session = client.create_session(request)
    click.echo(f"Session {session.session_id} created (status: {session.status}).")
    if follow:
        _stream_logs(client, session.session_id, output_format="text", follow=True)


@session.command("logs")
@click.argument("session_id")
@click.option("--follow/--no-follow", default=False, show_default=True, help="Stream live logs.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    show_default=True,
    help="Log output format.",
)
@click.pass_obj
def session_logs(state: CLIState, session_id: str, follow: bool, output_format: str) -> None:
    client = state.ensure_client()
    _stream_logs(client, session_id, output_format=output_format.lower(), follow=follow)


@session.command("debug")
@click.argument("session_id")
@click.option("--action", default="open", show_default=True, help="Debugger action to perform.")
@click.option("--payload", multiple=True, help="key=value pairs forwarded to the debug adapter.")
@click.pass_obj
def session_debug(state: CLIState, session_id: str, action: str, payload: Iterable[str]) -> None:
    client = state.ensure_client()
    request = DebugActionRequest(action=action, payload=_parse_metadata(payload))
    response = client.send_debug_action(session_id, request)
    suffix = f" ({response.detail})" if response.detail else ""
    click.echo(f"Action '{response.status}' accepted{suffix}.")


@artifact.command("download")
@click.argument("session_id")
@click.argument("artifact_id")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path, writable=True),
    required=True,
    help="Destination file path.",
)
@click.pass_obj
def artifact_download(state: CLIState, session_id: str, artifact_id: str, output: Path) -> None:
    client = state.ensure_client()
    metadata, content = client.download_artifact(session_id, artifact_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    click.echo(f"Downloaded {metadata.filename} ({metadata.size} bytes) to {output}.")


@agent.command("install")
@click.argument(
    "repository",
    default=Path("."),
    required=False,
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
)
@click.option("--force", is_flag=True, help="Rewrite AGENTS.md with only the Debug Server section.")
@click.option(
    "--section-heading",
    default="Debug Server Integration",
    show_default=True,
    help="Heading applied to the inserted AGENTS.md section.",
)
@click.pass_obj
def agent_install(
    state: CLIState,
    repository: Path,
    force: bool,
    section_heading: str,
) -> None:
    """Seed AGENTS.md and .codex scaffolding for Debug Server workflows."""

    if not repository.exists():
        raise click.BadParameter(f"Repository path {repository} does not exist.")
    if not repository.is_dir():
        raise click.BadParameter("Repository path must be a directory.")

    codex_created = _ensure_codex_scaffold(repository)
    block = render_agent_installation(state.settings, section_heading)
    agents_path = repository / "AGENTS.md"
    created_agents, updated_agents = _write_agents_section(agents_path, block, force=force)

    if created_agents:
        click.echo(f"Created {agents_path}.")
    elif updated_agents:
        click.echo(f"Updated {agents_path}.")
    else:
        click.echo(f"No changes required for {agents_path}.")

    if codex_created:
        click.echo("Created Debug Server scaffolding:")
        for entry in codex_created:
            click.echo(f"  - {entry}")


def _write_agents_section(path: Path, block: str, *, force: bool) -> tuple[bool, bool]:
    """Ensure the Debug Server section exists in AGENTS.md."""

    created = False
    updated = False
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    else:
        created = True

    if AGENT_SENTINEL_START in existing and AGENT_SENTINEL_END in existing:
        start = existing.index(AGENT_SENTINEL_START)
        end = existing.index(AGENT_SENTINEL_END) + len(AGENT_SENTINEL_END)
        new_content = existing[:start] + block + existing[end:]
    elif force:
        new_content = block
    elif existing.strip():
        new_content = existing.rstrip() + "\n\n" + block
    else:
        new_content = block

    if created or new_content != existing:
        path.write_text(new_content.rstrip() + "\n", encoding="utf-8")
        updated = not created and new_content != existing

    return created, updated


def _ensure_codex_scaffold(repository: Path) -> list[str]:
    """Create .codex metadata directories and SPEC.md if missing."""

    created: list[str] = []
    codex = repository / ".codex"
    tasks = codex / "tasks"
    done = codex / "done"
    for path in (codex, tasks, done):
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path.relative_to(repository)))

    spec = codex / "SPEC.md"
    if not spec.exists():
        spec.write_text(DEFAULT_SPEC_TEMPLATE, encoding="utf-8")
        created.append(str(spec.relative_to(repository)))

    return created


def _stream_logs(
    client: DebugServerClient,
    session_id: str,
    *,
    output_format: str,
    follow: bool,
) -> None:
    for entry in client.stream_session_logs(session_id, follow=follow):
        if output_format == "json":
            click.echo(
                json.dumps(
                    {
                        "message": entry.message,
                        "stream": entry.stream,
                        "timestamp": entry.timestamp.isoformat(),
                    }
                )
            )
        else:
            click.echo(entry.to_text())


def main() -> None:
    """Entry point for console_scripts."""

    app(standalone_mode=True)

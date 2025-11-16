"""Cloud launcher helpers for Terraform-driven Docker nodes."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import cycle
from pathlib import Path
from typing import cast

import click

_HUMAN_OVERRIDE_ENV = "DEBUG_SERVER_OPERATOR_ALLOW"
_AUTOMATION_SENTINELS = (
    "CI",
    "DEBUG_SERVER_AGENT",
    "DEBUG_SERVER_AUTOMATION",
)
_OPERATOR_KEY_ENV = "DEBUG_SERVER_OPERATOR_KEY"
_STATE_DIR_ENV = "DEBUG_SERVER_HOME"
_DEFAULT_STATE_SUBDIR = "cloud"


def _config_dir() -> Path:
    base = os.environ.get(_STATE_DIR_ENV)
    root = Path(base) if base else Path.home() / ".debug-server"
    return root / _DEFAULT_STATE_SUBDIR


def _normalize_bool(value: str | None) -> bool:
    if value is None:
        return False
    lowered = value.lower()
    return lowered in {"1", "true", "yes", "on"}


def require_human_operator() -> None:
    """Guard cloud commands from running in automated contexts."""

    if _normalize_bool(os.environ.get(_HUMAN_OVERRIDE_ENV)):
        return

    for name in _AUTOMATION_SENTINELS:
        if _normalize_bool(os.environ.get(name)):
            raise click.UsageError(
                "Cloud provisioning is disabled for agents and CI. "
                "Set DEBUG_SERVER_OPERATOR_ALLOW=1 only when running interactively."
            )


@dataclass(slots=True)
class TerraformInputs:
    provider: str
    stack_name: str
    docker_host: str
    app_image: str
    app_ports: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    token: str | None = None

    def to_tfvars(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "provider": self.provider,
            "stack_name": self.stack_name,
            "docker_host": self.docker_host,
            "app_image": self.app_image,
            "app_ports": self.app_ports,
            "app_env": self.env,
        }
        if self.token:
            payload["runner_token"] = self.token
        return payload


class TerraformInvoker:
    """Wrap calls to the terraform binary with helpful messaging."""

    def __init__(self, working_dir: Path) -> None:
        self.working_dir = working_dir

    def ensure_binary(self) -> None:
        if shutil.which("terraform") is None:
            raise click.UsageError(
                "Terraform is required to provision cloud nodes. Install it or use --dry-run to "
                "only render tfvars."
            )

    def run(self, *args: str) -> None:
        self.ensure_binary()
        command = ["terraform", *args]
        click.echo(f"Running {' '.join(command)} in {self.working_dir}...")
        subprocess.run(  # noqa: S603 - terraform arguments are constructed by the CLI
            command, cwd=self.working_dir, check=True
        )


class EncryptedStateStore:
    """Persist per-operator state with a simple XOR-based envelope."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or _config_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _key(self) -> bytes:
        raw = os.environ.get(_OPERATOR_KEY_ENV)
        if not raw:
            raise click.UsageError(
                "Set DEBUG_SERVER_OPERATOR_KEY to encrypt/decrypt cloud session state."
            )
        return raw.encode("utf-8")

    def _xor(self, payload: bytes, key: bytes) -> bytes:
        return bytes(b ^ k for b, k in zip(payload, cycle(key)))

    def save(self, name: str, payload: dict[str, object]) -> Path:
        key = self._key()
        data = json.dumps(payload, indent=2).encode("utf-8")
        encrypted = self._xor(data, key)
        encoded = base64.b64encode(encrypted)
        path = self.base_dir / f"{name}.json.enc"
        path.write_bytes(encoded)
        return path

    def load(self, name: str) -> dict[str, object]:
        path = self.base_dir / f"{name}.json.enc"
        if not path.exists():
            raise click.UsageError(f"No state stored for stack '{name}'.")
        key = self._key()
        decoded = base64.b64decode(path.read_bytes())
        decrypted = self._xor(decoded, key)
        parsed = json.loads(decrypted.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise click.UsageError("Stored state is corrupted or unreadable.")
        return cast(dict[str, object], parsed)

    def delete(self, name: str) -> None:
        path = self.base_dir / f"{name}.json.enc"
        if path.exists():
            path.unlink()


def _render_tfvars_file(target: Path, inputs: TerraformInputs) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(inputs.to_tfvars(), indent=2), encoding="utf-8")


def _parse_env_entries(entries: Iterable[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise click.BadParameter("Environment entries must be KEY=VALUE pairs.")
        key, value = entry.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def _parse_ports(entries: Iterable[str]) -> list[str]:
    ports: list[str] = []
    for entry in entries:
        if ":" not in entry:
            raise click.BadParameter("Ports must be HOST:CONTAINER mappings.")
        ports.append(entry)
    return ports


@click.group()
def cloud() -> None:
    """Provision Docker-capable VMs via Terraform."""

    require_human_operator()


@cloud.command("up")
@click.option("--provider", required=True, help="Provider label used by terraform stack directory.")
@click.option("--stack-name", default="debug-cloud", show_default=True)
@click.option("--docker-host", required=True, help="Docker host URI exposed by the provisioned VM.")
@click.option(
    "--image", "app_image", required=True, help="Application image to run via docker provider."
)
@click.option(
    "--env", "app_env", multiple=True, help="Environment variables propagated to the container."
)
@click.option(
    "--port",
    "app_port",
    multiple=True,
    help="Port mapping in HOST:CONTAINER format for the app container.",
)
@click.option(
    "--token",
    help="Optional runner/API token stored alongside the terraform state for follow-up commands.",
)
@click.option(
    "--stack-dir",
    type=click.Path(path_type=Path),
    help=(
        "Directory containing the terraform stack to run (defaults to "
        "infra/terraform/<provider>_docker_node)."
    ),
)
@click.option(
    "--dry-run/--apply",
    default=True,
    show_default=True,
    help="Render terraform.tfvars.json without invoking terraform.",
)
def cloud_up(
    provider: str,
    stack_name: str,
    docker_host: str,
    app_image: str,
    app_env: Iterable[str],
    app_port: Iterable[str],
    token: str | None,
    stack_dir: Path | None,
    dry_run: bool,
) -> None:
    """Render terraform variables and optionally apply the stack."""

    env_map = _parse_env_entries(app_env)
    ports = _parse_ports(app_port)
    inputs = TerraformInputs(
        provider=provider,
        stack_name=stack_name,
        docker_host=docker_host,
        app_image=app_image,
        app_ports=ports,
        env=env_map,
        token=token,
    )

    working_dir = stack_dir or Path("infra/terraform") / f"{provider}_docker_node"
    tfvars_path = working_dir / "terraform.tfvars.json"
    _render_tfvars_file(tfvars_path, inputs)

    store = EncryptedStateStore()
    state_payload = {
        "provider": provider,
        "stack_name": stack_name,
        "working_dir": str(working_dir),
        "tfvars": str(tfvars_path),
        "docker_host": docker_host,
        "app_image": app_image,
        "app_ports": ports,
        "app_env": env_map,
        "token_present": bool(token),
    }
    state_path = store.save(stack_name, state_payload)
    click.echo(f"Persisted encrypted state to {state_path}.")

    if dry_run:
        click.echo("Dry run complete; terraform commands were not executed.")
        return

    invoker = TerraformInvoker(working_dir=working_dir)
    invoker.run("init")
    invoker.run("plan")
    invoker.run("apply", "-auto-approve")


@cloud.command("destroy")
@click.option("--stack-name", required=True, help="Identifier used when creating the stack.")
@click.option(
    "--dry-run/--apply",
    default=True,
    show_default=True,
    help="Skip terraform destroy and only print intended actions.",
)
def cloud_destroy(stack_name: str, dry_run: bool) -> None:
    """Tear down a previously created cloud stack."""

    store = EncryptedStateStore()
    state = store.load(stack_name)
    working_dir_raw = state.get("working_dir")
    tfvars_raw = state.get("tfvars")
    if not isinstance(working_dir_raw, str) or not isinstance(tfvars_raw, str):
        raise click.UsageError("Stored state is missing terraform paths.")
    working_dir = Path(working_dir_raw)
    tfvars_path = Path(tfvars_raw)
    if not tfvars_path.exists():
        click.echo("tfvars file missing; re-rendering from stored state.")
        app_ports_raw = state.get("app_ports", [])
        env_raw = state.get("app_env", {})
        app_ports = [str(port) for port in app_ports_raw] if isinstance(app_ports_raw, list) else []
        app_env = {str(k): str(v) for k, v in env_raw.items()} if isinstance(env_raw, dict) else {}
        provider = str(state.get("provider", ""))
        docker_host = str(state.get("docker_host", ""))
        app_image = str(state.get("app_image", ""))
        inputs = TerraformInputs(
            provider=provider,
            stack_name=stack_name,
            docker_host=docker_host,
            app_image=app_image,
            app_ports=app_ports,
            env=app_env,
            token=None,
        )
        _render_tfvars_file(tfvars_path, inputs)

    if dry_run:
        click.echo(f"Would run 'terraform destroy' in {working_dir} using {tfvars_path}.")
        return

    invoker = TerraformInvoker(working_dir=working_dir)
    invoker.run("destroy", "-auto-approve")
    store.delete(stack_name)
    click.echo(f"Destroyed stack '{stack_name}' and removed state cache.")

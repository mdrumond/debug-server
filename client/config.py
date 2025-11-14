"""Configuration helpers shared across CLI and SDK surfaces."""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

_CONFIG_FILENAME = "config.toml"
_DEFAULT_BASE_URL = "http://127.0.0.1:8000"
_ENV_HOME = "DEBUG_SERVER_HOME"
_ENV_URL = "DEBUG_SERVER_URL"
_ENV_TOKEN = "DEBUG_SERVER_TOKEN"
_ENV_VERIFY = "DEBUG_SERVER_VERIFY_TLS"


@dataclass(slots=True)
class ClientConfig:
    """Represents persisted CLI settings."""

    base_url: str = _DEFAULT_BASE_URL
    token: str | None = None
    verify_tls: bool = True

    def merged(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        verify_tls: bool | None = None,
    ) -> ClientConfig:
        """Return a copy that applies CLI/env overrides."""

        return replace(
            self,
            base_url=base_url or self.base_url,
            token=token or self.token,
            verify_tls=self.verify_tls if verify_tls is None else verify_tls,
        )


def _config_dir(create: bool = False) -> Path:
    custom = os.environ.get(_ENV_HOME)
    base = Path(custom) if custom else Path.home() / ".debug-server"
    if create:
        base.mkdir(parents=True, exist_ok=True)
    return base


def config_path() -> Path:
    """Return the path to the persisted CLI configuration."""

    return _config_dir(create=False) / _CONFIG_FILENAME


def load_client_config() -> ClientConfig:
    """Load configuration from disk + environment overrides."""

    data: dict[str, Any] = {}
    path = config_path()
    if path.exists():
        data = tomllib.loads(path.read_text())

    config = ClientConfig(
        base_url=str(data.get("base_url", _DEFAULT_BASE_URL)),
        token=data.get("token"),
        verify_tls=bool(data.get("verify_tls", True)),
    )

    env_url = os.environ.get(_ENV_URL)
    env_token = os.environ.get(_ENV_TOKEN)
    env_verify = os.environ.get(_ENV_VERIFY)
    verify_tls: bool | None = None
    if env_verify is not None:
        verify_tls = env_verify not in {"0", "false", "False"}

    return config.merged(base_url=env_url, token=env_token, verify_tls=verify_tls)


def save_client_config(config: ClientConfig) -> Path:
    """Persist configuration to ~/.debug-server/config.toml."""

    base = _config_dir(create=True)
    path = base / _CONFIG_FILENAME
    lines = [
        f"base_url = {json.dumps(config.base_url)}",
        f"token = {json.dumps(config.token or '')}",
        f"verify_tls = {'true' if config.verify_tls else 'false'}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

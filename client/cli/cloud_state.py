"""Inventory helpers for managing cloud-launched debug servers."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from .cloud import EncryptedStateStore


def _utc_timestamp() -> str:
    # Use timezone-aware UTC datetime and format as ISO 8601 with trailing "Z"
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    status: str
    owner: str | None = None
    token: str | None = None
    updated_at: str = field(default_factory=_utc_timestamp)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "owner": self.owner,
            "token": self.token,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SessionRecord:
        session_id = payload.get("session_id")
        if session_id is None:
            raise click.UsageError("Missing required field 'session_id' in session record payload.")

        return cls(
            session_id=str(session_id),
            status=str(payload.get("status", "unknown")),
            owner=payload.get("owner") if payload.get("owner") is not None else None,
            token=payload.get("token") if payload.get("token") is not None else None,
            updated_at=str(payload.get("updated_at", _utc_timestamp())),
        )


@dataclass(slots=True)
class ServerRecord:
    stack_name: str
    provider: str
    docker_host: str
    app_image: str
    app_ports: list[str]
    app_env: dict[str, str]
    token: str | None
    working_dir: str
    tfvars: str
    created_at: str = field(default_factory=_utc_timestamp)
    updated_at: str = field(default_factory=_utc_timestamp)
    sessions: dict[str, SessionRecord] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stack_name": self.stack_name,
            "provider": self.provider,
            "docker_host": self.docker_host,
            "app_image": self.app_image,
            "app_ports": self.app_ports,
            "app_env": self.app_env,
            "token": self.token,
            "working_dir": self.working_dir,
            "tfvars": self.tfvars,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sessions": {sid: record.to_dict() for sid, record in self.sessions.items()},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ServerRecord:
        sessions_raw = payload.get("sessions", {})
        sessions: dict[str, SessionRecord] = {}
        if isinstance(sessions_raw, dict):
            for session_id, record in sessions_raw.items():
                if isinstance(record, dict):
                    sessions[session_id] = SessionRecord.from_dict(record)

        stack_name = payload.get("stack_name")
        if stack_name is None:
            raise click.UsageError("Missing required field 'stack_name' in server record payload.")

        return cls(
            stack_name=str(stack_name),
            provider=str(payload.get("provider", "")),
            docker_host=str(payload.get("docker_host", "")),
            app_image=str(payload.get("app_image", "")),
            app_ports=[str(port) for port in payload.get("app_ports", [])],
            app_env={str(k): str(v) for k, v in payload.get("app_env", {}).items()},
            token=payload.get("token") if payload.get("token") is not None else None,
            working_dir=str(payload.get("working_dir", "")),
            tfvars=str(payload.get("tfvars", "")),
            created_at=str(payload.get("created_at", _utc_timestamp())),
            updated_at=str(payload.get("updated_at", _utc_timestamp())),
            sessions=sessions,
        )


class CloudInventory:
    """Manage multi-stack state using the encrypted local store."""

    _SCHEMA_VERSION = 1
    _INVENTORY_NAME = "inventory"

    def __init__(self, store: EncryptedStateStore | None = None) -> None:
        if store is None:
            from .cloud import EncryptedStateStore

            self.store = EncryptedStateStore()
        else:
            self.store = store

    def _inventory_path(self) -> Path:
        return self.store.base_dir / f"{self._INVENTORY_NAME}.json.enc"

    def _default(self) -> dict[str, Any]:
        return {"version": self._SCHEMA_VERSION, "servers": {}}

    def _load_raw(self) -> dict[str, Any]:
        path = self._inventory_path()
        if not path.exists():
            return self._default()
        try:
            data = self.store.load(self._INVENTORY_NAME)
        except click.UsageError as exc:
            raise click.UsageError(
                "Failed to decrypt cloud inventory. Ensure DEBUG_SERVER_OPERATOR_KEY matches the key "
                "used when the inventory was created and that the file is not corrupted."
            ) from exc
        if not isinstance(data, dict):
            return self._default()
        if data.get("version") != self._SCHEMA_VERSION:
            data["version"] = self._SCHEMA_VERSION
        if "servers" not in data or not isinstance(data["servers"], dict):
            data["servers"] = {}
        return data

    def _persist(self, payload: dict[str, Any]) -> None:
        self.store.save(self._INVENTORY_NAME, payload)

    def record_server(self, record: ServerRecord) -> None:
        inventory = self._load_raw()
        servers = inventory["servers"]
        record.updated_at = _utc_timestamp()
        servers[record.stack_name] = record.to_dict()
        self._persist(inventory)

    def remove_server(self, stack_name: str) -> None:
        inventory = self._load_raw()
        servers = inventory["servers"]
        if stack_name in servers:
            del servers[stack_name]
            self._persist(inventory)

    def list_servers(self) -> list[ServerRecord]:
        inventory = self._load_raw()
        return [
            ServerRecord.from_dict(raw)
            for raw in inventory.get("servers", {}).values()
            if isinstance(raw, dict)
        ]

    def get_server(self, stack_name: str) -> ServerRecord | None:
        inventory = self._load_raw()
        raw = inventory.get("servers", {}).get(stack_name)
        if isinstance(raw, dict):
            return ServerRecord.from_dict(raw)
        return None

    def upsert_session(self, stack_name: str, record: SessionRecord) -> None:
        inventory = self._load_raw()
        servers = inventory.get("servers", {})
        if stack_name not in servers:
            raise click.UsageError(
                f"Stack '{stack_name}' is not tracked. Run 'cloud up' to register it first."
            )
        server = servers[stack_name]
        if not isinstance(server, dict):
            server = {}
            servers[stack_name] = server
        sessions = server.setdefault("sessions", {})
        if not isinstance(sessions, dict):
            sessions = {}
            server["sessions"] = sessions
        record.updated_at = _utc_timestamp()
        sessions[record.session_id] = record.to_dict()
        server["updated_at"] = record.updated_at
        self._persist(inventory)

    def remove_session(self, stack_name: str, session_id: str) -> None:
        inventory = self._load_raw()
        servers = inventory.get("servers", {})
        server = servers.get(stack_name)
        if not isinstance(server, dict):
            raise click.UsageError(
                f"Stack '{stack_name}' is not tracked. Run 'cloud up' to register it first."
            )
        sessions = server.get("sessions")
        if isinstance(sessions, dict) and session_id in sessions:
            del sessions[session_id]
            server["updated_at"] = _utc_timestamp()
            self._persist(inventory)

"""Debugger tunnel orchestration utilities."""

from __future__ import annotations

import secrets
import socket
from dataclasses import dataclass
from datetime import UTC, datetime

from debug_server.db import MetadataStore


@dataclass(slots=True)
class DebuggerTunnel:
    """Represents an authenticated debugger tunnel endpoint."""

    session_id: str
    kind: str
    host: str
    port: int
    token: str
    created_at: datetime

    @property
    def uri(self) -> str:
        return f"ws://{self.host}:{self.port}/debug/{self.session_id}/{self.kind}"

    def to_payload(self) -> dict[str, str | int]:
        return {
            "session_id": self.session_id,
            "kind": self.kind,
            "host": self.host,
            "port": self.port,
            "token": self.token,
            "uri": self.uri,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class DebuggerTunnelState:
    """Lightweight snapshot of a tunnel stored in metadata."""

    last_event: str | None
    payload: dict[str, object]


class DebuggerTunnelManager:
    """Allocate ports and bearer tokens for debugger tunnels."""

    def __init__(self, metadata_store: MetadataStore, host: str = "127.0.0.1") -> None:
        self.metadata_store = metadata_store
        self.host = host
        self._tunnels: dict[tuple[str, str], DebuggerTunnel] = {}

    def open_tunnel(self, session_id: str, kind: str, port: int | None = None) -> DebuggerTunnel:
        tunnel = DebuggerTunnel(
            session_id=session_id,
            kind=kind,
            host=self.host,
            port=port or self._allocate_port(),
            token=secrets.token_urlsafe(16),
            created_at=datetime.now(UTC),
        )
        self._tunnels[(session_id, kind)] = tunnel
        self.metadata_store.update_debugger_state(
            session_id,
            last_event="tunnel-created",
            payload={"tunnel": tunnel.to_payload()},
        )
        return tunnel

    def close_tunnel(self, session_id: str, kind: str) -> None:
        self._tunnels.pop((session_id, kind), None)
        self.metadata_store.update_debugger_state(
            session_id,
            last_event="tunnel-closed",
            payload={"tunnel": None},
        )

    def get_state(self, session_id: str) -> DebuggerTunnelState | None:
        state = self.metadata_store.get_debugger_state(session_id)
        if state is None:
            return None
        return DebuggerTunnelState(last_event=state.last_event, payload=dict(state.payload))

    @staticmethod
    def _allocate_port() -> int:
        with socket.socket() as sock:
            sock.bind(("", 0))
            return int(sock.getsockname()[1])


__all__ = ["DebuggerTunnel", "DebuggerTunnelManager", "DebuggerTunnelState"]

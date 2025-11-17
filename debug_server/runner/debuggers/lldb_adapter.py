"""Adapter for launching binaries under lldb-server."""

from __future__ import annotations

from typing import Any

from debug_server.db import MetadataStore
from debug_server.runner import CommandSpec, WorkerSupervisor

from .debugpy_adapter import DebuggerLaunch
from .gdb_adapter import NativeDebuggerLaunchRequest
from .tunnel import DebuggerTunnelManager


class LLDBAdapter:
    """Prepare lldb-server command invocations for the runner."""

    def __init__(
        self,
        supervisor: WorkerSupervisor,
        tunnel_manager: DebuggerTunnelManager,
        metadata_store: MetadataStore,
    ) -> None:
        self.supervisor = supervisor
        self.tunnel_manager = tunnel_manager
        self.metadata_store = metadata_store

    def start(
        self, session_id: str, lease: Any, request: NativeDebuggerLaunchRequest
    ) -> DebuggerLaunch:
        tunnel = self.tunnel_manager.open_tunnel(session_id, "lldb")
        self.metadata_store.update_debugger_state(
            session_id,
            last_event="tunnel-ready",
            payload={"tunnel": tunnel.to_payload()},
        )
        env = dict(request.env or {})
        env.setdefault("DEBUG_SESSION_TOKEN", tunnel.token)
        env.setdefault("DEBUG_SESSION_URI", tunnel.uri)
        argv = [
            "lldb-server",
            "gdbserver",
            f"{tunnel.host}:{tunnel.port}",
            request.binary,
            *request.args,
        ]
        command = CommandSpec(argv=argv, env=env, cwd=request.cwd, log_name="debugger")
        self.supervisor.run_command(session_id=session_id, spec=command, lease=lease)
        return DebuggerLaunch(tunnel=tunnel, command=command)


__all__ = ["LLDBAdapter"]

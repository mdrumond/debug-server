from __future__ import annotations

from debug_server.db import MetadataStore
from debug_server.runner.debuggers import DebuggerTunnelManager


def test_tunnel_registration(metadata_store: MetadataStore) -> None:
    manager = DebuggerTunnelManager(metadata_store, host="127.0.0.1")
    tunnel = manager.open_tunnel("sess-2", "debugpy")
    assert tunnel.host == "127.0.0.1"
    assert tunnel.port > 0
    assert tunnel.token
    assert tunnel.uri.startswith("ws://127.0.0.1:")

    state = manager.get_state("sess-2")
    assert state is not None
    assert state.last_event == "tunnel-created"
    assert state.payload["tunnel"]["port"] == tunnel.port

    manager.close_tunnel("sess-2", "debugpy")
    closed = metadata_store.get_debugger_state("sess-2")
    assert closed is not None
    assert closed.last_event == "tunnel-closed"

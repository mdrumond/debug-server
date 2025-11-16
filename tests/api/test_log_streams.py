from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from debug_server.api.streams import LogManager
from debug_server.db import MetadataStore


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _prepare_session(store: MetadataStore) -> tuple[str, str]:
    repository = store.upsert_repository(
        name="demo",
        remote_url="https://example.com/demo.git",
        default_branch="main",
    )
    _, token_value = store.create_token("runner", scopes=["sessions:read", "artifacts:read"])
    session = store.create_session(
        repository_id=repository.id or 0,
        commit_sha="abc1234",
        worktree_id=None,
        requested_by="tester",
        token_id=None,
    )
    return session.id, token_value


def test_log_websocket_replays_history(client: TestClient, metadata_store: MetadataStore) -> None:
    session_id, token = _prepare_session(metadata_store)
    log_manager: LogManager = client.app.state.context.log_manager
    log_manager.append(session_id, "first line\n")

    with client.websocket_connect(
        f"/sessions/{session_id}/logs", headers=_auth_header(token)
    ) as websocket:
        first = websocket.receive_json()
        assert first["text"] == "first line\n"
        log_manager.append(session_id, "second line\n", stream="stderr")
        second = websocket.receive_json()
        assert second["stream"] == "stderr"
        assert second["text"] == "second line\n"


def test_log_websocket_missing_session(client: TestClient, metadata_store: MetadataStore) -> None:
    _, token = metadata_store.create_token("runner", scopes=["sessions:read", "artifacts:read"])
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/sessions/missing/logs", headers=_auth_header(token)):
            pass

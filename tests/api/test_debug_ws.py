from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from debug_server.api.streams import DebugBroker
from debug_server.db import MetadataStore


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _prepare_session(store: MetadataStore) -> tuple[str, str]:
    repository = store.upsert_repository(
        name="demo",
        remote_url="https://example.com/demo.git",
        default_branch="main",
    )
    _, token_value = store.create_token("runner", scopes=["sessions:write", "sessions:read"])
    session = store.create_session(
        repository_id=repository.id or 0,
        commit_sha="abc1234",
        worktree_id=None,
        requested_by="tester",
        token_id=None,
    )
    return session.id, token_value


def test_debug_websocket_broadcast(client: TestClient, metadata_store: MetadataStore) -> None:
    session_id, token = _prepare_session(metadata_store)
    broker: DebugBroker = client.app.state.context.debug_broker

    with client.websocket_connect(
        f"/sessions/{session_id}/debug", headers=_auth_header(token)
    ) as websocket:
        websocket.send_json({"action": "step", "thread": "main"})
        ack = websocket.receive_json()
        assert ack["kind"] == "ack"
        assert ack["payload"]["action"] == "step"

        broker.publish(session_id, "event", {"reason": "breakpoint"})
        event = websocket.receive_json()
        assert event["kind"] == "event"
        assert event["payload"]["reason"] == "breakpoint"


def test_debug_websocket_does_not_drop_events(
    client: TestClient, metadata_store: MetadataStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id, token = _prepare_session(metadata_store)
    broker: DebugBroker = client.app.state.context.debug_broker
    broker.publish(session_id, "history", {"seq": 1})

    original_subscribe_with_history = broker.subscribe_with_history

    def _subscribe_with_mid_event(session: str):
        queue, loop, unsubscribe, history = original_subscribe_with_history(session)
        broker.publish(session, "mid", {"seq": 2})
        return queue, loop, unsubscribe, history

    monkeypatch.setattr(broker, "subscribe_with_history", _subscribe_with_mid_event)

    with client.websocket_connect(
        f"/sessions/{session_id}/debug", headers=_auth_header(token)
    ) as websocket:
        history = websocket.receive_json()
        assert history["kind"] == "history"
        mid = websocket.receive_json()
        assert mid["kind"] == "mid"


def test_debug_websocket_requires_session(
    client: TestClient, metadata_store: MetadataStore
) -> None:
    _, token = metadata_store.create_token("runner", scopes=["sessions:write"])
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/sessions/missing/debug", headers=_auth_header(token)):
            pass

"""Debugger control streaming endpoints."""

# ruff: noqa: B008

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from debug_server.api.auth import require_websocket_token
from debug_server.api.context import AppContext, get_websocket_context
from debug_server.api.streams import DebugBroker, DebugEvent

router = APIRouter(prefix="/sessions", tags=["debug"])


def _serialize_event(event: DebugEvent, session_id: str) -> dict[str, object]:
    return {
        "session_id": session_id,
        "kind": event.kind,
        "payload": event.payload,
        "timestamp": event.timestamp.isoformat(),
    }


@router.websocket("/{session_id}/debug")
async def debug_stream(websocket: WebSocket, session_id: str) -> None:
    context: AppContext = get_websocket_context(websocket)
    await require_websocket_token(websocket, context, scopes=["sessions:write"])
    session = context.metadata_store.get_session(session_id)
    if session is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    broker = _get_debug_broker(context)
    queue, _, unsubscribe, history = broker.subscribe_with_history(session_id)
    for event in history:
        await websocket.send_json(_serialize_event(event, session_id))
    try:
        while True:
            message_task = asyncio.create_task(websocket.receive_json())
            event_task = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait(
                {message_task, event_task}, return_when=asyncio.FIRST_COMPLETED
            )

            if event_task in done:
                queue_event = event_task.result()
                if queue_event is None:
                    break
                await websocket.send_json(_serialize_event(queue_event, session_id))
            else:
                event_task.cancel()

            if message_task in done:
                incoming = message_task.result()
                await websocket.send_json(
                    {
                        "session_id": session_id,
                        "kind": "ack",
                        "payload": incoming,
                    }
                )
            else:
                message_task.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe()


def _get_debug_broker(context: AppContext) -> DebugBroker:
    if context.debug_broker is None:
        context.debug_broker = DebugBroker()
    return context.debug_broker


__all__ = ["router"]

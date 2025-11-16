"""Log streaming endpoints."""

# ruff: noqa: B008

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from debug_server.api.auth import require_websocket_token
from debug_server.api.context import AppContext, get_websocket_context
from debug_server.api.streams import LogEvent, LogManager

router = APIRouter(prefix="/sessions", tags=["logs"])


def _serialize_event(event: LogEvent) -> dict[str, str]:
    return {
        "stream": event.stream,
        "text": event.text,
        "timestamp": event.timestamp.isoformat(),
    }


@router.websocket("/{session_id}/logs")
async def stream_logs(websocket: WebSocket, session_id: str) -> None:
    context: AppContext = get_websocket_context(websocket)
    await require_websocket_token(websocket, context, scopes=["sessions:read", "artifacts:read"])
    session = context.metadata_store.get_session(session_id)
    if session is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    log_manager = _get_log_manager(context)
    history = log_manager.history(session_id)
    for event in history:
        await websocket.send_json(_serialize_event(event))
    queue, _, unsubscribe = log_manager.subscribe(session_id)
    try:
        while True:
            queue_event = await queue.get()
            if queue_event is None:
                break
            await websocket.send_json(_serialize_event(queue_event))
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe()


def _get_log_manager(context: AppContext) -> LogManager:
    if context.log_manager is None:
        context.log_manager = LogManager()
    return context.log_manager


__all__ = ["router"]

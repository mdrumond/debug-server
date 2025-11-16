"""In-memory stream brokers used by API routers."""

from __future__ import annotations

import asyncio
from asyncio import AbstractEventLoop
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any

try:  # pragma: no cover - Python 3.11+
    from datetime import UTC
except ImportError:  # pragma: no cover - fallback for <3.11
    from datetime import timezone as _timezone

    UTC = _timezone.utc  # noqa: UP017


@dataclass(slots=True)
class LogEvent:
    stream: str
    text: str
    timestamp: datetime


@dataclass(slots=True)
class DebugEvent:
    kind: str
    payload: dict[str, Any]
    timestamp: datetime


LogSubscription = tuple[asyncio.Queue[LogEvent | None], AbstractEventLoop, Callable[[], None]]
DebugSubscription = tuple[asyncio.Queue[DebugEvent | None], AbstractEventLoop, Callable[[], None]]


class LogManager:
    """Manage in-memory log fan-out for sessions."""

    def __init__(self) -> None:
        self._history: dict[str, list[LogEvent]] = defaultdict(list)
        self._subscribers: dict[
            str, list[tuple[asyncio.Queue[LogEvent | None], AbstractEventLoop]]
        ] = defaultdict(list)
        self._lock = Lock()

    def append(self, session_id: str, text: str, *, stream: str = "stdout") -> LogEvent:
        event = LogEvent(stream=stream, text=text, timestamp=datetime.now(UTC))
        with self._lock:
            self._history[session_id].append(event)
            subscribers = list(self._subscribers.get(session_id, []))
        for queue, loop in subscribers:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        return event

    def history(self, session_id: str) -> list[LogEvent]:
        with self._lock:
            return list(self._history.get(session_id, []))

    def subscribe(self, session_id: str) -> LogSubscription:
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[LogEvent | None] = asyncio.Queue()
        with self._lock:
            self._subscribers[session_id].append((queue, loop))

        def _unsubscribe() -> None:
            with self._lock:
                subscribers = self._subscribers.get(session_id)
                if subscribers and (queue, loop) in subscribers:
                    subscribers.remove((queue, loop))
            loop.call_soon_threadsafe(queue.put_nowait, None)

        return queue, loop, _unsubscribe


class DebugBroker:
    """Fan-out channel for debugger control and events."""

    def __init__(self) -> None:
        self._history: dict[str, list[DebugEvent]] = defaultdict(list)
        self._subscribers: dict[
            str, list[tuple[asyncio.Queue[DebugEvent | None], AbstractEventLoop]]
        ] = defaultdict(list)
        self._lock = Lock()

    def publish(self, session_id: str, kind: str, payload: dict[str, Any]) -> DebugEvent:
        event = DebugEvent(kind=kind, payload=dict(payload), timestamp=datetime.now(UTC))
        with self._lock:
            self._history[session_id].append(event)
            subscribers = list(self._subscribers.get(session_id, []))
        for queue, loop in subscribers:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        return event

    def history(self, session_id: str) -> list[DebugEvent]:
        with self._lock:
            return list(self._history.get(session_id, []))

    def subscribe(self, session_id: str) -> DebugSubscription:
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[DebugEvent | None] = asyncio.Queue()
        with self._lock:
            self._subscribers[session_id].append((queue, loop))

        def _unsubscribe() -> None:
            with self._lock:
                subscribers = self._subscribers.get(session_id)
                if subscribers and (queue, loop) in subscribers:
                    subscribers.remove((queue, loop))
            loop.call_soon_threadsafe(queue.put_nowait, None)

        return queue, loop, _unsubscribe


__all__ = ["DebugBroker", "DebugEvent", "LogEvent", "LogManager"]

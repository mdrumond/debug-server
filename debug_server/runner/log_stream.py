"""Structured log streaming helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Queue
from threading import Lock
from typing import cast

try:  # pragma: no cover - Python 3.11+
    from datetime import UTC
except ImportError:  # pragma: no cover - fallback for <3.11
    from datetime import timezone as _timezone

    UTC = _timezone.utc  # noqa: UP017

__all__ = ["LogChunk", "LogStream", "LogSubscription"]

_SENTINEL = object()


@dataclass(slots=True)
class LogChunk:
    """A single log event."""

    stream: str
    text: str
    timestamp: datetime


class LogSubscription:
    """Iterator wrapper around a queue-backed subscription."""

    def __init__(self, queue: Queue[LogChunk | object], closer: Callable[[], None]):
        self._queue = queue
        self._closer = closer
        self._closed = False

    def __iter__(self) -> Iterator[LogChunk]:
        while True:
            item = self._queue.get()
            if item is _SENTINEL:
                break
            yield cast(LogChunk, item)
        self._closed = True

    def close(self) -> None:
        if not self._closed:
            self._closer()
            self._closed = True


class LogStream:
    """Write logs to disk while notifying observers."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")
        self._listeners: list[Callable[[LogChunk], None]] = []
        self._queue_listeners: dict[int, Queue[LogChunk | object]] = {}
        self._lock = Lock()
        self._token = 0

    def __enter__(self) -> LogStream:  # noqa: D401 - context manager
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            if self._handle.closed:
                return
            self._handle.flush()
            self._handle.close()
            for queue in self._queue_listeners.values():
                queue.put(_SENTINEL)
            self._queue_listeners.clear()
            self._listeners.clear()

    def write(self, text: str, stream: str = "stdout") -> LogChunk:
        chunk = LogChunk(stream=stream, text=text, timestamp=datetime.now(UTC))
        with self._lock:
            self._handle.write(text)
            self._handle.flush()
            listeners = list(self._listeners)
            queue_values = list(self._queue_listeners.values())
        for listener in listeners:
            listener(chunk)
        for queue in queue_values:
            queue.put(chunk)
        return chunk

    def add_listener(self, callback: Callable[[LogChunk], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(callback)

        def _remove() -> None:
            with self._lock:
                try:
                    self._listeners.remove(callback)
                except ValueError:  # pragma: no cover - already removed
                    pass

        return _remove

    def follow(self) -> LogSubscription:
        """Return an iterator that yields log chunks as they arrive."""

        with self._lock:
            token = self._token
            self._token += 1
            queue: Queue[LogChunk | object] = Queue()
            self._queue_listeners[token] = queue

        def _close() -> None:
            with self._lock:
                queue = self._queue_listeners.pop(token, None)
            if queue is not None:
                queue.put(_SENTINEL)

        return LogSubscription(queue, _close)

    def replay(self) -> Iterable[LogChunk]:
        """Yield historical log chunks from disk."""

        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                yield LogChunk(stream="file", text=line, timestamp=datetime.now(UTC))

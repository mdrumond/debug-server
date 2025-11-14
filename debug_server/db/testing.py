"""Testing helpers for the metadata store."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import Session

from .service import MetadataStore
from .session import create_in_memory_engine, init_db


def create_test_store() -> MetadataStore:
    """Create an in-memory metadata store for unit tests."""

    engine = create_in_memory_engine()
    init_db(engine)
    return MetadataStore(engine)


@contextmanager
def in_memory_session() -> Iterator[Session]:
    """Provide a temporary SQLModel session backed by an in-memory DB."""

    engine = create_in_memory_engine()
    init_db(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


__all__ = ["create_test_store", "in_memory_session"]

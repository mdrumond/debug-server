"""Engine helpers and session utilities."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

DEFAULT_DB_PATH = Path(os.getenv("DEBUG_SERVER_DB_PATH", ".artifacts/data/metadata.db"))


def get_default_database_url() -> str:
    """Return the default SQLite URL, ensuring the directory exists."""

    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DB_PATH}"


def create_engine_from_url(url: str | None = None):
    """Create a SQLModel engine with sane SQLite defaults."""

    database_url = url or os.getenv("DEBUG_SERVER_DB_URL") or get_default_database_url()
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}
    engine = create_engine(database_url, connect_args=connect_args)
    return engine


def create_in_memory_engine():
    """Create an in-memory SQLite engine for tests."""

    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def init_db(engine) -> None:
    """Create all tables for metadata."""

    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(engine) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""

    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "create_engine_from_url",
    "create_in_memory_engine",
    "get_default_database_url",
    "init_db",
    "session_scope",
]

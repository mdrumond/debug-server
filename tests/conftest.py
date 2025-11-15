"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from debug_server.db import MetadataStore
from debug_server.db.testing import create_test_store


@pytest.fixture()
def metadata_store() -> MetadataStore:
    return create_test_store()

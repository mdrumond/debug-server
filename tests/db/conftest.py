"""Fixtures for DB tests."""

from __future__ import annotations

import pytest

from debug_server.db.testing import create_test_store


@pytest.fixture()
def metadata_store():
    return create_test_store()

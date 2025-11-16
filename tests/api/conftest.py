from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from debug_server.api.context import AppContext
from debug_server.api.main import create_app
from debug_server.db.testing import create_test_store


@pytest.fixture()
def metadata_store():
    return create_test_store()


@pytest.fixture()
def app(metadata_store):
    context = AppContext(metadata_store=metadata_store)
    return create_app(context)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client

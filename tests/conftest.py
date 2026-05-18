from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bot.config import get_settings
from bot.main import app


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Each test gets a clean, cached Settings built from current env."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

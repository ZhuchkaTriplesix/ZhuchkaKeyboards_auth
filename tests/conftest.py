"""Pytest hooks and shared fixtures."""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from src.main import app


def pytest_collection_modifyitems(_config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("INTEGRATION_TEST"):
        return
    skip = pytest.mark.skip(reason="set INTEGRATION_TEST=1 for integration tests")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c

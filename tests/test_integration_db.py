"""Integration tests (PostgreSQL + migrations). Run: INTEGRATION_TEST=1 pytest tests/ -m integration -v"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.mark.integration
def test_health_ready(client: TestClient):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json().get("status") == "ready"


@pytest.mark.integration
def test_oauth_token_invalid_client(client: TestClient):
    r = client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "no-such-client",
            "client_secret": "secret",
        },
    )
    assert r.status_code == 401
    body = r.json()
    assert body.get("error") == "invalid_client"

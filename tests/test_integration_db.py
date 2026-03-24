"""Integration tests (PostgreSQL + migrations). Run: INTEGRATION_TEST=1 pytest tests/ -m integration -v"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

# Matches config.ini.example defaults after bootstrap (`_ensure_bootstrap_client`).
_DEV_CLIENT_ID = "zhuchka-dev"
_DEV_CLIENT_SECRET = "change-me-dev-only"


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


@pytest.mark.integration
def test_oidc_discovery(client: TestClient):
    r = client.get("/.well-known/openid-configuration")
    assert r.status_code == 200
    body = r.json()
    assert "issuer" in body
    assert "token_endpoint" in body
    assert "userinfo_endpoint" in body
    assert body["userinfo_endpoint"].endswith("/oauth/userinfo")
    assert body.get("introspection_endpoint", "").endswith("/oauth/introspect")


@pytest.mark.integration
def test_jwks(client: TestClient):
    r = client.get("/.well-known/jwks.json")
    assert r.status_code == 200
    assert "keys" in r.json()
    assert isinstance(r.json()["keys"], list)


@pytest.mark.integration
def test_oauth_token_unsupported_grant_type(client: TestClient):
    r = client.post(
        "/oauth/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": _DEV_CLIENT_ID,
            "client_secret": _DEV_CLIENT_SECRET,
        },
    )
    assert r.status_code == 400
    assert r.json().get("error") == "unsupported_grant_type"


@pytest.mark.integration
def test_oauth_token_refresh_requires_refresh_token(client: TestClient):
    r = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": _DEV_CLIENT_ID,
            "client_secret": _DEV_CLIENT_SECRET,
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body.get("error") == "invalid_request"


@pytest.mark.integration
def test_oauth_userinfo_requires_bearer(client: TestClient):
    r = client.get("/oauth/userinfo")
    assert r.status_code == 401
    body = r.json()
    assert body.get("code") == "missing_bearer"
    assert "message" in body


@pytest.mark.integration
def test_oauth_introspect_requires_token(client: TestClient):
    r = client.post(
        "/oauth/introspect",
        data={
            "client_id": _DEV_CLIENT_ID,
            "client_secret": _DEV_CLIENT_SECRET,
        },
    )
    assert r.status_code == 400
    assert r.json().get("error") == "invalid_request"


@pytest.mark.integration
def test_oauth_introspect_invalid_client(client: TestClient):
    r = client.post(
        "/oauth/introspect",
        data={"token": "x", "client_id": "no-such", "client_secret": "nope"},
    )
    assert r.status_code == 401
    assert r.json().get("error") == "invalid_client"


@pytest.mark.integration
def test_oauth_introspect_rejects_public_client(client: TestClient):
    r = client.post(
        "/oauth/introspect",
        data={"token": "x", "client_id": "zhuchka-market-web"},
    )
    assert r.status_code == 401


@pytest.mark.integration
def test_oauth_introspect_client_credentials_access_token(client: TestClient):
    tr = client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": _DEV_CLIENT_ID,
            "client_secret": _DEV_CLIENT_SECRET,
        },
    )
    assert tr.status_code == 200
    at = tr.json()["access_token"]
    ir = client.post(
        "/oauth/introspect",
        data={
            "token": at,
            "token_type_hint": "access_token",
            "client_id": _DEV_CLIENT_ID,
            "client_secret": _DEV_CLIENT_SECRET,
        },
    )
    assert ir.status_code == 200
    body = ir.json()
    assert body.get("active") is True
    assert body.get("sub") == f"client:{_DEV_CLIENT_ID}"
    assert body.get("token_type") == "Bearer"
    assert "exp" in body


@pytest.mark.integration
def test_oauth_introspect_unknown_token_inactive(client: TestClient):
    ir = client.post(
        "/oauth/introspect",
        data={
            "token": "not-a-valid-token",
            "client_id": _DEV_CLIENT_ID,
            "client_secret": _DEV_CLIENT_SECRET,
        },
    )
    assert ir.status_code == 200
    assert ir.json() == {"active": False}

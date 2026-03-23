"""Smoke tests for public routes (no admin token, no DB assumptions where possible)."""

from __future__ import annotations

from starlette.testclient import TestClient


def test_health_live(client: TestClient):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_json_ok(client: TestClient):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    assert r.json()["openapi"].startswith("3.")


def test_oidc_discovery(client: TestClient):
    r = client.get("/.well-known/openid-configuration")
    assert r.status_code == 200
    body = r.json()
    assert "issuer" in body
    assert "token_endpoint" in body


def test_jwks(client: TestClient):
    r = client.get("/.well-known/jwks.json")
    assert r.status_code == 200
    assert "keys" in r.json()


def test_oauth_authorize_stub(client: TestClient):
    r = client.get("/oauth/authorize")
    assert r.status_code == 400

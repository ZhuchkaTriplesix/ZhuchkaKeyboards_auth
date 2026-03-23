"""OpenAPI 3.x document at GET /api/openapi.json."""

from starlette.testclient import TestClient

from src.main import app


def test_openapi_json_schema():
    with TestClient(app) as client:
        response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    body = response.json()
    assert body["openapi"].startswith("3.")
    assert body["info"]["title"] == "Zhuchka Auth"
    assert body["info"]["version"] == "1.0.0"
    paths = body["paths"]
    assert "/oauth/token" in paths
    assert "/.well-known/openid-configuration" in paths
    assert "/api/v1/users" in paths
    assert "BearerAuth" in body["components"]["securitySchemes"]
    tags = {t["name"] for t in body.get("tags", [])}
    assert "admin" in tags
    assert "oauth" in tags

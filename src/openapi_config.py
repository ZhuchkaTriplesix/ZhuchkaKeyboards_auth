"""OpenAPI 3.x metadata and custom schema (see /api/openapi.json)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": "health", "description": "Liveness and readiness probes."},
    {
        "name": "oauth",
        "description": "OAuth2 token endpoint, revoke, introspection (RFC 7662), OIDC discovery, JWKS.",
    },
    {"name": "oidc", "description": "OIDC discovery document and JWKS (same router as oauth)."},
    {
        "name": "admin",
        "description": "Administrative API; requires Bearer JWT whose `scope` includes `admin`.",
    },
    {"name": "root", "description": "Template root routes (health under /api/root)."},
]


def apply_openapi(app: FastAPI) -> None:
    """Attach a generator that produces OpenAPI 3.x JSON with shared metadata."""

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        info = openapi_schema.setdefault("info", {})
        info.setdefault("contact", {"name": "ZhuchkaKeyboards"})
        info.setdefault("license", {"name": "MIT"})
        components = openapi_schema.setdefault("components", {})
        schemes = components.setdefault("securitySchemes", {})
        schemes.setdefault(
            "BearerAuth",
            {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": (
                    "OAuth2 access token (JWT). Admin APIs require `scope` containing `admin`."
                ),
            },
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

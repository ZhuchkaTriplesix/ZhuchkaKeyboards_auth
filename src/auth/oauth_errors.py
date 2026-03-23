"""OAuth2-style error payloads (RFC 6749)."""

from typing import Any

from fastapi.responses import JSONResponse


def oauth_error(status_code: int, error: str, description: str | None = None) -> JSONResponse:
    body: dict[str, Any] = {"error": error}
    if description:
        body["error_description"] = description
    return JSONResponse(status_code=status_code, content=body)

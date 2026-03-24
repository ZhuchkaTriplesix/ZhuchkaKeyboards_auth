"""Federated login: Telegram Login widget, Google ID token."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src.auth.federated_login import login_with_google, login_with_telegram
from src.auth.oauth_errors import oauth_error
from src.database.dependencies import DbSession

router = APIRouter()


class TelegramFederatedIn(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    client_id: str
    scope: str | None = None
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    telegram_hash: str = Field(..., alias="hash", description="Telegram HMAC")


class GoogleFederatedIn(BaseModel):
    client_id: str
    scope: str | None = None
    id_token: str


@router.post("/oauth/federated/telegram", include_in_schema=True)
async def oauth_federated_telegram(
    request: Request,
    session: DbSession,
    body: TelegramFederatedIn,
) -> JSONResponse:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    payload: dict = {
        "id": body.id,
        "auth_date": body.auth_date,
        "hash": body.telegram_hash,
    }
    if body.first_name is not None:
        payload["first_name"] = body.first_name
    if body.last_name is not None:
        payload["last_name"] = body.last_name
    if body.username is not None:
        payload["username"] = body.username
    if body.photo_url is not None:
        payload["photo_url"] = body.photo_url
    try:
        out = await login_with_telegram(
            session,
            client_id=body.client_id,
            scope=body.scope,
            payload=payload,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        code = exc.args[0] if exc.args else "invalid_grant"
        if code == "federated_disabled":
            return oauth_error(
                503,
                "temporarily_unavailable",
                "Set TELEGRAM_BOT_TOKEN in [AUTH] to enable Telegram login.",
            )
        if code == "unauthorized_client":
            return oauth_error(401, "invalid_client", "Use the public storefront client_id")
        if code == "invalid_grant":
            return oauth_error(400, "invalid_grant", "Telegram signature or payload invalid")
        if code == "staff_federation_denied":
            return oauth_error(
                403,
                "access_denied",
                "Staff accounts cannot sign in via Telegram or Google; use the operational login.",
            )
        return oauth_error(400, "invalid_grant", code)
    await session.commit()
    return JSONResponse(content=out)


@router.post("/oauth/federated/google", include_in_schema=True)
async def oauth_federated_google(
    request: Request,
    session: DbSession,
    body: GoogleFederatedIn,
) -> JSONResponse:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        out = await login_with_google(
            session,
            client_id=body.client_id,
            scope=body.scope,
            id_token=body.id_token,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        code = exc.args[0] if exc.args else "invalid_grant"
        if code == "federated_disabled":
            return oauth_error(
                503,
                "temporarily_unavailable",
                "Set GOOGLE_CLIENT_IDS in [AUTH] (comma-separated OAuth client IDs).",
            )
        if code == "unauthorized_client":
            return oauth_error(401, "invalid_client", "Use the public storefront client_id")
        if code == "invalid_grant":
            return oauth_error(400, "invalid_grant", "Google ID token invalid or email missing")
        if code == "staff_federation_denied":
            return oauth_error(
                403,
                "access_denied",
                "Staff accounts cannot sign in via Telegram or Google; use the operational login.",
            )
        return oauth_error(400, "invalid_grant", code)
    await session.commit()
    return JSONResponse(content=out)

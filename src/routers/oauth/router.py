"""OIDC discovery, JWKS, OAuth2 token/revoke/userinfo."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.auth.db_models import User
from src.auth.deps import require_access_token
from src.auth.jwt_tokens import jwks_document
from src.auth.oauth_errors import oauth_error
from src.auth.oauth_logic import (
    authenticate_client,
    grant_client_credentials,
    grant_password,
    grant_refresh_token,
    revoke_refresh_token,
)
from src.config import auth_cfg
from src.database.dependencies import DbSession
from src.routers.oauth.federated_router import router as federated_oauth_subrouter

router = APIRouter()


def _issuer_base() -> str:
    return auth_cfg.issuer.rstrip("/")


@router.get("/.well-known/openid-configuration", include_in_schema=True)
async def openid_configuration() -> dict:
    base = _issuer_base()
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "userinfo_endpoint": f"{base}/oauth/userinfo",
        "jwks_uri": f"{base}/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "grant_types_supported": [
            "authorization_code",
            "client_credentials",
            "password",
            "refresh_token",
        ],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "scopes_supported": ["openid", "profile", "email", "admin"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
    }


@router.get("/.well-known/jwks.json", include_in_schema=True)
async def jwks() -> dict:
    return jwks_document()


@router.get("/oauth/authorize", include_in_schema=True)
async def oauth_authorize() -> JSONResponse:
    return oauth_error(
        400,
        "unsupported_response_type",
        "Authorization Code + PKCE is planned; use token grant (password or client_credentials) for now.",
    )


@router.post("/oauth/token", include_in_schema=True)
async def oauth_token(
    request: Request,
    session: DbSession,
    grant_type: str = Form(...),
    username: str | None = Form(None),
    password: str | None = Form(None),
    refresh_token: str | None = Form(None),
    scope: str | None = Form(None),
    client_id: str | None = Form(None),
    client_secret: str | None = Form(None),
    client_basic: HTTPBasicCredentials | None = Depends(HTTPBasic(auto_error=False)),
) -> JSONResponse:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    client = await authenticate_client(
        session,
        client_id=client_id,
        client_secret=client_secret,
        basic_user=client_basic.username if client_basic else None,
        basic_password=client_basic.password if client_basic else None,
    )
    if not client:
        return oauth_error(401, "invalid_client", "Client authentication failed")

    try:
        if grant_type == "client_credentials":
            body = await grant_client_credentials(session, client, scope)
        elif grant_type == "password":
            if not username or not password:
                return oauth_error(400, "invalid_request", "username and password are required")
            body = await grant_password(
                session,
                client,
                username=username,
                password=password,
                scope=scope,
                ip=ip,
                user_agent=ua,
            )
        elif grant_type == "refresh_token":
            if not refresh_token:
                return oauth_error(400, "invalid_request", "refresh_token is required")
            body = await grant_refresh_token(
                session,
                client,
                refresh_token=refresh_token,
                ip=ip,
                user_agent=ua,
            )
        else:
            return oauth_error(400, "unsupported_grant_type")
    except ValueError as exc:
        code = exc.args[0] if exc.args else "invalid_grant"
        if code == "access_denied":
            return oauth_error(403, "access_denied")
        if code == "unauthorized_client":
            return oauth_error(401, "invalid_client")
        if code == "unsupported_grant":
            return oauth_error(400, "unsupported_grant")
        return oauth_error(400, "invalid_grant", code)

    return JSONResponse(content=body)


@router.post("/oauth/revoke", include_in_schema=True)
async def oauth_revoke(
    session: DbSession,
    token: str | None = Form(None),
) -> Response:
    await revoke_refresh_token(session, token)
    return Response(status_code=200)


@router.get("/oauth/userinfo", include_in_schema=True)
async def oauth_userinfo(
    session: DbSession,
    claims: dict = Depends(require_access_token),
) -> dict:
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="invalid_token")
    if sub.startswith("client:"):
        return {"sub": sub}
    try:
        uid = UUID(sub)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_sub") from exc
    user = await session.get(User, uid)
    out: dict = {"sub": sub}
    if user:
        out["email"] = user.email
        out["email_verified"] = True
    return out


router.include_router(federated_oauth_subrouter)

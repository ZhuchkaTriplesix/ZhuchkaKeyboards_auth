"""OIDC discovery, JWKS, OAuth2 token/revoke/userinfo."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.auth.db_models import User
from src.auth.deps import require_access_token
from src.auth.jwt_tokens import jwks_document
from src.auth.oauth_errors import oauth_error
from src.auth.oauth_logic import (
    authenticate_client,
    get_oauth_client_by_id,
    grant_authorization_code,
    grant_client_credentials,
    grant_password,
    grant_refresh_token,
    introspect_token,
    oauth_authorization_redirect_url,
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
        "introspection_endpoint": f"{base}/oauth/introspect",
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
        "code_challenge_methods_supported": ["S256"],
    }


@router.get("/.well-known/jwks.json", include_in_schema=True)
async def jwks() -> dict:
    return jwks_document()


@router.get("/oauth/authorize", include_in_schema=True)
async def oauth_authorize(
    request: Request,
    session: DbSession,
    response_type: str = Query(..., description="Must be `code`"),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str | None = Query(None),
    state: str | None = Query(None),
    code_challenge: str | None = Query(None),
    code_challenge_method: str | None = Query(None),
) -> RedirectResponse | JSONResponse:
    """Authorization Code + PKCE (S256) for the **public** storefront client. Requires prior federated login cookie."""
    client = await get_oauth_client_by_id(session, client_id.strip())
    if not client:
        return oauth_error(400, "invalid_request", "Unknown client_id")
    uris = list(client.redirect_uris or [])
    if redirect_uri not in uris:
        return oauth_error(
            400, "invalid_request", "redirect_uri does not match client registration"
        )
    url = await oauth_authorization_redirect_url(
        session,
        client=client,
        redirect_uri=redirect_uri,
        response_type=response_type,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        browser_login_jwt=request.cookies.get(auth_cfg.browser_login_cookie_name),
    )
    return RedirectResponse(url=url, status_code=302)


@router.post("/oauth/token", include_in_schema=True)
async def oauth_token(
    request: Request,
    session: DbSession,
    grant_type: str = Form(...),
    username: str | None = Form(None),
    password: str | None = Form(None),
    refresh_token: str | None = Form(None),
    scope: str | None = Form(None),
    code: str | None = Form(None),
    redirect_uri: str | None = Form(None),
    code_verifier: str | None = Form(None),
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
        elif grant_type == "authorization_code":
            if not code or not redirect_uri:
                return oauth_error(400, "invalid_request", "code and redirect_uri are required")
            body = await grant_authorization_code(
                session,
                client,
                code=code,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
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


@router.post("/oauth/introspect", include_in_schema=True)
async def oauth_introspect(
    session: DbSession,
    token: str | None = Form(None),
    token_type_hint: str | None = Form(None),
    client_id: str | None = Form(None),
    client_secret: str | None = Form(None),
    client_basic: HTTPBasicCredentials | None = Depends(HTTPBasic(auto_error=False)),
) -> JSONResponse:
    """RFC 7662 token introspection. Requires a **confidential** OAuth client (Basic or form auth)."""
    if not token:
        return oauth_error(400, "invalid_request", "token is required")
    client = await authenticate_client(
        session,
        client_id=client_id,
        client_secret=client_secret,
        basic_user=client_basic.username if client_basic else None,
        basic_password=client_basic.password if client_basic else None,
    )
    if not client:
        return oauth_error(401, "invalid_client", "Client authentication failed")
    if client.is_public:
        return oauth_error(
            401,
            "invalid_client",
            "Token introspection requires a confidential OAuth client",
        )
    body = await introspect_token(session, token=token, token_type_hint=token_type_hint)
    return JSONResponse(content=body)


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

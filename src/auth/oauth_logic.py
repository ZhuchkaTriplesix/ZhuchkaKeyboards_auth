"""Token issuance: client_credentials, refresh_token, password (optional)."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.db_models import LoginAudit, OAuthAuthorizationCode, OAuthClient, RefreshToken, User
from src.auth.jwt_tokens import decode_access_token, decode_browser_login_token, mint_access_token
from src.auth.oauth_urls import append_query_params
from src.auth.passwords import verify_password, verify_secret
from src.config import auth_cfg
from src.database.core import async_session_maker


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


_PKCE_VERIFIER_RE = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")


def verify_pkce_s256(code_verifier: str, code_challenge: str) -> bool:
    """RFC 7636: BASE64URL(SHA256(ASCII(code_verifier))) == code_challenge (no padding compare)."""
    if not _PKCE_VERIFIER_RE.match(code_verifier):
        return False
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed = base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def _strip_pad(s: str) -> str:
        return s.rstrip("=")

    return secrets.compare_digest(_strip_pad(computed), _strip_pad(code_challenge.strip()))


def _scope_intersect(requested: str | None, allowed: list[str]) -> str:
    req = (requested or "").split()
    allow = set(allowed)
    out = [x for x in req if x in allow]
    if not out and allow:
        out = [sorted(allow)[0]]
    return " ".join(out)


def _user_scope_string(user: User, requested: str | None, allowed: list[str]) -> str:
    allow_set = set(allowed)
    parts = set((requested or "").split()) & allow_set
    role_names = {r.name for r in user.roles}
    if "admin" in role_names and "admin" in allow_set:
        parts.add("admin")
    if not parts:
        parts = {"openid", "profile", "email"} & allow_set
    if not parts and allow_set:
        parts = set(sorted(allow_set)[:3])
    return " ".join(sorted(parts))


async def _get_client(session: AsyncSession, client_id: str) -> OAuthClient | None:
    r = await session.execute(select(OAuthClient).where(OAuthClient.client_id == client_id))
    return r.scalar_one_or_none()


async def get_oauth_client_by_id(session: AsyncSession, client_id: str) -> OAuthClient | None:
    return await _get_client(session, client_id)


def _oauth_authorize_error_redirect(
    redirect_uri: str,
    error: str,
    state: str | None,
    description: str | None = None,
) -> str:
    p: dict[str, str] = {"error": error}
    if state:
        p["state"] = state
    if description:
        p["error_description"] = description
    return append_query_params(redirect_uri, p)


async def oauth_authorization_redirect_url(
    session: AsyncSession,
    *,
    client: OAuthClient,
    redirect_uri: str,
    response_type: str,
    scope: str | None,
    state: str | None,
    code_challenge: str | None,
    code_challenge_method: str | None,
    browser_login_jwt: str | None,
) -> str:
    """Build 302 Location for GET /oauth/authorize (public client + PKCE S256 + browser login cookie)."""
    if response_type.strip() != "code":
        return _oauth_authorize_error_redirect(
            redirect_uri,
            "unsupported_response_type",
            state,
            "Only response_type=code is supported",
        )
    if not client.is_public:
        return _oauth_authorize_error_redirect(
            redirect_uri,
            "unauthorized_client",
            state,
            "Authorization Code flow is for public clients only",
        )
    ch = (code_challenge or "").strip()
    chm = (code_challenge_method or "").strip().upper()
    if not ch or chm != "S256":
        return _oauth_authorize_error_redirect(
            redirect_uri,
            "invalid_request",
            state,
            "code_challenge and code_challenge_method=S256 are required",
        )
    if not browser_login_jwt:
        return _oauth_authorize_error_redirect(
            redirect_uri,
            "login_required",
            state,
            "Sign in first (e.g. POST /oauth/federated/google or /oauth/federated/telegram)",
        )
    try:
        claims = decode_browser_login_token(browser_login_jwt)
        sub = claims.get("sub")
        uid = UUID(str(sub))
    except Exception:
        return _oauth_authorize_error_redirect(
            redirect_uri, "login_required", state, "Invalid or expired login session"
        )

    user = await session.get(User, uid)
    if not user:
        return _oauth_authorize_error_redirect(
            redirect_uri, "login_required", state, "User not found"
        )

    try:
        raw = await register_authorization_code(
            session,
            client,
            user,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=ch,
            code_challenge_method="S256",
        )
    except ValueError as exc:
        code = exc.args[0] if exc.args else "invalid_request"
        if code == "access_denied":
            return _oauth_authorize_error_redirect(redirect_uri, "access_denied", state)
        if code == "unauthorized_client":
            return _oauth_authorize_error_redirect(redirect_uri, "unauthorized_client", state)
        if code == "invalid_request":
            return _oauth_authorize_error_redirect(redirect_uri, "invalid_request", state, code)
        return _oauth_authorize_error_redirect(redirect_uri, "invalid_request", state, code)

    params: dict[str, str] = {"code": raw}
    if state:
        params["state"] = state
    return append_query_params(redirect_uri, params)


async def authenticate_client(
    session: AsyncSession,
    *,
    client_id: str | None,
    client_secret: str | None,
    basic_user: str | None,
    basic_password: str | None,
) -> OAuthClient | None:
    cid = client_id or basic_user
    secret = client_secret or basic_password
    if not cid:
        return None
    client = await _get_client(session, cid)
    if not client:
        return None
    if client.is_public:
        if secret:
            return None
        return client
    if not client.client_secret_hash or not secret:
        return None
    if not verify_secret(secret, client.client_secret_hash):
        return None
    return client


async def grant_client_credentials(
    _session: AsyncSession,
    client: OAuthClient,
    scope: str | None,
) -> dict[str, Any]:
    if "client_credentials" not in (client.allowed_grant_types or []):
        raise ValueError("unsupported_grant")
    sc = _scope_intersect(scope, list(client.allowed_scopes or []))
    if not sc:
        sc = " ".join(sorted(set(client.allowed_scopes or [])))
    token, expires_in = mint_access_token(
        sub=f"client:{client.client_id}",
        scope=sc,
        client_id=client.client_id,
    )
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": sc,
    }


async def _bump_failed_login(email: str) -> None:
    async with async_session_maker() as s:
        r = await s.execute(select(User).where(User.email == email))
        user = r.scalar_one_or_none()
        if not user:
            return
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.locked_until = datetime.now(tz=UTC) + timedelta(minutes=15)
        await s.commit()


async def _audit_login(
    *,
    success: bool,
    reason: str | None,
    user_id: UUID | None,
    client_id: str,
    ip: str | None,
    user_agent: str | None,
    login_method: str | None = None,
) -> None:
    async with async_session_maker() as s:
        s.add(
            LoginAudit(
                user_id=user_id,
                client_id=client_id,
                login_method=login_method,
                ip=ip,
                user_agent=user_agent,
                success=success,
                reason=reason,
            )
        )
        await s.commit()


async def grant_password(
    session: AsyncSession,
    client: OAuthClient,
    *,
    username: str,
    password: str,
    scope: str | None,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    if not auth_cfg.password_grant_enabled:
        raise ValueError("unsupported_grant")
    if not client.allow_password_grant or "password" not in (client.allowed_grant_types or []):
        raise ValueError("unsupported_grant")
    if client.is_public:
        raise ValueError("unauthorized_client")

    email = username.strip().lower()
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        await _audit_login(
            success=False,
            reason="invalid_credentials",
            user_id=user.id if user else None,
            client_id=client.client_id,
            ip=ip,
            user_agent=user_agent,
            login_method="password",
        )
        raise ValueError("invalid_grant")

    if user.locked_until and user.locked_until > datetime.now(tz=UTC):
        await _audit_login(
            success=False,
            reason="locked",
            user_id=user.id,
            client_id=client.client_id,
            ip=ip,
            user_agent=user_agent,
            login_method="password",
        )
        raise ValueError("access_denied")

    if not verify_password(password, user.password_hash):
        await _bump_failed_login(email)
        await _audit_login(
            success=False,
            reason="invalid_credentials",
            user_id=user.id,
            client_id=client.client_id,
            ip=ip,
            user_agent=user_agent,
            login_method="password",
        )
        raise ValueError("invalid_grant")

    user.failed_login_count = 0
    user.locked_until = None

    sc = _user_scope_string(user, scope, list(client.allowed_scopes or []))
    token, expires_in = mint_access_token(
        sub=str(user.id),
        scope=sc,
        client_id=client.client_id,
    )

    raw_refresh = secrets.token_urlsafe(48)
    exp = datetime.now(tz=UTC) + timedelta(days=auth_cfg.refresh_token_days)
    rt = RefreshToken(
        token_hash=_hash_refresh(raw_refresh),
        user_id=user.id,
        client_db_id=client.id,
        scope=sc,
        expires_at=exp,
    )
    session.add(rt)
    session.add(
        LoginAudit(
            user_id=user.id,
            client_id=client.client_id,
            login_method="password",
            ip=ip,
            user_agent=user_agent,
            success=True,
            reason=None,
        )
    )
    await session.flush()

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": raw_refresh,
        "scope": sc,
    }


async def grant_refresh_token(
    session: AsyncSession,
    client: OAuthClient,
    *,
    refresh_token: str,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    if "refresh_token" not in (client.allowed_grant_types or []):
        raise ValueError("unsupported_grant")

    h = _hash_refresh(refresh_token)
    r = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
    row = r.scalar_one_or_none()
    if not row or row.revoked_at or row.expires_at < datetime.now(tz=UTC):
        raise ValueError("invalid_grant")
    if row.client_db_id != client.id:
        raise ValueError("invalid_grant")

    if row.user_id:
        ur = await session.execute(
            select(User).options(selectinload(User.roles)).where(User.id == row.user_id)
        )
        user = ur.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("invalid_grant")
        sc = _user_scope_string(user, row.scope, list(client.allowed_scopes or []))
        sub = str(user.id)
    else:
        sc = _scope_intersect(row.scope, list(client.allowed_scopes or []))
        sub = f"client:{client.client_id}"

    token, expires_in = mint_access_token(sub=sub, scope=sc, client_id=client.client_id)

    row.revoked_at = datetime.now(tz=UTC)
    raw_new = secrets.token_urlsafe(48)
    exp = datetime.now(tz=UTC) + timedelta(days=auth_cfg.refresh_token_days)
    new_row = RefreshToken(
        token_hash=_hash_refresh(raw_new),
        user_id=row.user_id,
        client_db_id=client.id,
        scope=sc,
        expires_at=exp,
        replaced_by_id=None,
    )
    session.add(new_row)
    await session.flush()
    row.replaced_by_id = new_row.id

    session.add(
        LoginAudit(
            user_id=row.user_id,
            client_id=client.client_id,
            login_method="refresh_token",
            ip=ip,
            user_agent=user_agent,
            success=True,
            reason="refresh",
        )
    )

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": raw_new,
        "scope": sc,
    }


async def issue_tokens_for_user(
    session: AsyncSession,
    client: OAuthClient,
    *,
    user: User,
    scope: str | None,
    ip: str | None,
    user_agent: str | None,
    login_method: str,
) -> dict[str, Any]:
    """Mint access + refresh for a resource owner (federated / future browser flows)."""
    if not user.is_active:
        raise ValueError("invalid_grant")
    if user.locked_until and user.locked_until > datetime.now(tz=UTC):
        raise ValueError("access_denied")

    user.failed_login_count = 0
    user.locked_until = None

    sc = _user_scope_string(user, scope, list(client.allowed_scopes or []))
    token, expires_in = mint_access_token(
        sub=str(user.id),
        scope=sc,
        client_id=client.client_id,
    )
    raw_refresh = secrets.token_urlsafe(48)
    exp = datetime.now(tz=UTC) + timedelta(days=auth_cfg.refresh_token_days)
    rt = RefreshToken(
        token_hash=_hash_refresh(raw_refresh),
        user_id=user.id,
        client_db_id=client.id,
        scope=sc,
        expires_at=exp,
    )
    session.add(rt)
    session.add(
        LoginAudit(
            user_id=user.id,
            client_id=client.client_id,
            login_method=login_method,
            ip=ip,
            user_agent=user_agent,
            success=True,
            reason=None,
        )
    )
    await session.flush()

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": raw_refresh,
        "scope": sc,
    }


async def register_authorization_code(
    session: AsyncSession,
    client: OAuthClient,
    user: User,
    *,
    redirect_uri: str,
    scope: str | None,
    code_challenge: str,
    code_challenge_method: str,
) -> str:
    """Persist an OAuth2 authorization code (PKCE S256). Caller validated redirect_uri and client policy."""
    if (code_challenge_method or "").strip().upper() != "S256":
        raise ValueError("invalid_request")
    if not client.is_public:
        raise ValueError("unauthorized_client")
    if "authorization_code" not in (client.allowed_grant_types or []):
        raise ValueError("unauthorized_client")
    if user.identity_kind != "customer":
        raise ValueError("access_denied")
    if not user.is_active:
        raise ValueError("access_denied")
    if user.locked_until and user.locked_until > datetime.now(tz=UTC):
        raise ValueError("access_denied")

    sc = _user_scope_string(user, scope, list(client.allowed_scopes or []))
    raw = secrets.token_urlsafe(48)
    exp = datetime.now(tz=UTC) + timedelta(minutes=auth_cfg.authorization_code_minutes)
    session.add(
        OAuthAuthorizationCode(
            code_hash=_hash_refresh(raw),
            client_db_id=client.id,
            user_id=user.id,
            redirect_uri=redirect_uri,
            scope=sc,
            code_challenge=code_challenge.strip(),
            code_challenge_method="S256",
            expires_at=exp,
        )
    )
    await session.flush()
    return raw


async def grant_authorization_code(
    session: AsyncSession,
    client: OAuthClient,
    *,
    code: str,
    redirect_uri: str,
    code_verifier: str | None,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    if "authorization_code" not in (client.allowed_grant_types or []):
        raise ValueError("unsupported_grant")
    h = _hash_refresh(code)
    r = await session.execute(
        select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code_hash == h)
    )
    acr = r.scalar_one_or_none()
    if not acr or acr.consumed_at or acr.expires_at < datetime.now(tz=UTC):
        raise ValueError("invalid_grant")
    if acr.client_db_id != client.id:
        raise ValueError("invalid_grant")
    if acr.redirect_uri != redirect_uri:
        raise ValueError("invalid_grant")
    if not code_verifier:
        raise ValueError("invalid_grant")
    if not verify_pkce_s256(code_verifier, acr.code_challenge):
        raise ValueError("invalid_grant")

    ur = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == acr.user_id)
    )
    user = ur.scalar_one_or_none()
    if not user or not user.is_active:
        raise ValueError("invalid_grant")
    if client.is_public and user.identity_kind != "customer":
        raise ValueError("invalid_grant")

    acr.consumed_at = datetime.now(tz=UTC)
    out = await issue_tokens_for_user(
        session,
        client,
        user=user,
        scope=acr.scope,
        ip=ip,
        user_agent=user_agent,
        login_method="authorization_code",
    )
    await session.flush()
    return out


async def revoke_refresh_token(session: AsyncSession, token: str | None) -> None:
    if not token:
        return
    h = _hash_refresh(token)
    r = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
    row = r.scalar_one_or_none()
    if row and not row.revoked_at:
        row.revoked_at = datetime.now(tz=UTC)


async def introspect_access_token_string(token: str) -> dict[str, Any]:
    """RFC 7662-style introspection for RS256 access JWTs issued by this server."""
    try:
        claims = decode_access_token(token)
    except Exception:
        return {"active": False}
    if claims.get("token_use") != "access":
        return {"active": False}
    sub = claims.get("sub")
    if not sub:
        return {"active": False}
    out: dict[str, Any] = {
        "active": True,
        "token_type": "Bearer",
        "scope": str(claims.get("scope") or ""),
        "client_id": str(claims.get("client_id") or ""),
        "sub": str(sub),
    }
    exp = claims.get("exp")
    iat = claims.get("iat")
    if exp is not None:
        out["exp"] = int(exp)
    if iat is not None:
        out["iat"] = int(iat)
    return out


async def introspect_refresh_token_string(session: AsyncSession, raw: str) -> dict[str, Any]:
    h = _hash_refresh(raw)
    r = await session.execute(
        select(RefreshToken)
        .options(selectinload(RefreshToken.client))
        .where(RefreshToken.token_hash == h)
    )
    row = r.scalar_one_or_none()
    if not row or row.revoked_at or row.expires_at < datetime.now(tz=UTC):
        return {"active": False}
    oc = row.client
    cid = oc.client_id if oc else ""
    out: dict[str, Any] = {
        "active": True,
        "token_type": "refresh_token",
        "scope": row.scope or "",
        "client_id": cid,
        "sub": str(row.user_id) if row.user_id else f"client:{cid}",
        "exp": int(row.expires_at.timestamp()),
    }
    return out


async def introspect_token(
    session: AsyncSession,
    *,
    token: str,
    token_type_hint: str | None,
) -> dict[str, Any]:
    """Return introspection JSON (active + metadata). Caller must authenticate a confidential client."""
    hint = (token_type_hint or "").strip().lower()
    if hint == "refresh_token":
        return await introspect_refresh_token_string(session, token)
    if hint == "access_token":
        return await introspect_access_token_string(token)
    if token.count(".") == 2:
        r = await introspect_access_token_string(token)
        if r.get("active"):
            return r
    return await introspect_refresh_token_string(session, token)

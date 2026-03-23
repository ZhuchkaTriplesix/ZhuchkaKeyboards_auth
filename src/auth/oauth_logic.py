"""Token issuance: client_credentials, refresh_token, password (optional)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.db_models import LoginAudit, OAuthClient, RefreshToken, User
from src.auth.jwt_tokens import mint_access_token
from src.auth.passwords import verify_password, verify_secret
from src.config import auth_cfg
from src.database.core import async_session_maker


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


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


async def revoke_refresh_token(session: AsyncSession, token: str | None) -> None:
    if not token:
        return
    h = _hash_refresh(token)
    r = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
    row = r.scalar_one_or_none()
    if row and not row.revoked_at:
        row.revoked_at = datetime.now(tz=UTC)

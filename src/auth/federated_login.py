"""Link or create users from Telegram / Google and issue OAuth tokens."""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.db_models import ExternalIdentity, User
from src.auth.federated_verify import decode_google_id_token, verify_telegram_widget
from src.auth.oauth_logic import authenticate_client as authenticate_oauth_client
from src.auth.oauth_logic import issue_tokens_for_user
from src.auth.passwords import hash_password
from src.config import auth_cfg


def _synthetic_telegram_email(telegram_id: int) -> str:
    return f"tg.{telegram_id}@telegram.federated.zhuchka"


def _ensure_customer_for_federated_login(user: User) -> None:
    """Staff accounts must use org-issued credentials, not Telegram/Google (see docs/microservices/01-auth.md)."""
    if user.identity_kind == "staff":
        raise ValueError("staff_federation_denied")


async def login_with_telegram(
    session: AsyncSession,
    *,
    client_id: str,
    scope: str | None,
    payload: dict[str, Any],
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    if not auth_cfg.telegram_bot_token:
        raise ValueError("federated_disabled")
    if not verify_telegram_widget(payload, bot_token=auth_cfg.telegram_bot_token):
        raise ValueError("invalid_grant")

    client = await authenticate_oauth_client(
        session,
        client_id=client_id,
        client_secret=None,
        basic_user=None,
        basic_password=None,
    )
    if not client or not client.is_public:
        raise ValueError("unauthorized_client")

    tid = int(payload["id"])
    subject = str(tid)
    r = await session.execute(
        select(ExternalIdentity)
        .options(selectinload(ExternalIdentity.user).selectinload(User.roles))
        .where(
            ExternalIdentity.provider == "telegram",
            ExternalIdentity.subject == subject,
        )
    )
    ext = r.scalar_one_or_none()
    if ext and ext.user:
        user = ext.user
        _ensure_customer_for_federated_login(user)
    else:
        email = _synthetic_telegram_email(tid)
        ur = await session.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email)
        )
        existing = ur.scalar_one_or_none()
        if existing:
            user = existing
            _ensure_customer_for_federated_login(user)
            session.add(
                ExternalIdentity(
                    user_id=user.id,
                    provider="telegram",
                    subject=subject,
                )
            )
        else:
            user = User(
                email=email,
                identity_kind="customer",
                password_hash=hash_password(secrets.token_urlsafe(32)),
                is_active=True,
            )
            session.add(user)
            await session.flush()
            session.add(
                ExternalIdentity(
                    user_id=user.id,
                    provider="telegram",
                    subject=subject,
                )
            )
        await session.flush()
        await session.refresh(user, ["roles"])

    return await issue_tokens_for_user(
        session,
        client,
        user=user,
        scope=scope,
        ip=ip,
        user_agent=user_agent,
        login_method="telegram",
    )


async def login_with_google(
    session: AsyncSession,
    *,
    client_id: str,
    scope: str | None,
    id_token: str,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    audiences = [x.strip() for x in auth_cfg.google_client_ids.split(",") if x.strip()]
    if not audiences:
        raise ValueError("federated_disabled")
    try:
        claims = decode_google_id_token(id_token, audiences=audiences)
    except Exception as exc:
        raise ValueError("invalid_grant") from exc

    sub = str(claims.get("sub", ""))
    if not sub:
        raise ValueError("invalid_grant")
    email = str(claims.get("email", "")).strip().lower()
    if not email:
        raise ValueError("invalid_grant")

    client = await authenticate_oauth_client(
        session,
        client_id=client_id,
        client_secret=None,
        basic_user=None,
        basic_password=None,
    )
    if not client or not client.is_public:
        raise ValueError("unauthorized_client")

    r = await session.execute(
        select(ExternalIdentity)
        .options(selectinload(ExternalIdentity.user).selectinload(User.roles))
        .where(ExternalIdentity.provider == "google", ExternalIdentity.subject == sub)
    )
    ext = r.scalar_one_or_none()
    if ext and ext.user:
        user = ext.user
        _ensure_customer_for_federated_login(user)
    else:
        ur = await session.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email)
        )
        existing = ur.scalar_one_or_none()
        if existing:
            user = existing
            _ensure_customer_for_federated_login(user)
            session.add(
                ExternalIdentity(
                    user_id=user.id,
                    provider="google",
                    subject=sub,
                )
            )
        else:
            user = User(
                email=email,
                identity_kind="customer",
                password_hash=hash_password(secrets.token_urlsafe(32)),
                is_active=True,
            )
            session.add(user)
            await session.flush()
            session.add(
                ExternalIdentity(
                    user_id=user.id,
                    provider="google",
                    subject=sub,
                )
            )
        await session.flush()
        await session.refresh(user, ["roles"])

    return await issue_tokens_for_user(
        session,
        client,
        user=user,
        scope=scope,
        ip=ip,
        user_agent=user_agent,
        login_method="google",
    )

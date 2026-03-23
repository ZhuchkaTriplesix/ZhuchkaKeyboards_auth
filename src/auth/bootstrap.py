"""One-time bootstrap: roles, dev OAuth client, optional admin user."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.db_models import OAuthClient, Role, User, UserRole
from src.auth.passwords import hash_password, hash_secret
from src.config import auth_cfg


async def run_bootstrap(session: AsyncSession) -> None:
    await _ensure_roles(session)
    await _ensure_bootstrap_client(session)
    await _ensure_bootstrap_admin(session)
    await session.commit()


async def _ensure_roles(session: AsyncSession) -> None:
    for name in ("admin", "user"):
        r = await session.execute(select(Role).where(Role.name == name))
        if r.scalar_one_or_none() is None:
            session.add(Role(name=name))
    await session.flush()


async def _ensure_bootstrap_client(session: AsyncSession) -> None:
    r = await session.execute(
        select(OAuthClient).where(OAuthClient.client_id == auth_cfg.bootstrap_client_id)
    )
    if r.scalar_one_or_none() is not None:
        return
    session.add(
        OAuthClient(
            client_id=auth_cfg.bootstrap_client_id,
            client_secret_hash=hash_secret(auth_cfg.bootstrap_client_secret),
            is_public=False,
            redirect_uris=["http://127.0.0.1/callback"],
            allowed_grant_types=[
                "authorization_code",
                "refresh_token",
                "client_credentials",
                "password",
            ],
            allowed_scopes=["openid", "profile", "email", "admin"],
            allow_password_grant=True,
        )
    )


async def _ensure_bootstrap_admin(session: AsyncSession) -> None:
    if not auth_cfg.bootstrap_admin_email or not auth_cfg.bootstrap_admin_password:
        return
    email = auth_cfg.bootstrap_admin_email.strip().lower()
    r = await session.execute(select(User).where(User.email == email))
    if r.scalar_one_or_none() is not None:
        return
    user = User(
        email=email,
        identity_kind="staff",
        password_hash=hash_password(auth_cfg.bootstrap_admin_password),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    ar = await session.execute(select(Role).where(Role.name == "admin"))
    admin_role = ar.scalar_one()
    session.add(UserRole(user_id=user.id, role_id=admin_role.id))

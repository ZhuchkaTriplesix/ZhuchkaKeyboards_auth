"""Бизнес-логика admin API."""

from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.db_models import OAuthClient, User
from src.auth.passwords import hash_password, hash_secret
from src.routers.admin.dal import AdminDAL
from src.routers.admin.exceptions import (
    AdminNotFoundError,
    ClientIdExistsError,
    EmailExistsError,
    UnknownRoleError,
)
from src.routers.admin.schemas import (
    OAuthClientCreate,
    OAuthClientCreated,
    OAuthClientPatch,
    RolesPayload,
    UserCreate,
    UserPatch,
)


async def create_user(session: AsyncSession, body: UserCreate) -> User:
    dal = AdminDAL(session)
    email = body.email.strip().lower()
    if await dal.user_get_by_email(email):
        raise EmailExistsError()
    user = User(
        email=email,
        identity_kind=body.identity_kind.value,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    dal.user_add(user)
    await session.flush()
    role = await dal.role_by_name("user")
    if role:
        dal.user_role_add(user.id, role.id)
    await session.flush()
    return user


async def list_users(session: AsyncSession) -> list[User]:
    return await AdminDAL(session).users_list()


async def get_user(session: AsyncSession, user_id: UUID) -> User:
    user = await AdminDAL(session).user_get_by_id(user_id)
    if not user:
        raise AdminNotFoundError("user", str(user_id))
    return user


async def patch_user(session: AsyncSession, user_id: UUID, body: UserPatch) -> User:
    dal = AdminDAL(session)
    user = await dal.user_get_by_id(user_id)
    if not user:
        raise AdminNotFoundError("user", str(user_id))
    if body.email is not None:
        new_email = body.email.strip().lower()
        if new_email != user.email:
            if await dal.user_get_by_email(new_email):
                raise EmailExistsError()
            user.email = new_email
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.identity_kind is not None:
        user.identity_kind = body.identity_kind.value
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    await session.flush()
    return user


async def soft_delete_user(session: AsyncSession, user_id: UUID) -> None:
    dal = AdminDAL(session)
    user = await dal.user_get_by_id(user_id)
    if not user:
        raise AdminNotFoundError("user", str(user_id))
    user.is_active = False
    await session.flush()


async def replace_user_roles(session: AsyncSession, user_id: UUID, body: RolesPayload) -> User:
    dal = AdminDAL(session)
    user = await dal.user_get_by_id(user_id)
    if not user:
        raise AdminNotFoundError("user", str(user_id))
    await dal.user_roles_delete_all(user_id)
    for name in body.role_names:
        role = await dal.role_by_name(name)
        if not role:
            raise UnknownRoleError(name)
        dal.user_role_add(user.id, role.id)
    await session.flush()
    await session.refresh(user, attribute_names=["roles"])
    return user


async def add_user_roles(session: AsyncSession, user_id: UUID, body: RolesPayload) -> User:
    dal = AdminDAL(session)
    user = await dal.user_get_by_id(user_id)
    if not user:
        raise AdminNotFoundError("user", str(user_id))
    have = await dal.user_roles_ids(user_id)
    for name in body.role_names:
        role = await dal.role_by_name(name)
        if not role:
            raise UnknownRoleError(name)
        if role.id not in have:
            dal.user_role_add(user.id, role.id)
            have.add(role.id)
    await session.flush()
    await session.refresh(user, attribute_names=["roles"])
    return user


async def set_user_mfa(session: AsyncSession, user_id: UUID, *, enabled: bool) -> User:
    dal = AdminDAL(session)
    user = await dal.user_get_by_id(user_id)
    if not user:
        raise AdminNotFoundError("user", str(user_id))
    user.mfa_enabled = enabled
    await session.flush()
    return user


async def list_roles(session: AsyncSession):
    return await AdminDAL(session).roles_all()


async def list_clients(session: AsyncSession):
    return await AdminDAL(session).oauth_clients_list()


async def get_client(session: AsyncSession, client_pk: UUID) -> OAuthClient:
    oc = await AdminDAL(session).oauth_client_get_by_id(client_pk)
    if not oc:
        raise AdminNotFoundError("oauth_client", str(client_pk))
    return oc


async def create_client(session: AsyncSession, body: OAuthClientCreate) -> OAuthClientCreated:
    dal = AdminDAL(session)
    cid = body.client_id.strip()
    if await dal.oauth_client_get_by_client_id(cid):
        raise ClientIdExistsError()
    plain_secret = body.client_secret or secrets.token_urlsafe(32)
    oc = OAuthClient(
        client_id=cid,
        client_secret_hash=hash_secret(plain_secret) if not body.is_public else None,
        is_public=body.is_public,
        redirect_uris=list(body.redirect_uris),
        allowed_grant_types=body.allowed_grant_types
        or ["authorization_code", "refresh_token", "client_credentials", "password"],
        allowed_scopes=body.allowed_scopes or ["openid", "profile", "email"],
        allow_password_grant=body.allow_password_grant,
    )
    dal.oauth_client_add(oc)
    await session.flush()
    return OAuthClientCreated(
        id=oc.id,
        client_id=oc.client_id,
        is_public=oc.is_public,
        redirect_uris=list(oc.redirect_uris or []),
        allowed_grant_types=list(oc.allowed_grant_types or []),
        allowed_scopes=list(oc.allowed_scopes or []),
        allow_password_grant=oc.allow_password_grant,
        created_at=oc.created_at,
        client_secret=plain_secret,
    )


async def patch_client(
    session: AsyncSession, client_pk: UUID, body: OAuthClientPatch
) -> OAuthClient:
    dal = AdminDAL(session)
    oc = await dal.oauth_client_get_by_id(client_pk)
    if not oc:
        raise AdminNotFoundError("oauth_client", str(client_pk))
    if body.is_public is not None:
        oc.is_public = body.is_public
    if body.redirect_uris is not None:
        oc.redirect_uris = list(body.redirect_uris)
    if body.allowed_grant_types is not None:
        oc.allowed_grant_types = list(body.allowed_grant_types)
    if body.allowed_scopes is not None:
        oc.allowed_scopes = list(body.allowed_scopes)
    if body.allow_password_grant is not None:
        oc.allow_password_grant = body.allow_password_grant
    if body.client_secret is not None:
        oc.client_secret_hash = hash_secret(body.client_secret)
    await session.flush()
    return oc


async def delete_client(session: AsyncSession, client_pk: UUID) -> None:
    dal = AdminDAL(session)
    oc = await dal.oauth_client_get_by_id(client_pk)
    if not oc:
        raise AdminNotFoundError("oauth_client", str(client_pk))
    await dal.oauth_client_delete(oc)
    await session.flush()

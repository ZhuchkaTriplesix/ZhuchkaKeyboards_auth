"""Admin API: /api/v1/users, roles, MFA, OAuth clients (per docs/microservices/01-auth.md)."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from src.auth.db_models import OAuthClient, Role, User, UserRole
from src.auth.deps import require_admin_scope
from src.auth.passwords import hash_password, hash_secret
from src.database.dependencies import DbSession

router = APIRouter(dependencies=[Depends(require_admin_scope)])


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    identity_kind: Literal["customer", "staff"] = "staff"


class UserOut(BaseModel):
    id: UUID
    email: str
    is_active: bool
    identity_kind: str
    mfa_enabled: bool

    model_config = {"from_attributes": True}


class UserPatch(BaseModel):
    email: EmailStr | None = None
    is_active: bool | None = None
    identity_kind: Literal["customer", "staff"] | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class RolesPayload(BaseModel):
    role_names: list[str] = Field(default_factory=list)


class RoleOut(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class OAuthClientOut(BaseModel):
    id: UUID
    client_id: str
    is_public: bool
    redirect_uris: list[str]
    allowed_grant_types: list[str]
    allowed_scopes: list[str]
    allow_password_grant: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OAuthClientCreate(BaseModel):
    client_id: str = Field(min_length=2, max_length=128)
    is_public: bool = False
    redirect_uris: list[str] = Field(default_factory=list)
    allowed_grant_types: list[str] | None = None
    allowed_scopes: list[str] | None = None
    allow_password_grant: bool = False
    client_secret: str | None = Field(None, min_length=8, max_length=256)


class OAuthClientCreated(OAuthClientOut):
    client_secret: str


class OAuthClientPatch(BaseModel):
    is_public: bool | None = None
    redirect_uris: list[str] | None = None
    allowed_grant_types: list[str] | None = None
    allowed_scopes: list[str] | None = None
    allow_password_grant: bool | None = None
    client_secret: str | None = Field(None, min_length=8, max_length=256)


async def _get_user(session: DbSession, user_id: UUID) -> User | None:
    r = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    return r.scalar_one_or_none()


@router.post("/users", response_model=UserOut)
async def create_user(session: DbSession, body: UserCreate) -> User:
    email = body.email.strip().lower()
    r = await session.execute(select(User).where(User.email == email))
    if r.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="email_exists")
    user = User(
        email=email,
        identity_kind=body.identity_kind,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    rr = await session.execute(select(Role).where(Role.name == "user"))
    role = rr.scalar_one_or_none()
    if role:
        session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(session: DbSession) -> list[User]:
    r = await session.execute(select(User).order_by(User.created_at.desc()).limit(200))
    return list(r.scalars().all())


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(session: DbSession, user_id: UUID) -> User:
    user = await _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def patch_user(session: DbSession, user_id: UUID, body: UserPatch) -> User:
    user = await _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    if body.email is not None:
        new_email = body.email.strip().lower()
        if new_email != user.email:
            dup = await session.execute(select(User).where(User.email == new_email))
            if dup.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="email_exists")
            user.email = new_email
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.identity_kind is not None:
        user.identity_kind = body.identity_kind
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    await session.flush()
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(session: DbSession, user_id: UUID) -> Response:
    user = await _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    user.is_active = False
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/users/{user_id}/roles", response_model=UserOut)
async def replace_user_roles(session: DbSession, user_id: UUID, body: RolesPayload) -> User:
    user = await _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for name in body.role_names:
        rr = await session.execute(select(Role).where(Role.name == name.strip()))
        role = rr.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=400, detail=f"unknown_role:{name}")
        session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()
    await session.refresh(user, attribute_names=["roles"])
    return user


@router.post("/users/{user_id}/roles", response_model=UserOut)
async def add_user_roles(session: DbSession, user_id: UUID, body: RolesPayload) -> User:
    user = await _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    rur = await session.execute(select(UserRole).where(UserRole.user_id == user_id))
    have = {ur.role_id for ur in rur.scalars().all()}
    for name in body.role_names:
        rr = await session.execute(select(Role).where(Role.name == name.strip()))
        role = rr.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=400, detail=f"unknown_role:{name}")
        if role.id not in have:
            session.add(UserRole(user_id=user.id, role_id=role.id))
            have.add(role.id)
    await session.flush()
    await session.refresh(user, attribute_names=["roles"])
    return user


@router.post("/users/{user_id}/mfa", response_model=UserOut)
async def enable_user_mfa(session: DbSession, user_id: UUID) -> User:
    user = await _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    user.mfa_enabled = True
    await session.flush()
    return user


@router.delete("/users/{user_id}/mfa", response_model=UserOut)
async def disable_user_mfa(session: DbSession, user_id: UUID) -> User:
    user = await _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    user.mfa_enabled = False
    await session.flush()
    return user


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(session: DbSession) -> list[Role]:
    r = await session.execute(select(Role).order_by(Role.name))
    return list(r.scalars().all())


@router.get("/clients", response_model=list[OAuthClientOut])
async def list_clients(session: DbSession) -> list[OAuthClient]:
    r = await session.execute(
        select(OAuthClient).order_by(OAuthClient.created_at.desc()).limit(500)
    )
    return list(r.scalars().all())


@router.get("/clients/{client_pk}", response_model=OAuthClientOut)
async def get_client(session: DbSession, client_pk: UUID) -> OAuthClient:
    r = await session.execute(select(OAuthClient).where(OAuthClient.id == client_pk))
    row = r.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="client_not_found")
    return row


@router.post("/clients", response_model=OAuthClientCreated, status_code=status.HTTP_201_CREATED)
async def create_client(session: DbSession, body: OAuthClientCreate) -> OAuthClient:
    cid = body.client_id.strip()
    dup = await session.execute(select(OAuthClient).where(OAuthClient.client_id == cid))
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="client_id_exists")
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
    session.add(oc)
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


@router.patch("/clients/{client_pk}", response_model=OAuthClientOut)
async def patch_client(session: DbSession, client_pk: UUID, body: OAuthClientPatch) -> OAuthClient:
    r = await session.execute(select(OAuthClient).where(OAuthClient.id == client_pk))
    oc = r.scalar_one_or_none()
    if not oc:
        raise HTTPException(status_code=404, detail="client_not_found")
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


@router.delete("/clients/{client_pk}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(session: DbSession, client_pk: UUID) -> Response:
    r = await session.execute(select(OAuthClient).where(OAuthClient.id == client_pk))
    oc = r.scalar_one_or_none()
    if not oc:
        raise HTTPException(status_code=404, detail="client_not_found")
    await session.delete(oc)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

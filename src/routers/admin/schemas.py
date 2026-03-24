"""Pydantic-схемы admin API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.routers.admin.enums import IdentityKind


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    identity_kind: IdentityKind = IdentityKind.staff


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
    identity_kind: IdentityKind | None = None
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

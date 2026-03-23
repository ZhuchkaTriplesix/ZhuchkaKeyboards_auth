"""Admin API: users (bootstrap extension)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from src.auth.db_models import Role, User, UserRole
from src.auth.deps import require_admin_scope
from src.auth.passwords import hash_password
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

    model_config = {"from_attributes": True}


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

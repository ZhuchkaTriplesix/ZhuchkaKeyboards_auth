"""Доступ к БД для admin API (без бизнес-логики и HTTP)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.db_models import OAuthClient, Role, User, UserRole


class AdminDAL:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def user_get_by_id(self, user_id: UUID) -> User | None:
        r = await self.session.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        return r.scalar_one_or_none()

    async def user_get_by_email(self, email: str) -> User | None:
        r = await self.session.execute(select(User).where(User.email == email))
        return r.scalar_one_or_none()

    async def users_list(self, *, limit: int = 200) -> list[User]:
        r = await self.session.execute(select(User).order_by(User.created_at.desc()).limit(limit))
        return list(r.scalars().all())

    async def role_by_name(self, name: str) -> Role | None:
        r = await self.session.execute(select(Role).where(Role.name == name.strip()))
        return r.scalar_one_or_none()

    async def roles_all(self) -> list[Role]:
        r = await self.session.execute(select(Role).order_by(Role.name))
        return list(r.scalars().all())

    async def user_roles_ids(self, user_id: UUID) -> set[UUID]:
        r = await self.session.execute(select(UserRole).where(UserRole.user_id == user_id))
        return {ur.role_id for ur in r.scalars().all()}

    async def user_roles_delete_all(self, user_id: UUID) -> None:
        await self.session.execute(delete(UserRole).where(UserRole.user_id == user_id))

    def user_add(self, user: User) -> None:
        self.session.add(user)

    def user_role_add(self, user_id: UUID, role_id: UUID) -> None:
        self.session.add(UserRole(user_id=user_id, role_id=role_id))

    async def oauth_clients_list(self, *, limit: int = 500) -> list[OAuthClient]:
        r = await self.session.execute(
            select(OAuthClient).order_by(OAuthClient.created_at.desc()).limit(limit)
        )
        return list(r.scalars().all())

    async def oauth_client_get_by_id(self, client_pk: UUID) -> OAuthClient | None:
        r = await self.session.execute(select(OAuthClient).where(OAuthClient.id == client_pk))
        return r.scalar_one_or_none()

    async def oauth_client_get_by_client_id(self, client_id: str) -> OAuthClient | None:
        r = await self.session.execute(
            select(OAuthClient).where(OAuthClient.client_id == client_id)
        )
        return r.scalar_one_or_none()

    def oauth_client_add(self, oc: OAuthClient) -> None:
        self.session.add(oc)

    async def oauth_client_delete(self, oc: OAuthClient) -> None:
        await self.session.delete(oc)

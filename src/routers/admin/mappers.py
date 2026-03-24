"""ORM → Pydantic DTO (только ответные схемы наружу)."""

from __future__ import annotations

from src.auth.db_models import OAuthClient, Role, User
from src.routers.admin.schemas import OAuthClientOut, RoleOut, UserOut


def user_out(user: User) -> UserOut:
    return UserOut.model_validate(user)


def role_out(role: Role) -> RoleOut:
    return RoleOut.model_validate(role)


def oauth_client_out(oc: OAuthClient) -> OAuthClientOut:
    return OAuthClientOut.model_validate(oc)

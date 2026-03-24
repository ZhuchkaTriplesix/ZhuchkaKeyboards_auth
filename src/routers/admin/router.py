from __future__ import annotations

# HTTP-слой admin API: только маршруты и маппинг ошибок домена → HTTP.
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.auth.deps import require_admin_scope
from src.database.dependencies import DbSession
from src.routers.admin import actions
from src.routers.admin.exceptions import (
    AdminNotFoundError,
    ClientIdExistsError,
    EmailExistsError,
    UnknownRoleError,
)
from src.routers.admin.schemas import (
    OAuthClientCreate,
    OAuthClientCreated,
    OAuthClientOut,
    OAuthClientPatch,
    RoleOut,
    RolesPayload,
    UserCreate,
    UserOut,
    UserPatch,
)

router = APIRouter(dependencies=[Depends(require_admin_scope)])


def _raise_mapped(exc: BaseException) -> None:
    if isinstance(exc, EmailExistsError):
        raise HTTPException(status_code=409, detail="email_exists") from exc
    if isinstance(exc, ClientIdExistsError):
        raise HTTPException(status_code=409, detail="client_id_exists") from exc
    if isinstance(exc, UnknownRoleError):
        raise HTTPException(status_code=400, detail=f"unknown_role:{exc.role_name}") from exc
    if isinstance(exc, AdminNotFoundError):
        if exc.resource == "user":
            raise HTTPException(status_code=404, detail="user_not_found") from exc
        if exc.resource == "oauth_client":
            raise HTTPException(status_code=404, detail="client_not_found") from exc
    raise exc


@router.post(
    "/users",
    response_model=UserOut,
    summary="Создать пользователя",
    description="Создание учётной записи (staff/customer) с начальной ролью `user` при наличии.",
)
async def create_user(session: DbSession, body: UserCreate) -> UserOut:
    try:
        return await actions.create_user(session, body)
    except Exception as e:
        _raise_mapped(e)


@router.get(
    "/users",
    response_model=list[UserOut],
    summary="Список пользователей",
    description="До 200 последних записей по дате создания.",
)
async def list_users(session: DbSession) -> list[UserOut]:
    return await actions.list_users(session)


@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    summary="Получить пользователя",
    description="Возвращает пользователя по UUID.",
)
async def get_user(session: DbSession, user_id: UUID) -> UserOut:
    try:
        return await actions.get_user(session, user_id)
    except Exception as e:
        _raise_mapped(e)


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    summary="Обновить пользователя",
    description="Частичное обновление email, пароля, флагов.",
)
async def patch_user(session: DbSession, user_id: UUID, body: UserPatch) -> UserOut:
    try:
        return await actions.patch_user(session, user_id, body)
    except Exception as e:
        _raise_mapped(e)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Деактивировать пользователя",
    description="Мягкое удаление: is_active = false.",
)
async def delete_user(session: DbSession, user_id: UUID) -> Response:
    try:
        await actions.soft_delete_user(session, user_id)
    except Exception as e:
        _raise_mapped(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/users/{user_id}/roles",
    response_model=UserOut,
    summary="Заменить роли пользователя",
    description="Полная замена набора ролей по именам.",
)
async def replace_user_roles(session: DbSession, user_id: UUID, body: RolesPayload) -> UserOut:
    try:
        return await actions.replace_user_roles(session, user_id, body)
    except Exception as e:
        _raise_mapped(e)


@router.post(
    "/users/{user_id}/roles",
    response_model=UserOut,
    summary="Добавить роли пользователю",
    description="Идемпотентное добавление без дублей.",
)
async def add_user_roles(session: DbSession, user_id: UUID, body: RolesPayload) -> UserOut:
    try:
        return await actions.add_user_roles(session, user_id, body)
    except Exception as e:
        _raise_mapped(e)


@router.post(
    "/users/{user_id}/mfa",
    response_model=UserOut,
    summary="Включить MFA",
    description="Устанавливает mfa_enabled = true.",
)
async def enable_user_mfa(session: DbSession, user_id: UUID) -> UserOut:
    try:
        return await actions.set_user_mfa(session, user_id, enabled=True)
    except Exception as e:
        _raise_mapped(e)


@router.delete(
    "/users/{user_id}/mfa",
    response_model=UserOut,
    summary="Выключить MFA",
    description="Устанавливает mfa_enabled = false.",
)
async def disable_user_mfa(session: DbSession, user_id: UUID) -> UserOut:
    try:
        return await actions.set_user_mfa(session, user_id, enabled=False)
    except Exception as e:
        _raise_mapped(e)


@router.get(
    "/roles",
    response_model=list[RoleOut],
    summary="Список ролей",
    description="Все роли в алфавитном порядке.",
)
async def list_roles(session: DbSession) -> list[RoleOut]:
    return await actions.list_roles(session)


@router.get(
    "/clients",
    response_model=list[OAuthClientOut],
    summary="Список OAuth-клиентов",
    description="До 500 записей.",
)
async def list_clients(session: DbSession) -> list[OAuthClientOut]:
    return await actions.list_clients(session)


@router.get(
    "/clients/{client_pk}",
    response_model=OAuthClientOut,
    summary="Получить OAuth-клиента",
    description="По внутреннему UUID записи.",
)
async def get_client(session: DbSession, client_pk: UUID) -> OAuthClientOut:
    try:
        return await actions.get_client(session, client_pk)
    except Exception as e:
        _raise_mapped(e)


@router.post(
    "/clients",
    response_model=OAuthClientCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Создать OAuth-клиента",
    description="Секрет показывается один раз в ответе (или передан явно).",
)
async def create_client(session: DbSession, body: OAuthClientCreate) -> OAuthClientCreated:
    try:
        return await actions.create_client(session, body)
    except Exception as e:
        _raise_mapped(e)


@router.patch(
    "/clients/{client_pk}",
    response_model=OAuthClientOut,
    summary="Обновить OAuth-клиента",
    description="Частичное обновление полей и опционально ротация client_secret.",
)
async def patch_client(
    session: DbSession, client_pk: UUID, body: OAuthClientPatch
) -> OAuthClientOut:
    try:
        return await actions.patch_client(session, client_pk, body)
    except Exception as e:
        _raise_mapped(e)


@router.delete(
    "/clients/{client_pk}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить OAuth-клиента",
    description="Жёсткое удаление записи клиента.",
)
async def delete_client(session: DbSession, client_pk: UUID) -> Response:
    try:
        await actions.delete_client(session, client_pk)
    except Exception as e:
        _raise_mapped(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

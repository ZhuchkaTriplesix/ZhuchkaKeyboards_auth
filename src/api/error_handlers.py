"""Глобальные обработчики: приводят HTTPException и валидацию к ApiErrorResponse."""

from __future__ import annotations

import re
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from src.api.error_schemas import ApiErrorResponse
from src.middlewares.database import get_request_id

# Сообщения для кодов, которые поднимаются строкой в HTTPException(detail="...").
_ERROR_MESSAGES: dict[str, str] = {
    "missing_bearer": "Требуется заголовок Authorization с Bearer-токеном.",
    "invalid_token": "Недействительный или просроченный access token.",
    "invalid_sub": "Некорректный идентификатор субъекта.",
    "forbidden": "Недостаточно прав (scope) для этой операции.",
    "email_exists": "Пользователь с таким email уже существует.",
    "client_id_exists": "OAuth client_id уже занят.",
    "user_not_found": "Пользователь не найден.",
    "client_not_found": "OAuth-клиент не найден.",
    "docs_auth_failed": "Неверные учётные данные для доступа к документации API.",
}


def _slug_code(s: str) -> str:
    s = s.strip()
    if re.match(r"^[a-z][a-z0-9_]*$", s):
        return s
    return "error"


def _message_for_code(code: str, raw: str) -> str:
    if code in _ERROR_MESSAGES:
        return _ERROR_MESSAGES[code]
    if raw.startswith("unknown_role:"):
        role = raw.split(":", 1)[-1].strip()
        return f"Неизвестная роль: {role}"
    return raw if len(raw) < 200 else "Ошибка запроса"


def _http_exception_to_body(detail: Any) -> tuple[str, str, dict[str, Any] | list[Any] | None]:
    if isinstance(detail, dict) and "code" in detail:
        return (
            str(detail["code"]),
            str(detail.get("message", detail["code"])),
            detail.get("details") if isinstance(detail.get("details"), dict | list) else None,
        )
    if isinstance(detail, str):
        if detail.startswith("unknown_role:"):
            role = detail.split(":", 1)[-1].strip()
            return "unknown_role", _message_for_code("unknown_role", detail), {"role": role}
        code = _slug_code(detail)
        return code, _message_for_code(code, detail), None
    return "error", str(detail), None


def register_error_handlers(app: Any) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Any, exc: HTTPException) -> JSONResponse:
        rid = get_request_id()
        code, message, details = _http_exception_to_body(exc.detail)
        body = ApiErrorResponse(code=code, message=message, details=details, request_id=rid)
        headers: dict[str, str] = {}
        if rid:
            headers["X-Request-Id"] = rid
        if getattr(exc, "headers", None):
            headers.update(dict(exc.headers))
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(exclude_none=True),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Any, exc: RequestValidationError
    ) -> JSONResponse:
        rid = get_request_id()
        body = ApiErrorResponse(
            code="validation_error",
            message="Ошибка валидации тела или параметров запроса.",
            details={"errors": jsonable_encoder(exc.errors())},
            request_id=rid,
        )
        headers: dict[str, str] = {}
        if rid:
            headers["X-Request-Id"] = rid
        return JSONResponse(
            status_code=422,
            content=body.model_dump(exclude_none=True),
            headers=headers,
        )

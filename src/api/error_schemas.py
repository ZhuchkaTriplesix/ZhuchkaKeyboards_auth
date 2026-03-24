"""Схемы тел для ошибок REST (сквозной envelope по docs/microservices-api-requirements.md)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    """Единый формат ошибки: `code`, `message`, опционально `details` и `request_id`."""

    code: str = Field(..., description="Стабильный машинный код ошибки")
    message: str = Field(..., description="Человекочитаемое сообщение")
    details: dict[str, Any] | list[Any] | None = Field(
        default=None,
        description="Дополнительный контекст (поля валидации и т.д.)",
    )
    request_id: str | None = Field(
        default=None,
        description="Корреляция с логами (совпадает с X-Request-Id ответа)",
    )

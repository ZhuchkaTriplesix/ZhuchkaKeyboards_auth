from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    office_id: UUID | None
    staff_id: UUID | None
    username: str
    permissions: list[str]
    roles: list[str]

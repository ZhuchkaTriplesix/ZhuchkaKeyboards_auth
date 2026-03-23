import uuid
from uuid import UUID

from sqlalchemy import types
from sqlalchemy.orm import Mapped

from src.database.base import Base


class Root(Base):
    id: Mapped[UUID] = mapped_column(types.Uuid, primary_key=True, default=uuid.uuid4)

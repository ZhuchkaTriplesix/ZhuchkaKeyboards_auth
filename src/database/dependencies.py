from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.core import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]

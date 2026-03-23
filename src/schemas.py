from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class User(BaseModel):
    office_id: Optional[UUID]
    staff_id: Optional[UUID]
    username: str
    permissions: List[str]
    roles: List[str]


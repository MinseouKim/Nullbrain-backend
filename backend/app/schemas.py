from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class ProfileCreate(BaseModel):
    version: int = 1
    body: Dict[str, Any]
    measures: Dict[str, Any]

class ProfileOut(BaseModel):
    id: UUID
    version: int
    body: Dict[str, Any]
    measures: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2

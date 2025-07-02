from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from uuid import UUID


class SystemSettingsBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: Any
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    is_public: bool = False


class SystemSettingsCreate(SystemSettingsBase):
    pass


class SystemSettingsUpdate(BaseModel):
    value: Optional[Any] = None
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    is_public: Optional[bool] = None


class SystemSettingsResponse(SystemSettingsBase):
    id: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

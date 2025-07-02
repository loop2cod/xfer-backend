from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime, timezone
from uuid import UUID


class UserActivityBase(BaseModel):
    action: str = Field(..., min_length=1, max_length=255)
    resource_type: Optional[str] = Field(None, max_length=100)
    resource_id: Optional[str] = Field(None, max_length=255)
    details: Optional[dict] = None


class UserActivityCreate(UserActivityBase):
    pass


class UserActivityResponse(UserActivityBase):
    id: UUID
    user_id: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v.tzinfo else v.replace(tzinfo=timezone.utc).isoformat()
        }


class UserActivityListResponse(BaseModel):
    activities: list[UserActivityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
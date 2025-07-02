from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from uuid import UUID


class AuditLogBase(BaseModel):
    action: str = Field(..., min_length=1, max_length=255)
    resource_type: str = Field(..., min_length=1, max_length=100)
    resource_id: Optional[str] = Field(None, max_length=255)
    details: Optional[dict] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: UUID
    admin_id: UUID
    admin_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

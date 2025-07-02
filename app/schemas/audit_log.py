from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
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

    # New fields for enhanced audit log display
    type: str = Field(..., description="Log type derived from resource_type")
    activity_description: str = Field(..., description="Human-readable description of the activity")
    created_by: str = Field(..., description="Name of the admin who performed the action")
    reference_link: Optional[str] = Field(None, description="Link to the related resource if applicable")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: (v.astimezone(timezone.utc) if v.tzinfo else v.replace(tzinfo=timezone.utc)).strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
        }

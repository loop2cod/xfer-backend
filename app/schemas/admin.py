from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID


class AdminBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str = "admin"


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminCreate(AdminBase):
    password: str
    permissions: Optional[Dict[str, Any]] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['super_admin', 'admin', 'operator']:
            raise ValueError('Invalid role')
        return v


class AdminUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AdminResponse(AdminBase):
    id: UUID
    permissions: Optional[Dict[str, Any]] = None
    is_active: bool
    is_super_admin: bool
    api_key: Optional[str] = None
    api_key_expires_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v.tzinfo else v.replace(tzinfo=timezone.utc).isoformat()
        }


class AdminPermissionUpdate(BaseModel):
    permissions: Dict[str, Any]


class AdminRolePermissions(BaseModel):
    role: str
    permissions: List[str]
    description: str


# Default permissions for different roles
DEFAULT_PERMISSIONS = {
    "super_admin": {
        "can_manage_admins": True,
        "can_manage_users": True,
        "can_approve_transfers": True,
        "can_view_reports": True,
        "can_manage_wallets": True,
        "can_view_audit_logs": True,
        "can_manage_system_settings": True,
        "can_export_data": True
    },
    "admin": {
        "can_manage_admins": False,
        "can_manage_users": True,
        "can_approve_transfers": True,
        "can_view_reports": True,
        "can_manage_wallets": True,
        "can_view_audit_logs": True,
        "can_manage_system_settings": False,
        "can_export_data": True
    },
    "operator": {
        "can_manage_admins": False,
        "can_manage_users": False,
        "can_approve_transfers": True,
        "can_view_reports": True,
        "can_manage_wallets": False,
        "can_view_audit_logs": False,
        "can_manage_system_settings": False,
        "can_export_data": False
    }
}
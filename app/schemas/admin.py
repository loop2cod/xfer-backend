from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class AdminBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str = "admin"


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
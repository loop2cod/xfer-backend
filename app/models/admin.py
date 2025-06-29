from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
import uuid
from app.db.database import Base
from app.core.database_types import UUIDType


class Admin(Base):
    __tablename__ = "admins"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    
    # Admin Details
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Role and Permissions
    role = Column(String(50), default="admin")  # super_admin, admin, operator
    permissions = Column(JSON, nullable=True)
    # Structure: {
    #   "can_approve_transfers": true,
    #   "can_manage_users": true,
    #   "can_view_reports": true,
    #   "can_manage_wallets": false
    # }
    
    # Status
    is_active = Column(Boolean, default=True)
    is_super_admin = Column(Boolean, default=False)
    
    # API Access
    api_key = Column(String(255), nullable=True, unique=True)
    api_key_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Security
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_attempts = Column(String(10), default="0")
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_by = Column(UUIDType, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Admin(email='{self.email}', role='{self.role}')>"
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime, timezone
# from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base
from app.core.database_types import UUIDType


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUIDType, ForeignKey("admins.id"), nullable=False)
    action = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc)  # Ensure UTC timezone
    )

    # Relationships
    # admin = relationship("Admin", back_populates="audit_logs")  # Commented out to avoid circular import

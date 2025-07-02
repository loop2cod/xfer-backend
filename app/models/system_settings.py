from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.database import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False, index=True)
    is_public = Column(Boolean, default=False, nullable=False)
    updated_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

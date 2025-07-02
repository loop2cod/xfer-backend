from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base
from app.core.database_types import UUIDType
from app.core.security import generate_customer_id
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(20), unique=True, nullable=False, default=generate_customer_id)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # KYC Information
    kyc_status = Column(String(50), default="pending")  # pending, approved, rejected
    kyc_documents = Column(Text, nullable=True)  # JSON string
    
    # Account Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_code = Column(String(6), nullable=True)
    verification_code_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # SQLite will store this as local time
        default=datetime.now(timezone.utc)  # Python will use UTC if not provided
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=datetime.now(timezone.utc),
        default=datetime.now(timezone.utc)
    )
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    transfer_requests = relationship("TransferRequest", back_populates="user")
    wallets = relationship("Wallet", back_populates="user")
    notes = relationship("UserNote", back_populates="user")

    def __repr__(self):
        return f"<User(email='{self.email}', kyc_status='{self.kyc_status}')>"
    
    @staticmethod
    def utcnow():
        return datetime.utcnow()
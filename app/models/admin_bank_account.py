from sqlalchemy import Column, String, DateTime, Numeric, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base
from app.core.database_types import UUIDType
from datetime import datetime, timezone


class AdminBankAccount(Base):
    __tablename__ = "admin_bank_accounts"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    
    # Bank Account Details
    name = Column(String(100), nullable=False)
    bank_name = Column(String(100), nullable=False)
    account_number = Column(String(50), nullable=False)
    routing_number = Column(String(50), nullable=True)
    account_type = Column(String(20), nullable=False)  # Checking, Savings, Business
    
    # Fee Information
    fee_percentage = Column(Numeric(5, 2), default=0)  # Fee percentage (e.g., 1.5%)
    
    # Account Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Only one account should be primary
    
    # Additional Information
    account_holder_name = Column(String(100), nullable=True)
    swift_code = Column(String(50), nullable=True)
    iban = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=datetime.now(timezone.utc),
        default=datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<AdminBankAccount(name='{self.name}', bank='{self.bank_name}', is_primary='{self.is_primary}')>"
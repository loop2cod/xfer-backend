from sqlalchemy import Column, String, DateTime, Numeric, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base
from app.core.database_types import UUIDType
from datetime import datetime, timezone


class AdminWallet(Base):
    __tablename__ = "admin_wallets"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    
    # Wallet Details
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False, unique=True, index=True)
    currency = Column(String(10), nullable=False, default="USDT")
    network = Column(String(20), nullable=False, default="TRC20")  # TRC20, ERC20, etc.
    
    # Fee Information
    fee_percentage = Column(Numeric(5, 2), default=0)  # Fee percentage (e.g., 1.5%)
    
    # Wallet Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Only one wallet should be primary
    
    # Additional Information
    notes = Column(Text, nullable=True)
    
    # Security
    last_transaction_hash = Column(String(255), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    
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
        return f"<AdminWallet(name='{self.name}', address='{self.address}', is_primary='{self.is_primary}')>"
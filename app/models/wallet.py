from sqlalchemy import Column, String, DateTime, Numeric, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base
from app.core.database_types import UUIDType


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    # Wallet Details
    address = Column(String(255), nullable=False, unique=True, index=True)
    currency = Column(String(10), nullable=False, default="USDT")
    network = Column(String(20), nullable=False, default="TRC20")  # TRC20, ERC20, etc.
    
    # Balance Information
    balance = Column(Numeric(20, 8), default=0)
    pending_balance = Column(Numeric(20, 8), default=0)
    frozen_balance = Column(Numeric(20, 8), default=0)
    
    # Wallet Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    wallet_type = Column(String(20), default="user")  # user, admin, system
    
    # Additional Information
    label = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Security
    last_transaction_hash = Column(String(255), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="wallets")

    def __repr__(self):
        return f"<Wallet(address='{self.address}', currency='{self.currency}', balance='{self.balance}')>"
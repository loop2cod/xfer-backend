from sqlalchemy import Column, String, DateTime, Numeric, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base
from app.core.database_types import UUIDType


class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    # Transfer Details
    type = Column(String(20), nullable=False)  # crypto-to-fiat, fiat-to-crypto
    amount = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), nullable=False)
    net_amount = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(10), nullable=False, default="USDT")
    
    # Status and Processing
    status = Column(String(20), default="pending")  # pending, processing, completed, failed, cancelled
    status_message = Column(Text, nullable=True)
    priority = Column(String(10), default="normal")  # low, normal, high
    
    # Crypto Transaction Details
    crypto_tx_hash = Column(String(255), nullable=True)
    deposit_wallet_address = Column(String(255), nullable=True)
    admin_wallet_address = Column(String(255), nullable=True)
    confirmation_count = Column(Numeric(3, 0), default=0)
    required_confirmations = Column(Numeric(3, 0), default=6)
    
    # Bank Account Information (for crypto-to-fiat)
    bank_account_info = Column(JSON, nullable=True)
    # Structure: {
    #   "account_name": "John Doe",
    #   "account_number": "1234567890",
    #   "bank_name": "Chase Bank",
    #   "routing_number": "021000021",
    #   "transfer_amount": "495.00"
    # }
    
    # Multiple bank accounts support
    bank_accounts = Column(JSON, nullable=True)
    # Structure: [
    #   {
    #     "account_name": "John Doe",
    #     "account_number": "1234567890", 
    #     "bank_name": "Chase Bank",
    #     "routing_number": "021000021",
    #     "transfer_amount": "250.00"
    #   },
    #   {...}
    # ]
    
    # Processing Information
    processed_by = Column(UUIDType, nullable=True)  # Admin user ID
    processing_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transfer_requests")

    def __repr__(self):
        return f"<TransferRequest(id='{self.id}', type='{self.type}', amount='{self.amount}', status='{self.status}')>"
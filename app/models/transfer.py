from sqlalchemy import Column, String, DateTime, Numeric, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base
from app.core.database_types import UUIDType
from app.core.security import generate_transfer_id
from datetime import datetime, timezone


class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    transfer_id = Column(String(20), unique=True, nullable=False, default=generate_transfer_id)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    # Transfer Details
    transfer_type = Column(String(20), nullable=False)  # crypto-to-fiat, fiat-to-crypto, crypto_purchase, bank_purchase
    type_ = Column("type", String(20), nullable=False)  # crypto-to-fiat, fiat-to-crypto (backward compatibility)
    amount = Column(Numeric(20, 8), nullable=False)
    fee_amount = Column(Numeric(20, 8), nullable=False, default=0)
    fee = Column(Numeric(20, 8), nullable=False)  # backward compatibility
    amount_after_fee = Column(Numeric(20, 8), nullable=False)
    net_amount = Column(Numeric(20, 8), nullable=False)  # backward compatibility
    currency = Column(String(10), nullable=False, default="USDT")
    
    # Status and Processing
    status = Column(String(20), default="pending")  # pending, processing, completed, failed, cancelled
    status_message = Column(Text, nullable=True)
    priority = Column(String(10), default="normal")  # low, normal, high
    
    # Crypto Transaction Details
    crypto_tx_hash = Column(String(255), nullable=True)
    deposit_wallet_address = Column(String(255), nullable=True)
    recipient_wallet = Column(String(255), nullable=True)  # User's wallet for purchases
    admin_wallet_address = Column(String(255), nullable=True)
    admin_wallet_id = Column(UUIDType, ForeignKey("admin_wallets.id"), nullable=True)
    network = Column(String(20), nullable=True)  # TRC20, ERC20, etc.
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
    
    # Admin Bank Account (for purchases)
    admin_bank_account_id = Column(UUIDType, ForeignKey("admin_bank_accounts.id"), nullable=True)
    payment_method = Column(String(20), nullable=True)  # crypto, bank_transfer, etc.
    
    # Processing Information
    processed_by = Column(UUIDType, nullable=True)  # Admin user ID
    processing_notes = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)  # General notes
    admin_remarks = Column(Text, nullable=True)  # Admin remarks visible to client
    internal_notes = Column(Text, nullable=True)  # Internal admin notes (not visible to client)
    status_history = Column(JSON, nullable=True)  # Track status changes with timestamps
    
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
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transfer_requests")
    admin_wallet = relationship("AdminWallet", foreign_keys=[admin_wallet_id])
    admin_bank_account = relationship("AdminBankAccount", foreign_keys=[admin_bank_account_id])

    def __repr__(self):
        return f"<TransferRequest(id='{self.id}', type='{self.type_}', amount='{self.amount}', status='{self.status}')>"
    
    @staticmethod
    def utcnow():
        return datetime.utcnow()
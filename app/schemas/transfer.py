from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class BankAccountInfo(BaseModel):
    account_name: str
    account_number: str
    bank_name: str
    routing_number: str
    transfer_amount: str


class TransferBase(BaseModel):
    type: str  # crypto-to-fiat, fiat-to-crypto
    amount: Decimal
    currency: str = "USDT"


class TransferCreate(TransferBase):
    deposit_wallet_address: Optional[str] = None
    crypto_tx_hash: Optional[str] = None
    bank_account_info: Optional[BankAccountInfo] = None
    bank_accounts: Optional[List[BankAccountInfo]] = None
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ['crypto-to-fiat', 'fiat-to-crypto']:
            raise ValueError('Type must be either crypto-to-fiat or fiat-to-crypto')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v


class TransferUpdate(BaseModel):
    status: Optional[str] = None
    status_message: Optional[str] = None
    crypto_tx_hash: Optional[str] = None
    confirmation_count: Optional[int] = None
    processing_notes: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v and v not in ['pending', 'processing', 'completed', 'failed', 'cancelled']:
            raise ValueError('Invalid status')
        return v


class TransferResponse(TransferBase):
    id: UUID
    user_id: UUID
    fee: Decimal
    net_amount: Decimal
    status: str
    status_message: Optional[str] = None
    crypto_tx_hash: Optional[str] = None
    deposit_wallet_address: Optional[str] = None
    admin_wallet_address: Optional[str] = None
    confirmation_count: Optional[int] = None
    required_confirmations: Optional[int] = None
    bank_account_info: Optional[Dict[str, Any]] = None
    bank_accounts: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TransferStats(BaseModel):
    total_requests: int
    pending_requests: int
    completed_requests: int
    failed_requests: int
    total_volume: float
    total_fees: float
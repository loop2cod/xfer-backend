from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID


class UserInfo(BaseModel):
    """Simplified user info for transfer responses"""
    id: UUID
    customer_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class BankAccountInfo(BaseModel):
    account_name: str = Field(..., min_length=2, max_length=100, description="Account holder name")
    account_number: str = Field(..., min_length=5, max_length=50, description="Bank account number")
    bank_name: str = Field(..., min_length=2, max_length=100, description="Bank name")
    routing_number: str = Field(..., min_length=5, max_length=20, description="Bank routing number")
    transfer_amount: str = Field(..., description="Amount to transfer to this account")

    @validator('transfer_amount')
    def validate_transfer_amount(cls, v):
        try:
            amount = Decimal(v)
            if amount <= 0:
                raise ValueError('Transfer amount must be greater than 0')
            return v
        except (ValueError, TypeError):
            raise ValueError('Transfer amount must be a valid number')


class TransferBase(BaseModel):
    type: str  # crypto-to-fiat, fiat-to-crypto
    amount: Decimal
    currency: str = "USDT"


class TransferCreate(TransferBase):
    deposit_wallet_address: Optional[str] = Field(None, min_length=20, max_length=255, description="User's wallet address for deposit")
    crypto_tx_hash: Optional[str] = Field(None, min_length=20, max_length=255, description="Blockchain transaction hash")
    bank_account_info: Optional[BankAccountInfo] = Field(None, description="Single bank account info (legacy)")
    bank_accounts: Optional[List[BankAccountInfo]] = Field(None, description="Multiple bank accounts for distribution")
    network: Optional[str] = Field(default="TRC20", description="Blockchain network")

    @validator('type')
    def validate_type(cls, v):
        if v not in ['crypto-to-fiat', 'fiat-to-crypto']:
            raise ValueError('Type must be either crypto-to-fiat or fiat-to-crypto')
        return v

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v > Decimal('1000000'):  # 1M limit
            raise ValueError('Amount exceeds maximum limit')
        return v

    @validator('bank_accounts')
    def validate_bank_accounts(cls, v, values):
        if v and len(v) > 10:  # Maximum 10 bank accounts
            raise ValueError('Maximum 10 bank accounts allowed')
        return v


class TransferUpdate(BaseModel):
    status: Optional[str] = None
    status_message: Optional[str] = None
    crypto_tx_hash: Optional[str] = None
    confirmation_count: Optional[int] = None
    processing_notes: Optional[str] = None
    admin_remarks: Optional[str] = None
    internal_notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = [
            'pending', 'processing', 'on_hold', 'completed', 'failed', 'cancelled', 'refunded'
        ]
        if v and v not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
        return v


class TransferResponse(BaseModel):
    id: UUID
    transfer_id: str
    user_id: UUID
    type: str = Field(alias="type_")  # Map from type_ field in the model
    transfer_type: str
    amount: Decimal
    currency: str = "USDT"
    fee: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    amount_after_fee: Decimal
    status: str
    status_message: Optional[str] = None
    priority: Optional[str] = None
    crypto_tx_hash: Optional[str] = None
    deposit_wallet_address: Optional[str] = None
    admin_wallet_address: Optional[str] = None
    admin_wallet_id: Optional[UUID] = None
    network: Optional[str] = None
    confirmation_count: Optional[int] = None
    required_confirmations: Optional[int] = None
    bank_account_info: Optional[Dict[str, Any]] = None
    bank_accounts: Optional[List[Dict[str, Any]]] = None
    processed_by: Optional[UUID] = None
    processing_notes: Optional[str] = None
    notes: Optional[str] = None
    admin_remarks: Optional[str] = None
    internal_notes: Optional[str] = None
    status_history: Optional[List[Dict[str, Any]]] = None
    user: Optional[UserInfo] = None  # Add user information
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v.tzinfo else v.replace(tzinfo=timezone.utc).isoformat()
        }


class TransferStats(BaseModel):
    total_requests: int
    pending_requests: int
    completed_requests: int
    failed_requests: int
    total_volume: float
    total_fees: float


class HashVerificationRequest(BaseModel):
    transaction_hash: str = Field(..., min_length=20, max_length=255, description="Transaction hash from blockchain")
    wallet_address: str = Field(..., min_length=20, max_length=255, description="Wallet address used for deposit")
    amount: Decimal = Field(..., gt=0, description="Expected transaction amount")
    network: Optional[str] = Field(default="TRC20", description="Blockchain network")


class HashVerificationResponse(BaseModel):
    is_valid: bool = Field(..., description="Whether the transaction is valid")
    confirmations: int = Field(..., ge=0, description="Number of blockchain confirmations")
    amount: Decimal = Field(..., description="Actual transaction amount")
    message: str = Field(..., description="Verification result message")
    network: Optional[str] = Field(None, description="Blockchain network")
    block_height: Optional[int] = Field(None, description="Block height of transaction")
    timestamp: Optional[datetime] = Field(None, description="Transaction timestamp")
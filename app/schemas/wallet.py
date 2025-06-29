from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class WalletBase(BaseModel):
    address: str
    currency: str = "USDT"
    network: str = "TRC20"
    label: Optional[str] = None


class WalletCreate(WalletBase):
    @validator('address')
    def validate_address(cls, v):
        # Basic validation for TRON addresses
        if not v.startswith('T') or len(v) != 34:
            raise ValueError('Invalid TRON address format')
        return v


class WalletUpdate(BaseModel):
    balance: Optional[Decimal] = None
    pending_balance: Optional[Decimal] = None
    frozen_balance: Optional[Decimal] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    label: Optional[str] = None
    notes: Optional[str] = None


class WalletResponse(WalletBase):
    id: UUID
    user_id: UUID
    balance: Decimal
    pending_balance: Decimal
    frozen_balance: Decimal
    is_active: bool
    is_verified: bool
    wallet_type: str
    notes: Optional[str] = None
    last_transaction_hash: Optional[str] = None
    last_activity_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
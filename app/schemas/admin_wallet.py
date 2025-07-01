from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class AdminWalletBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=10, max_length=255)
    currency: str = Field(default="USDT", min_length=1, max_length=10)
    network: str = Field(default="TRC20", min_length=1, max_length=20)
    fee_percentage: Decimal = Field(default=0, ge=0, le=100)
    is_active: bool = Field(default=True)
    is_primary: bool = Field(default=False)
    notes: Optional[str] = None


class AdminWalletCreate(AdminWalletBase):
    pass


class AdminWalletUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, min_length=10, max_length=255)
    currency: Optional[str] = Field(None, min_length=1, max_length=10)
    network: Optional[str] = Field(None, min_length=1, max_length=20)
    fee_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    notes: Optional[str] = None


class AdminWalletResponse(AdminWalletBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_activity_at: Optional[datetime] = None
    last_transaction_hash: Optional[str] = None

    class Config:
        orm_mode = True


class SetPrimaryWallet(BaseModel):
    wallet_id: UUID
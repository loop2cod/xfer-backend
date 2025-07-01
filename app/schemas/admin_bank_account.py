from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class AdminBankAccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    bank_name: str = Field(..., min_length=1, max_length=100)
    account_number: str = Field(..., min_length=4, max_length=50)
    routing_number: Optional[str] = Field(None, max_length=50)
    account_type: str = Field(..., min_length=1, max_length=20)
    fee_percentage: Decimal = Field(default=0, ge=0, le=100)
    is_active: bool = Field(default=True)
    is_primary: bool = Field(default=False)
    account_holder_name: Optional[str] = Field(None, max_length=100)
    swift_code: Optional[str] = Field(None, max_length=50)
    iban: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class AdminBankAccountCreate(AdminBankAccountBase):
    pass


class AdminBankAccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_number: Optional[str] = Field(None, min_length=4, max_length=50)
    routing_number: Optional[str] = Field(None, max_length=50)
    account_type: Optional[str] = Field(None, min_length=1, max_length=20)
    fee_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    account_holder_name: Optional[str] = Field(None, max_length=100)
    swift_code: Optional[str] = Field(None, max_length=50)
    iban: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class AdminBankAccountResponse(AdminBankAccountBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SetPrimaryBankAccount(BaseModel):
    account_id: UUID
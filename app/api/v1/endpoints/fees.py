from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Optional
from uuid import UUID

from app.api.deps import get_current_user
from app.db.database import get_db
from app.services.fee_service import FeeService
from app.schemas.base import BaseResponse
from pydantic import BaseModel, Field

router = APIRouter()


class FeeCalculationRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount to calculate fee for")
    wallet_id: Optional[UUID] = Field(None, description="Specific wallet ID (optional)")
    account_id: Optional[UUID] = Field(None, description="Specific bank account ID (optional)")


class FeeCalculationResponse(BaseModel):
    original_amount: float
    fee_percentage: float
    fee_amount: float
    amount_after_fee: float
    currency: str
    wallet: Optional[dict] = None
    bank_account: Optional[dict] = None


@router.post("/calculate-crypto-fee", response_model=BaseResponse[dict])
async def calculate_crypto_payment_fee(
    amount: Decimal = Query(..., gt=0, description="Payment amount"),
    wallet_id: Optional[UUID] = Query(None, description="Specific wallet ID (optional)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate fee for crypto payment"""
    try:
        fee_info = await FeeService.calculate_crypto_payment_fee(
            db=db,
            amount=amount,
            wallet_id=str(wallet_id) if wallet_id else None
        )
        return BaseResponse.success_response(
            data=fee_info,
            message="Crypto payment fee calculated successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating crypto payment fee"
        )


@router.post("/calculate-bank-fee", response_model=BaseResponse[dict])
async def calculate_bank_purchase_fee(
    amount: Decimal = Query(..., gt=0, description="Purchase amount"),
    account_id: Optional[UUID] = Query(None, description="Specific bank account ID (optional)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate fee for crypto purchase via bank account"""
    try:
        fee_info = await FeeService.calculate_bank_purchase_fee(
            db=db,
            amount=amount,
            account_id=str(account_id) if account_id else None
        )
        return BaseResponse.success_response(
            data=fee_info,
            message="Bank purchase fee calculated successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating bank purchase fee"
        )


@router.get("/payment-methods", response_model=BaseResponse[dict])
async def get_payment_methods(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get available payment methods with their fees"""
    try:
        # Get primary wallet
        primary_wallet_info = None
        try:
            wallet, wallet_fee = await FeeService.get_wallet_fee_info(db)
            primary_wallet_info = {
                "id": str(wallet.id),
                "name": wallet.name,
                "address": wallet.address,
                "currency": wallet.currency,
                "network": wallet.network,
                "fee_percentage": float(wallet_fee),
                "is_primary": wallet.is_primary
            }
        except ValueError:
            pass  # No primary wallet available
        
        # Get primary bank account
        primary_bank_info = None
        try:
            account, account_fee = await FeeService.get_bank_account_fee_info(db)
            primary_bank_info = {
                "id": str(account.id),
                "name": account.name,
                "bank_name": account.bank_name,
                "account_type": account.account_type,
                "fee_percentage": float(account_fee),
                "is_primary": account.is_primary
            }
        except ValueError:
            pass  # No primary bank account available
        
        return BaseResponse.success_response(
            data={
                "primary_wallet": primary_wallet_info,
                "primary_bank_account": primary_bank_info
            },
            message="Payment methods retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving payment methods"
        )
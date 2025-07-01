from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_current_user, get_current_admin
from app.db.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas.base import BaseResponse, MessageResponse
from app.models.user import User
from pydantic import BaseModel, Field, validator

router = APIRouter()


class CryptoPurchaseRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Purchase amount in USD")
    recipient_wallet: str = Field(..., min_length=26, max_length=62, description="User's wallet address")
    wallet_id: Optional[UUID] = Field(None, description="Specific admin wallet ID (optional)")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 100000:  # Max $100k per transaction
            raise ValueError('Amount exceeds maximum limit')
        return v


class BankPurchaseRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Purchase amount in USD")
    recipient_wallet: str = Field(..., min_length=26, max_length=62, description="User's wallet address")
    account_id: Optional[UUID] = Field(None, description="Specific admin bank account ID (optional)")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 100000:  # Max $100k per transaction
            raise ValueError('Amount exceeds maximum limit')
        return v


class PurchaseStatusUpdate(BaseModel):
    status: str = Field(..., description="New status")
    admin_notes: Optional[str] = Field(None, description="Admin notes")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'processing', 'completed', 'failed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v


@router.post("/crypto", response_model=BaseResponse[dict])
async def create_crypto_purchase(
    purchase_data: CryptoPurchaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a crypto purchase order"""
    try:
        result = await PurchaseService.create_crypto_purchase(
            db=db,
            user=current_user,
            amount=purchase_data.amount,
            recipient_wallet=purchase_data.recipient_wallet,
            wallet_id=str(purchase_data.wallet_id) if purchase_data.wallet_id else None
        )
        
        return BaseResponse.success_response(
            data={
                "transfer_id": str(result["transfer"].id),
                "transfer_code": result["transfer"].transfer_id,
                "payment_details": result["fee_info"],
                "status": result["status"]
            },
            message="Crypto purchase order created successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating crypto purchase order"
        )


@router.post("/bank", response_model=BaseResponse[dict])
async def create_bank_purchase(
    purchase_data: BankPurchaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a bank purchase order"""
    try:
        result = await PurchaseService.create_bank_purchase(
            db=db,
            user=current_user,
            amount=purchase_data.amount,
            recipient_wallet=purchase_data.recipient_wallet,
            account_id=str(purchase_data.account_id) if purchase_data.account_id else None
        )
        
        return BaseResponse.success_response(
            data={
                "transfer_id": str(result["transfer"].id),
                "transfer_code": result["transfer"].transfer_id,
                "payment_details": result["fee_info"],
                "status": result["status"]
            },
            message="Bank purchase order created successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating bank purchase order"
        )


@router.get("/my-purchases", response_model=BaseResponse[List[dict]])
async def get_my_purchases(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's purchase history"""
    try:
        purchases = await PurchaseService.get_user_purchases(
            db=db,
            user_id=str(current_user.id),
            skip=skip,
            limit=limit
        )
        
        purchase_data = []
        for purchase in purchases:
            purchase_data.append({
                "id": str(purchase.id),
                "transfer_id": purchase.transfer_id,
                "transfer_type": purchase.transfer_type,
                "amount": float(purchase.amount),
                "fee_amount": float(purchase.fee_amount) if purchase.fee_amount else 0,
                "amount_after_fee": float(purchase.amount_after_fee) if purchase.amount_after_fee else 0,
                "currency": purchase.currency,
                "status": purchase.status,
                "payment_method": purchase.payment_method,
                "recipient_wallet": purchase.recipient_wallet,
                "admin_wallet_address": purchase.admin_wallet_address,
                "network": purchase.network,
                "created_at": purchase.created_at.isoformat() if purchase.created_at else None,
                "updated_at": purchase.updated_at.isoformat() if purchase.updated_at else None,
                "notes": purchase.notes
            })
        
        return BaseResponse.success_response(
            data=purchase_data,
            message="Purchase history retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving purchase history"
        )


@router.put("/{transfer_id}/status", response_model=BaseResponse[dict])
async def update_purchase_status(
    transfer_id: UUID,
    status_update: PurchaseStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Update purchase status (admin only)"""
    try:
        updated_transfer = await PurchaseService.update_purchase_status(
            db=db,
            transfer_id=str(transfer_id),
            status=status_update.status,
            admin_notes=status_update.admin_notes
        )
        
        if not updated_transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase order not found"
            )
        
        return BaseResponse.success_response(
            data={
                "id": str(updated_transfer.id),
                "transfer_id": updated_transfer.transfer_id,
                "status": updated_transfer.status,
                "updated_at": updated_transfer.updated_at.isoformat()
            },
            message="Purchase status updated successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating purchase status"
        )


@router.get("/admin/all", response_model=BaseResponse[List[dict]])
async def get_all_purchases(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Get all purchases (admin only)"""
    try:
        from sqlalchemy import select
        from app.models.transfer import TransferRequest
        
        query = (
            select(TransferRequest)
            .where(TransferRequest.transfer_type.in_(["crypto_purchase", "bank_purchase"]))
        )
        
        if status_filter:
            query = query.where(TransferRequest.status == status_filter)
        
        query = query.order_by(TransferRequest.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        purchases = result.scalars().all()
        
        purchase_data = []
        for purchase in purchases:
            purchase_data.append({
                "id": str(purchase.id),
                "transfer_id": purchase.transfer_id,
                "user_id": str(purchase.user_id),
                "transfer_type": purchase.transfer_type,
                "amount": float(purchase.amount),
                "fee_amount": float(purchase.fee_amount) if purchase.fee_amount else 0,
                "amount_after_fee": float(purchase.amount_after_fee) if purchase.amount_after_fee else 0,
                "currency": purchase.currency,
                "status": purchase.status,
                "payment_method": purchase.payment_method,
                "recipient_wallet": purchase.recipient_wallet,
                "admin_wallet_address": purchase.admin_wallet_address,
                "network": purchase.network,
                "created_at": purchase.created_at.isoformat() if purchase.created_at else None,
                "updated_at": purchase.updated_at.isoformat() if purchase.updated_at else None,
                "notes": purchase.notes,
                "processing_notes": purchase.processing_notes
            })
        
        return BaseResponse.success_response(
            data=purchase_data,
            message="All purchases retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving purchases"
        )
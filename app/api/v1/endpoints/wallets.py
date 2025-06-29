from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_current_user, get_current_admin, check_admin_permission
from app.db.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import WalletCreate, WalletUpdate, WalletResponse
from app.schemas.base import BaseResponse, MessageResponse

router = APIRouter()


@router.get("/", response_model=BaseResponse[List[WalletResponse]])
async def get_user_wallets(
    currency: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's wallets"""
    
    query = select(Wallet).where(Wallet.user_id == current_user.id)
    
    if currency:
        query = query.where(Wallet.currency == currency.upper())
    
    query = query.order_by(Wallet.created_at.desc())
    
    result = await db.execute(query)
    wallets = result.scalars().all()
    
    return BaseResponse.success_response(data=wallets, message="Wallets retrieved successfully")


@router.post("/", response_model=BaseResponse[WalletResponse])
async def create_wallet(
    wallet_data: WalletCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new wallet for user"""
    
    # Check if wallet address already exists
    result = await db.execute(
        select(Wallet).where(Wallet.address == wallet_data.address)
    )
    existing_wallet = result.scalar_one_or_none()
    
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet address already exists"
        )
    
    # Create new wallet
    wallet = Wallet(
        user_id=current_user.id,
        address=wallet_data.address,
        currency=wallet_data.currency.upper(),
        network=wallet_data.network.upper(),
        label=wallet_data.label
    )
    
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)
    
    return BaseResponse.success_response(data=wallet, message="Wallet operation completed successfully")


@router.get("/{wallet_id}", response_model=BaseResponse[WalletResponse])
async def get_wallet(
    wallet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific wallet"""
    
    result = await db.execute(
        select(Wallet).where(
            and_(
                Wallet.id == wallet_id,
                Wallet.user_id == current_user.id
            )
        )
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    return BaseResponse.success_response(data=wallet, message="Wallet operation completed successfully")


@router.put("/{wallet_id}", response_model=BaseResponse[WalletResponse])
async def update_wallet(
    wallet_id: UUID,
    wallet_update: WalletUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update wallet"""
    
    result = await db.execute(
        select(Wallet).where(
            and_(
                Wallet.id == wallet_id,
                Wallet.user_id == current_user.id
            )
        )
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Update fields (users can only update label and notes)
    if wallet_update.label is not None:
        wallet.label = wallet_update.label
    if wallet_update.notes is not None:
        wallet.notes = wallet_update.notes
    
    await db.commit()
    await db.refresh(wallet)
    
    return BaseResponse.success_response(data=wallet, message="Wallet operation completed successfully")


@router.delete("/{wallet_id}", response_model=MessageResponse)
async def delete_wallet(
    wallet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete wallet"""
    
    result = await db.execute(
        select(Wallet).where(
            and_(
                Wallet.id == wallet_id,
                Wallet.user_id == current_user.id
            )
        )
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Check if wallet has pending transactions
    if wallet.pending_balance > 0 or wallet.frozen_balance > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete wallet with pending or frozen balance"
        )
    
    await db.delete(wallet)
    await db.commit()
    
    return MessageResponse.success_message("Wallet deleted successfully")


# Admin endpoints
@router.get("/admin/all", response_model=BaseResponse[List[WalletResponse]])
async def get_all_wallets(
    skip: int = 0,
    limit: int = 50,
    currency: Optional[str] = None,
    wallet_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_wallets"))
):
    """Get all wallets (admin only)"""
    
    query = select(Wallet)
    
    if currency:
        query = query.where(Wallet.currency == currency.upper())
    
    if wallet_type:
        query = query.where(Wallet.wallet_type == wallet_type)
    
    if is_active is not None:
        query = query.where(Wallet.is_active == is_active)
    
    query = query.order_by(Wallet.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    wallets = result.scalars().all()
    
    return BaseResponse.success_response(data=wallets, message="Wallets retrieved successfully")


@router.put("/admin/{wallet_id}", response_model=BaseResponse[WalletResponse])
async def admin_update_wallet(
    wallet_id: UUID,
    wallet_update: WalletUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_wallets"))
):
    """Update wallet (admin only)"""
    
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Update fields
    for field, value in wallet_update.dict(exclude_unset=True).items():
        setattr(wallet, field, value)
    
    await db.commit()
    await db.refresh(wallet)
    
    return BaseResponse.success_response(data=wallet, message="Wallet operation completed successfully")


@router.get("/admin/balances", response_model=MessageResponse)
async def get_wallet_balances_summary(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_reports"))
):
    """Get wallet balances summary (admin only)"""
    
    from sqlalchemy import func
    
    result = await db.execute(
        select(
            Wallet.currency,
            func.count(Wallet.id).label("total_wallets"),
            func.sum(Wallet.balance).label("total_balance"),
            func.sum(Wallet.pending_balance).label("total_pending"),
            func.sum(Wallet.frozen_balance).label("total_frozen")
        ).group_by(Wallet.currency).where(Wallet.is_active == True)
    )
    
    balances = []
    for row in result:
        balances.append({
            "currency": row.currency,
            "total_wallets": row.total_wallets,
            "total_balance": float(row.total_balance or 0),
            "total_pending": float(row.total_pending or 0),
            "total_frozen": float(row.total_frozen or 0)
        })
    
    return BaseResponse.success_response(data={"balances": balances}, message="Operation completed successfully")
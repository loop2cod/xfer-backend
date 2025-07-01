from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from uuid import UUID

from app.api.deps import get_current_admin, get_super_admin, get_current_user
from app.db.database import get_db
from app.models.admin_wallet import AdminWallet
from app.schemas.admin_wallet import (
    AdminWalletCreate, 
    AdminWalletUpdate, 
    AdminWalletResponse,
    SetPrimaryWallet
)
from app.schemas.base import BaseResponse, MessageResponse

router = APIRouter()


@router.get("/", response_model=BaseResponse[List[AdminWalletResponse]])
async def get_admin_wallets(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """Get all admin wallets"""
    query = select(AdminWallet).order_by(AdminWallet.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    wallets = result.scalars().all()
    
    return BaseResponse.success_response(data=wallets, message="Admin wallets retrieved successfully")


@router.post("/", response_model=BaseResponse[AdminWalletResponse])
async def create_admin_wallet(
    wallet_data: AdminWalletCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_super_admin)
):
    """Create a new admin wallet (super admin only)"""
    # Check if wallet address already exists
    result = await db.execute(select(AdminWallet).where(AdminWallet.address == wallet_data.address))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet with this address already exists"
        )
    
    # If this is the first wallet or is set as primary, ensure it's the only primary
    if wallet_data.is_primary:
        await db.execute(
            update(AdminWallet).where(AdminWallet.is_primary == True).values(is_primary=False)
        )
        await db.commit()
    
    # If this is the first wallet, make it primary by default
    if not wallet_data.is_primary:
        result = await db.execute(select(AdminWallet))
        existing_wallets = result.scalars().all()
        if not existing_wallets:
            wallet_data.is_primary = True
    
    # Create new wallet
    wallet = AdminWallet(**wallet_data.dict())
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)
    
    return BaseResponse.success_response(data=wallet, message="Admin wallet created successfully")


@router.get("/{wallet_id}", response_model=BaseResponse[AdminWalletResponse])
async def get_admin_wallet(
    wallet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """Get admin wallet by ID"""
    result = await db.execute(select(AdminWallet).where(AdminWallet.id == wallet_id))
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin wallet not found"
        )
    
    return BaseResponse.success_response(data=wallet, message="Admin wallet retrieved successfully")


@router.put("/{wallet_id}", response_model=BaseResponse[AdminWalletResponse])
async def update_admin_wallet(
    wallet_id: UUID,
    wallet_update: AdminWalletUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_super_admin)
):
    """Update admin wallet (super admin only)"""
    result = await db.execute(select(AdminWallet).where(AdminWallet.id == wallet_id))
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin wallet not found"
        )
    
    # If setting this wallet as primary, unset any other primary wallets
    if wallet_update.is_primary is True and not wallet.is_primary:
        await db.execute(
            update(AdminWallet).where(AdminWallet.is_primary == True).values(is_primary=False)
        )
        await db.commit()
    
    # Don't allow unsetting the primary wallet without setting another one
    if wallet_update.is_primary is False and wallet.is_primary:
        # Check if there's another wallet that can be primary
        result = await db.execute(
            select(AdminWallet).where(AdminWallet.id != wallet_id)
        )
        other_wallets = result.scalars().all()
        
        if not other_wallets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot unset primary wallet when it's the only wallet"
            )
    
    # Update wallet fields
    update_data = wallet_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(wallet, field, value)
    
    await db.commit()
    await db.refresh(wallet)
    
    return BaseResponse.success_response(data=wallet, message="Admin wallet updated successfully")


@router.delete("/{wallet_id}", response_model=MessageResponse)
async def delete_admin_wallet(
    wallet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_super_admin)
):
    """Delete admin wallet (super admin only)"""
    result = await db.execute(select(AdminWallet).where(AdminWallet.id == wallet_id))
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin wallet not found"
        )
    
    # Don't allow deleting the primary wallet if it's the only wallet
    if wallet.is_primary:
        result = await db.execute(
            select(AdminWallet).where(AdminWallet.id != wallet_id)
        )
        other_wallets = result.scalars().all()
        
        if not other_wallets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only primary wallet"
            )
        
        # Set another wallet as primary
        another_wallet = other_wallets[0]
        another_wallet.is_primary = True
        await db.commit()
    
    # Delete the wallet
    await db.delete(wallet)
    await db.commit()
    
    return MessageResponse.success_message("Admin wallet deleted successfully")


@router.post("/set-primary", response_model=MessageResponse)
async def set_primary_wallet(
    data: SetPrimaryWallet,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_super_admin)
):
    """Set a wallet as primary (super admin only)"""
    # Check if wallet exists
    result = await db.execute(select(AdminWallet).where(AdminWallet.id == data.wallet_id))
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin wallet not found"
        )
    
    # Unset current primary wallet
    await db.execute(
        update(AdminWallet).where(AdminWallet.is_primary == True).values(is_primary=False)
    )
    
    # Set new primary wallet
    wallet.is_primary = True
    await db.commit()
    
    return MessageResponse.success_message(f"Wallet '{wallet.name}' set as primary successfully")


@router.get("/primary", response_model=BaseResponse[AdminWalletResponse])
async def get_primary_wallet(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get the primary wallet for client payments"""
    result = await db.execute(
        select(AdminWallet).where(
            AdminWallet.is_primary == True,
            AdminWallet.is_active == True
        )
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No primary wallet available"
        )
    
    return BaseResponse.success_response(data=wallet, message="Primary wallet retrieved successfully")


@router.get("/active", response_model=BaseResponse[List[AdminWalletResponse]])
async def get_active_wallets(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all active wallets for client use"""
    query = select(AdminWallet).where(AdminWallet.is_active == True).order_by(AdminWallet.is_primary.desc())
    result = await db.execute(query)
    wallets = result.scalars().all()
    
    return BaseResponse.success_response(data=wallets, message="Active wallets retrieved successfully")


@router.get("/public/primary", response_model=BaseResponse[AdminWalletResponse])
async def get_public_primary_wallet(
    db: AsyncSession = Depends(get_db)
):
    """Get the primary wallet for public use (no authentication required)"""
    result = await db.execute(
        select(AdminWallet).where(
            AdminWallet.is_primary == True,
            AdminWallet.is_active == True
        )
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No primary wallet available"
        )
    
    return BaseResponse.success_response(data=wallet, message="Primary wallet retrieved successfully")
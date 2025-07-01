from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from uuid import UUID

from app.api.deps import get_current_admin, get_super_admin, get_current_user
from app.db.database import get_db
from app.models.admin_bank_account import AdminBankAccount
from app.schemas.admin_bank_account import (
    AdminBankAccountCreate, 
    AdminBankAccountUpdate, 
    AdminBankAccountResponse,
    SetPrimaryBankAccount
)
from app.schemas.base import BaseResponse, MessageResponse

router = APIRouter()


@router.get("/", response_model=BaseResponse[List[AdminBankAccountResponse]])
async def get_admin_bank_accounts(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """Get all admin bank accounts"""
    query = select(AdminBankAccount).order_by(AdminBankAccount.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    return BaseResponse.success_response(data=accounts, message="Admin bank accounts retrieved successfully")


@router.post("/", response_model=BaseResponse[AdminBankAccountResponse])
async def create_admin_bank_account(
    account_data: AdminBankAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_super_admin)
):
    """Create a new admin bank account (super admin only)"""
    # Check if account number already exists
    result = await db.execute(select(AdminBankAccount).where(AdminBankAccount.account_number == account_data.account_number))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank account with this account number already exists"
        )
    
    # If this is set as primary, ensure it's the only primary
    if account_data.is_primary:
        await db.execute(
            update(AdminBankAccount).where(AdminBankAccount.is_primary == True).values(is_primary=False)
        )
        await db.commit()
    
    # If this is the first account, make it primary by default
    if not account_data.is_primary:
        result = await db.execute(select(AdminBankAccount))
        existing_accounts = result.scalars().all()
        if not existing_accounts:
            account_data.is_primary = True
    
    # Create new bank account
    account = AdminBankAccount(**account_data.dict())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    return BaseResponse.success_response(data=account, message="Admin bank account created successfully")


@router.get("/{account_id}", response_model=BaseResponse[AdminBankAccountResponse])
async def get_admin_bank_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """Get admin bank account by ID"""
    result = await db.execute(select(AdminBankAccount).where(AdminBankAccount.id == account_id))
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin bank account not found"
        )
    
    return BaseResponse.success_response(data=account, message="Admin bank account retrieved successfully")


@router.put("/{account_id}", response_model=BaseResponse[AdminBankAccountResponse])
async def update_admin_bank_account(
    account_id: UUID,
    account_update: AdminBankAccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_super_admin)
):
    """Update admin bank account (super admin only)"""
    result = await db.execute(select(AdminBankAccount).where(AdminBankAccount.id == account_id))
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin bank account not found"
        )
    
    # If setting this account as primary, unset any other primary accounts
    if account_update.is_primary is True and not account.is_primary:
        await db.execute(
            update(AdminBankAccount).where(AdminBankAccount.is_primary == True).values(is_primary=False)
        )
        await db.commit()
    
    # Don't allow unsetting the primary account without setting another one
    if account_update.is_primary is False and account.is_primary:
        # Check if there's another account that can be primary
        result = await db.execute(
            select(AdminBankAccount).where(AdminBankAccount.id != account_id)
        )
        other_accounts = result.scalars().all()
        
        if not other_accounts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot unset primary bank account when it's the only account"
            )
    
    # Update account fields
    update_data = account_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    
    await db.commit()
    await db.refresh(account)
    
    return BaseResponse.success_response(data=account, message="Admin bank account updated successfully")


@router.delete("/{account_id}", response_model=MessageResponse)
async def delete_admin_bank_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_super_admin)
):
    """Delete admin bank account (super admin only)"""
    result = await db.execute(select(AdminBankAccount).where(AdminBankAccount.id == account_id))
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin bank account not found"
        )
    
    # Don't allow deleting the primary account if it's the only account
    if account.is_primary:
        result = await db.execute(
            select(AdminBankAccount).where(AdminBankAccount.id != account_id)
        )
        other_accounts = result.scalars().all()
        
        if not other_accounts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only primary bank account"
            )
        
        # Set another account as primary
        another_account = other_accounts[0]
        another_account.is_primary = True
        await db.commit()
    
    # Delete the account
    await db.delete(account)
    await db.commit()
    
    return MessageResponse.success_message("Admin bank account deleted successfully")


@router.post("/set-primary", response_model=MessageResponse)
async def set_primary_bank_account(
    data: SetPrimaryBankAccount,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_super_admin)
):
    """Set a bank account as primary (super admin only)"""
    # Check if account exists
    result = await db.execute(select(AdminBankAccount).where(AdminBankAccount.id == data.account_id))
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin bank account not found"
        )
    
    # Unset current primary account
    await db.execute(
        update(AdminBankAccount).where(AdminBankAccount.is_primary == True).values(is_primary=False)
    )
    
    # Set new primary account
    account.is_primary = True
    await db.commit()
    
    return MessageResponse.success_message(f"Bank account '{account.name}' set as primary successfully")


@router.get("/primary", response_model=BaseResponse[AdminBankAccountResponse])
async def get_primary_bank_account(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get the primary bank account for client use"""
    result = await db.execute(
        select(AdminBankAccount).where(
            AdminBankAccount.is_primary == True,
            AdminBankAccount.is_active == True
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No primary bank account available"
        )
    
    return BaseResponse.success_response(data=account, message="Primary bank account retrieved successfully")


@router.get("/active", response_model=BaseResponse[List[AdminBankAccountResponse]])
async def get_active_bank_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all active bank accounts for client use"""
    query = select(AdminBankAccount).where(AdminBankAccount.is_active == True).order_by(AdminBankAccount.is_primary.desc())
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    return BaseResponse.success_response(data=accounts, message="Active bank accounts retrieved successfully")
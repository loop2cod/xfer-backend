from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.api.deps import get_current_user, get_current_admin, check_admin_permission
from app.db.database import get_db
from app.models.user import User
from app.models.transfer import TransferRequest
from app.schemas.user import UserResponse, UserUpdate, UserProfile
from app.schemas.base import BaseResponse, MessageResponse

router = APIRouter()


@router.get("/me", response_model=BaseResponse[UserProfile])
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user profile with statistics"""
    
    # Get transfer statistics
    stats_result = await db.execute(
        select(
            func.count(TransferRequest.id).label("total_transfers"),
            func.coalesce(func.sum(TransferRequest.amount), 0).label("total_volume"),
            func.count().filter(TransferRequest.status == "pending").label("pending_transfers")
        ).where(TransferRequest.user_id == current_user.id)
    )
    stats = stats_result.first()
    
    user_profile = UserProfile(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        kyc_status=current_user.kyc_status,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        total_transfers=stats.total_transfers or 0,
        total_volume=float(stats.total_volume or 0),
        pending_transfers=stats.pending_transfers or 0
    )
    
    return BaseResponse.success_response(data=user_profile, message="User profile retrieved successfully")


@router.put("/me", response_model=BaseResponse[UserResponse])
async def update_current_user(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user profile"""
    
    # Update fields
    for field, value in user_update.dict(exclude_unset=True).items():
        if field != "is_active":  # Users can't change their active status
            setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return BaseResponse.success_response(data=current_user, message="User profile updated successfully")


# Admin endpoints
@router.get("/admin/all", response_model=BaseResponse[List[UserResponse]])
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    search: str = None,
    kyc_status: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_users"))
):
    """Get all users (admin only)"""
    
    query = select(User)
    
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") |
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%")
        )
    
    if kyc_status:
        query = query.where(User.kyc_status == kyc_status)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return BaseResponse.success_response(data=users, message="Users retrieved successfully")


@router.get("/admin/{user_id}", response_model=BaseResponse[UserProfile])
async def get_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_users"))
):
    """Get user by ID with profile (admin only)"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get transfer statistics
    stats_result = await db.execute(
        select(
            func.count(TransferRequest.id).label("total_transfers"),
            func.coalesce(func.sum(TransferRequest.amount), 0).label("total_volume"),
            func.count().filter(TransferRequest.status == "pending").label("pending_transfers")
        ).where(TransferRequest.user_id == user.id)
    )
    stats = stats_result.first()
    
    user_profile = UserProfile(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        kyc_status=user.kyc_status,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        total_transfers=stats.total_transfers or 0,
        total_volume=float(stats.total_volume or 0),
        pending_transfers=stats.pending_transfers or 0
    )
    
    return BaseResponse.success_response(data=user_profile, message="User retrieved successfully")


@router.put("/admin/{user_id}", response_model=BaseResponse[UserResponse])
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_users"))
):
    """Update user (admin only)"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return BaseResponse.success_response(data=user, message="User operation completed successfully")


@router.put("/admin/{user_id}/kyc/{status}", response_model=MessageResponse)
async def update_user_kyc_status(
    user_id: str,
    status: str,
    notes: str = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_approve_kyc"))
):
    """Update user KYC status (admin only)"""
    
    if status not in ["pending", "approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid KYC status"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.kyc_status = status
    if status == "approved":
        user.is_verified = True
    
    await db.commit()
    
    return MessageResponse.success_message(f"KYC status updated to {status}")
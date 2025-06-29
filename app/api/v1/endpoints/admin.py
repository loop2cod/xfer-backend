from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.api.deps import get_current_admin, get_super_admin
from app.db.database import get_db
from app.models.admin import Admin
from app.models.user import User
from app.models.transfer import TransferRequest
from app.models.wallet import Wallet
from app.schemas.admin import AdminCreate, AdminUpdate, AdminResponse
from app.schemas.base import BaseResponse, MessageResponse
from app.core.security import get_password_hash, generate_api_key

router = APIRouter()


@router.get("/me", response_model=BaseResponse[AdminResponse])
async def get_current_admin_profile(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get current admin profile"""
    return BaseResponse.success_response(data=current_admin, message="Admin profile retrieved successfully")


@router.put("/me", response_model=BaseResponse[AdminResponse])
async def update_current_admin(
    admin_update: AdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Update current admin profile"""
    
    # Update fields (can't change role or super admin status)
    for field, value in admin_update.dict(exclude_unset=True).items():
        if field not in ["role", "is_super_admin"]:
            setattr(current_admin, field, value)
    
    await db.commit()
    await db.refresh(current_admin)
    
    return BaseResponse.success_response(data=current_admin, message="Admin profile updated successfully")


@router.post("/api-key", response_model=BaseResponse[dict])
async def generate_admin_api_key(
    expires_days: int = 90,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Generate new API key for admin"""
    
    api_key = generate_api_key()
    current_admin.api_key = api_key
    current_admin.api_key_expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    await db.commit()
    
    return BaseResponse.success_response(data={
        "api_key": api_key,
        "expires_at": current_admin.api_key_expires_at,
        "message": "API key generated successfully"
    }, message="Operation completed successfully")


@router.delete("/api-key", response_model=MessageResponse)
async def revoke_admin_api_key(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Revoke current admin API key"""
    
    current_admin.api_key = None
    current_admin.api_key_expires_at = None
    
    await db.commit()
    
    return MessageResponse.success_message("API key revoked successfully")


# Super admin endpoints
@router.get("/all", response_model=BaseResponse[List[AdminResponse]])
async def get_all_admins(
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_super_admin)
):
    """Get all admins (super admin only)"""
    
    query = select(Admin)
    
    if role:
        query = query.where(Admin.role == role)
    
    if is_active is not None:
        query = query.where(Admin.is_active == is_active)
    
    query = query.order_by(Admin.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    admins = result.scalars().all()
    
    return BaseResponse.success_response(data=admins, message="Admins retrieved successfully")


@router.post("/", response_model=BaseResponse[AdminResponse])
async def create_admin(
    admin_data: AdminCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_super_admin)
):
    """Create new admin (super admin only)"""
    
    # Check if admin already exists
    result = await db.execute(select(Admin).where(Admin.email == admin_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this email already exists"
        )
    
    # Create new admin
    hashed_password = get_password_hash(admin_data.password)
    admin = Admin(
        email=admin_data.email,
        password_hash=hashed_password,
        first_name=admin_data.first_name,
        last_name=admin_data.last_name,
        role=admin_data.role,
        permissions=admin_data.permissions,
        created_by=current_admin.id
    )
    
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    
    return BaseResponse.success_response(data=admin, message="Admin operation completed successfully")


@router.get("/{admin_id}", response_model=BaseResponse[AdminResponse])
async def get_admin(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_super_admin)
):
    """Get admin by ID (super admin only)"""
    
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    return BaseResponse.success_response(data=admin, message="Admin operation completed successfully")


@router.put("/{admin_id}", response_model=BaseResponse[AdminResponse])
async def update_admin(
    admin_id: UUID,
    admin_update: AdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_super_admin)
):
    """Update admin (super admin only)"""
    
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    # Prevent changing super admin status of self
    if admin.id == current_admin.id and "is_super_admin" in admin_update.dict(exclude_unset=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own super admin status"
        )
    
    # Update fields
    for field, value in admin_update.dict(exclude_unset=True).items():
        setattr(admin, field, value)
    
    await db.commit()
    await db.refresh(admin)
    
    return BaseResponse.success_response(data=admin, message="Admin operation completed successfully")


@router.delete("/{admin_id}", response_model=MessageResponse)
async def delete_admin(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_super_admin)
):
    """Delete admin (super admin only)"""
    
    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    await db.delete(admin)
    await db.commit()
    
    return MessageResponse.success_message("Admin deleted successfully")


@router.get("/dashboard/stats", response_model=BaseResponse[dict])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get dashboard statistics"""
    
    # Get user statistics
    users_result = await db.execute(
        select(
            func.count(User.id).label("total_users"),
            func.count().filter(User.is_active == True).label("active_users"),
            func.count().filter(User.kyc_status == "pending").label("pending_kyc")
        )
    )
    users_stats = users_result.first()
    
    # Get transfer statistics
    transfers_result = await db.execute(
        select(
            func.count(TransferRequest.id).label("total_transfers"),
            func.count().filter(TransferRequest.status == "pending").label("pending_transfers"),
            func.count().filter(TransferRequest.status == "completed").label("completed_transfers"),
            func.sum(TransferRequest.amount).filter(TransferRequest.status == "completed").label("total_volume")
        )
    )
    transfers_stats = transfers_result.first()
    
    # Get wallet statistics
    wallets_result = await db.execute(
        select(
            func.count(Wallet.id).label("total_wallets"),
            func.sum(Wallet.balance).label("total_balance")
        ).where(Wallet.is_active == True)
    )
    wallets_stats = wallets_result.first()
    
    # Get recent activity (last 24 hours)
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_activity = await db.execute(
        select(
            func.count(TransferRequest.id).label("recent_transfers"),
            func.count(User.id).label("new_users")
        ).select_from(
            TransferRequest.outerjoin(User)
        ).where(
            and_(
                TransferRequest.created_at >= last_24h,
                User.created_at >= last_24h
            )
        )
    )
    activity_stats = recent_activity.first()
    
    dashboard_data = {
        "users": {
            "total": users_stats.total_users or 0,
            "active": users_stats.active_users or 0,
            "pending_kyc": users_stats.pending_kyc or 0
        },
        "transfers": {
            "total": transfers_stats.total_transfers or 0,
            "pending": transfers_stats.pending_transfers or 0,
            "completed": transfers_stats.completed_transfers or 0,
            "total_volume": float(transfers_stats.total_volume or 0)
        },
        "wallets": {
            "total": wallets_stats.total_wallets or 0,
            "total_balance": float(wallets_stats.total_balance or 0)
        },
        "recent_activity": {
            "transfers_24h": activity_stats.recent_transfers or 0,
            "new_users_24h": activity_stats.new_users or 0
        }
    }
    
    return BaseResponse.success_response(data=dashboard_data, message="Dashboard statistics retrieved successfully")
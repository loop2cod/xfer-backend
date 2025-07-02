from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from typing import List

from app.api.deps import get_current_user, get_current_admin, check_admin_permission
from app.db.database import get_db
from app.models.user import User
from app.models.transfer import TransferRequest
from app.schemas.user import UserResponse, UserUpdate, UserProfile, UserAdminResponse
from app.schemas.base import BaseResponse, MessageResponse
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter()


class DashboardStats(BaseModel):
    total_sent: float = 0.0
    pending_requests: int = 0
    completed_transfers: int = 0
    failed_transfers: int = 0
    total_fees_paid: float = 0.0
    

class DashboardData(BaseModel):
    customer_id: str
    full_name: str
    email: str
    kyc_status: str
    account_balance: float = 0.0  # Future feature - wallet balance
    is_verified: bool
    member_since: datetime
    last_activity: datetime
    stats: DashboardStats
    account_limits: dict = {
        "daily_limit": 10000.0,
        "monthly_limit": 50000.0,
        "used_daily": 0.0,
        "used_monthly": 0.0
    }
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v.tzinfo else v.replace(tzinfo=timezone.utc).isoformat()
        }


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
            func.coalesce(func.sum(case((TransferRequest.status == 'completed', TransferRequest.amount), else_=0)), 0).label("total_volume"),
            func.sum(case((TransferRequest.status == 'pending', 1), else_=0)).label("pending_transfers")
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


@router.get("/dashboard", response_model=BaseResponse[DashboardData])
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard data for current user"""
    
    # Get comprehensive transfer statistics
    stats_query = select(
        func.count(TransferRequest.id).label("total_transfers"),
        func.coalesce(
            func.sum(
                case(
                    (and_(TransferRequest.status == "completed", TransferRequest.type_ == "crypto-to-fiat"), TransferRequest.amount),
                    else_=0
                )
            ), 0
        ).label("total_sent"),
        func.count().filter(TransferRequest.status == "pending").label("pending_requests"),
        func.count().filter(TransferRequest.status == "completed").label("completed_transfers"),
        func.count().filter(TransferRequest.status == "failed").label("failed_transfers"),
        func.coalesce(
            func.sum(
                case(
                    (TransferRequest.status == "completed", TransferRequest.fee),
                    else_=0
                )
            ), 0
        ).label("total_fees_paid")
    ).where(TransferRequest.user_id == current_user.id)

    stats_result = await db.execute(stats_query)
    stats = stats_result.first()

    # Calculate monthly usage (placeholder for future implementation)
    from datetime import datetime, timedelta
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    monthly_usage_query = select(
        func.coalesce(
            func.sum(
                case(
                    (and_(TransferRequest.status == "completed", TransferRequest.created_at >= start_of_month), TransferRequest.amount),
                    else_=0
                )
            ), 0
        ).label("monthly_usage")
    ).where(TransferRequest.user_id == current_user.id)
    
    monthly_result = await db.execute(monthly_usage_query)
    monthly_usage = monthly_result.scalar() or 0

    # Create dashboard stats
    dashboard_stats = DashboardStats(
        total_sent=float(stats.total_sent or 0),
        pending_requests=stats.pending_requests or 0,
        completed_transfers=stats.completed_transfers or 0,
        failed_transfers=stats.failed_transfers or 0,
        total_fees_paid=float(stats.total_fees_paid or 0)
    )

    # Build full name
    full_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
    if not full_name:
        full_name = current_user.email.split('@')[0].title()

    # Create dashboard data
    dashboard_data = DashboardData(
        customer_id=current_user.customer_id,
        full_name=full_name,
        email=current_user.email,
        kyc_status=current_user.kyc_status,
        account_balance=0.0,  # Future: integrate with wallet balance
        is_verified=current_user.is_verified,
        member_since=current_user.created_at,
        last_activity=current_user.last_login or current_user.updated_at,
        stats=dashboard_stats,
        account_limits={
            "daily_limit": 10000.0,
            "monthly_limit": 50000.0,
            "used_daily": 0.0,  # Future: calculate daily usage
            "used_monthly": float(monthly_usage)
        }
    )

    return BaseResponse.success_response(data=dashboard_data, message="Dashboard data retrieved successfully")


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
@router.get("/admin/all", response_model=BaseResponse[dict])
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    search: str = None,
    kyc_status: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_users"))
):
    """Get all users with pagination (admin only)"""

    base_query = select(User)
    count_query = select(func.count(User.id))

    # Apply filters
    filters = []

    if search:
        search_filter = (
            User.email.ilike(f"%{search}%") |
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%")
        )
        filters.append(search_filter)

    if kyc_status:
        filters.append(User.kyc_status == kyc_status)

    if is_active is not None:
        filters.append(User.is_active == is_active)

    if filters:
        base_query = base_query.where(*filters)
        count_query = count_query.where(*filters)

    # Get total count
    total_result = await db.execute(count_query)
    total_count = total_result.scalar()

    # Apply pagination and ordering
    query = base_query.order_by(User.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    users = result.scalars().all()

    # Calculate transfer statistics for each user
    user_responses = []
    for user in users:
        # Get transfer statistics for this user
        transfer_stats_query = select(
            func.count(TransferRequest.id).label('total_requests'),
            func.coalesce(func.sum(case((TransferRequest.status == 'completed', TransferRequest.amount), else_=0)), 0).label('total_volume'),
            func.sum(case((TransferRequest.status == 'completed', 1), else_=0)).label('completed_requests'),
            func.sum(case((TransferRequest.status == 'pending', 1), else_=0)).label('pending_requests')
        ).where(TransferRequest.user_id == user.id)

        stats_result = await db.execute(transfer_stats_query)
        stats = stats_result.first()

        # Create user response with statistics
        user_data = UserAdminResponse.model_validate(user)
        user_data.total_requests = stats.total_requests or 0
        user_data.total_volume = float(stats.total_volume or 0)
        user_data.completed_requests = stats.completed_requests or 0
        user_data.pending_requests = stats.pending_requests or 0

        user_responses.append(user_data)

    # Calculate pagination info
    total_pages = (total_count + limit - 1) // limit
    current_page = (skip // limit) + 1
    has_next = skip + limit < total_count
    has_prev = skip > 0

    return BaseResponse.success_response(
        data={
            "users": user_responses,
            "total_count": total_count,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        message="Users retrieved successfully"
    )


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
            func.coalesce(func.sum(case((TransferRequest.status == 'completed', TransferRequest.amount), else_=0)), 0).label("total_volume"),
            func.sum(case((TransferRequest.status == 'pending', 1), else_=0)).label("pending_transfers")
        ).where(TransferRequest.user_id == user.id)
    )
    stats = stats_result.first()

    # Create user profile using model_validate
    user_profile = UserProfile.model_validate(user)
    user_profile.total_transfers = stats.total_transfers or 0
    user_profile.total_volume = float(stats.total_volume or 0)
    user_profile.pending_transfers = stats.pending_transfers or 0
    
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


@router.put("/admin/{user_id}/status", response_model=BaseResponse[UserResponse])
async def update_user_status(
    user_id: str,
    status_data: dict,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_users"))
):
    """Update user status (admin only)"""

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update status
    if "is_active" in status_data:
        user.is_active = status_data["is_active"]

    await db.commit()
    await db.refresh(user)

    return BaseResponse.success_response(data=user, message="User status updated successfully")


@router.put("/admin/{user_id}/kyc", response_model=BaseResponse[UserResponse])
async def update_user_kyc(
    user_id: str,
    kyc_data: dict,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_manage_users"))
):
    """Update user KYC status (admin only)"""

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update KYC status
    if "kyc_status" in kyc_data:
        user.kyc_status = kyc_data["kyc_status"]

    # Add notes if provided
    if "notes" in kyc_data:
        # You might want to store this in a separate notes table
        pass

    await db.commit()
    await db.refresh(user)

    return BaseResponse.success_response(data=user, message="User KYC status updated successfully")


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
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.user_activity import UserActivityResponse, UserActivityListResponse
from app.schemas.base import BaseResponse
from app.services.user_activity import UserActivityService

router = APIRouter()


@router.get("/", response_model=BaseResponse[UserActivityListResponse])
async def get_user_activities(
    skip: int = 0,
    limit: int = 20,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's activities with filtering and pagination"""
    
    # Validate pagination parameters
    if limit > 100:
        limit = 100
    if skip < 0:
        skip = 0
    
    activities, total_count = await UserActivityService.get_user_activities(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        action_filter=action,
        resource_type_filter=resource_type
    )
    
    # Calculate pagination info
    total_pages = (total_count + limit - 1) // limit
    current_page = (skip // limit) + 1
    has_next = skip + limit < total_count
    has_prev = skip > 0
    
    response_data = UserActivityListResponse(
        activities=[UserActivityResponse.model_validate(activity) for activity in activities],
        total=total_count,
        page=current_page,
        page_size=limit,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
    
    return BaseResponse.success_response(
        data=response_data,
        message="User activities retrieved successfully"
    )


@router.get("/stats", response_model=BaseResponse[dict])
async def get_user_activity_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's activity statistics"""
    
    if days > 365:
        days = 365
    if days < 1:
        days = 1
    
    stats = await UserActivityService.get_activity_stats(
        db=db,
        user_id=current_user.id,
        days=days
    )
    
    return BaseResponse.success_response(
        data=stats,
        message="User activity statistics retrieved successfully"
    )
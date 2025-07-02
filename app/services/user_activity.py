from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from app.models.user_activity import UserActivity



class UserActivityService:
    """Service for managing user activity logging"""
    
    @staticmethod
    async def log_activity(
        db: AsyncSession,
        user_id: UUID,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserActivity:
        """Log a user activity"""
        
        activity = UserActivity(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(activity)
        await db.commit()
        await db.refresh(activity)

        # Ensure timezone information is properly set for SQLite compatibility
        if activity.created_at and activity.created_at.tzinfo is None:
            activity.created_at = activity.created_at.replace(tzinfo=timezone.utc)

        return activity
    
    @staticmethod
    async def get_user_activities(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        action_filter: Optional[str] = None,
        resource_type_filter: Optional[str] = None
    ) -> tuple[list[UserActivity], int]:
        """Get user activities with pagination and filtering"""
        
        # Base query
        query = select(UserActivity).where(UserActivity.user_id == user_id)
        count_query = select(func.count(UserActivity.id)).where(UserActivity.user_id == user_id)
        
        # Apply filters
        filters = []
        
        if action_filter:
            filters.append(UserActivity.action.ilike(f"%{action_filter}%"))
        
        if resource_type_filter:
            filters.append(UserActivity.resource_type == resource_type_filter)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(UserActivity.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        activities = result.scalars().all()

        # Ensure timezone information is properly set for SQLite compatibility
        for activity in activities:
            if activity.created_at and activity.created_at.tzinfo is None:
                activity.created_at = activity.created_at.replace(tzinfo=timezone.utc)

        return activities, total_count
    
    @staticmethod
    async def get_activity_stats(
        db: AsyncSession,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get user activity statistics"""
        
        from datetime import timedelta
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get total activities in period
        total_result = await db.execute(
            select(func.count(UserActivity.id)).where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.created_at >= start_date
                )
            )
        )
        total_activities = total_result.scalar()
        
        # Get activities by action
        action_result = await db.execute(
            select(
                UserActivity.action,
                func.count(UserActivity.id).label('count')
            ).where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.created_at >= start_date
                )
            ).group_by(UserActivity.action).order_by(func.count(UserActivity.id).desc())
        )
        actions_stats = [{"action": row[0], "count": row[1]} for row in action_result.fetchall()]
        
        # Get recent login activity
        recent_login_result = await db.execute(
            select(UserActivity.created_at).where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.action == "login",
                    UserActivity.created_at >= start_date
                )
            ).order_by(UserActivity.created_at.desc()).limit(1)
        )
        last_login = recent_login_result.scalar()

        # Ensure timezone information is properly set for SQLite compatibility
        if last_login and last_login.tzinfo is None:
            last_login = last_login.replace(tzinfo=timezone.utc)

        return {
            "period_days": days,
            "total_activities": total_activities,
            "actions_breakdown": actions_stats,
            "last_login": last_login.isoformat() if last_login else None
        }


# Activity action constants
class ActivityActions:
    LOGIN = "login"
    LOGOUT = "logout"
    PROFILE_UPDATE = "profile_update"
    PASSWORD_CHANGE = "password_change"
    EMAIL_VERIFICATION = "email_verification"
    TRANSFER_CREATE = "transfer_create"
    TRANSFER_UPDATE = "transfer_update"
    TRANSFER_CANCEL = "transfer_cancel"
    WALLET_CREATE = "wallet_create"
    WALLET_UPDATE = "wallet_update"
    KYC_SUBMIT = "kyc_submit"
    KYC_UPDATE = "kyc_update"


# Resource type constants
class ResourceTypes:
    USER = "user"
    TRANSFER = "transfer"
    WALLET = "wallet"
    KYC = "kyc"
    AUTH = "auth"
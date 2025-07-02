from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.models.audit_log import AuditLog


class AuditLogService:
    """Service for managing admin audit logging"""
    
    @staticmethod
    async def log_admin_activity(
        db: AsyncSession,
        admin_id: UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log an admin activity"""
        
        audit_log = AuditLog(
            admin_id=admin_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        
        return audit_log
    
    @staticmethod
    async def get_admin_audit_logs(
        db: AsyncSession,
        admin_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 20,
        action_filter: Optional[str] = None,
        resource_type_filter: Optional[str] = None
    ) -> tuple[list[AuditLog], int]:
        """Get admin audit logs with pagination and filtering"""
        
        # Base query
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))
        
        # Apply filters
        filters = []
        
        if admin_id:
            filters.append(AuditLog.admin_id == admin_id)
        
        if action_filter:
            filters.append(AuditLog.action.ilike(f"%{action_filter}%"))
        
        if resource_type_filter:
            filters.append(AuditLog.resource_type == resource_type_filter)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        audit_logs = result.scalars().all()
        
        return audit_logs, total_count


# Audit action constants for admins
class AdminAuditActions:
    LOGIN = "admin_login"
    LOGOUT = "admin_logout"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    APPROVE_TRANSFER = "approve_transfer"
    REJECT_TRANSFER = "reject_transfer"
    UPDATE_TRANSFER = "update_transfer"
    CREATE_ADMIN = "create_admin"
    UPDATE_ADMIN = "update_admin"
    DELETE_ADMIN = "delete_admin"
    UPDATE_SETTINGS = "update_settings"
    VIEW_REPORTS = "view_reports"
    EXPORT_DATA = "export_data"


# Resource type constants for admin actions
class AdminResourceTypes:
    AUTH = "admin_auth"
    USER = "user"
    TRANSFER = "transfer"
    ADMIN = "admin"
    SETTINGS = "settings"
    REPORTS = "reports"
    WALLET = "wallet"
    BANK_ACCOUNT = "bank_account"
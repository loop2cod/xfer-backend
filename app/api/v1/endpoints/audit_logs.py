from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.api.deps import get_current_admin, check_admin_permission
from app.db.database import get_db
from app.models.audit_log import AuditLog
from app.models.admin import Admin
from app.schemas.audit_log import AuditLogResponse, AuditLogCreate
from app.schemas.base import BaseResponse
from app.services.audit_log import AuditLogService

router = APIRouter()


@router.get("/", response_model=BaseResponse[dict])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    admin_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_audit_logs"))
):
    """Get audit logs with filtering"""
    
    # Base query with admin join
    query = select(AuditLog).join(Admin, AuditLog.admin_id == Admin.id)
    count_query = select(func.count(AuditLog.id)).join(Admin, AuditLog.admin_id == Admin.id)
    
    # Apply filters
    filters = []
    
    if admin_id:
        filters.append(AuditLog.admin_id == admin_id)
    
    if action:
        filters.append(AuditLog.action.ilike(f"%{action}%"))
    
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            filters.append(AuditLog.created_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format."
            )
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            filters.append(AuditLog.created_at <= end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format."
            )
    
    if search:
        filters.append(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.resource_type.ilike(f"%{search}%"),
                AuditLog.details.astext.ilike(f"%{search}%"),
                Admin.first_name.ilike(f"%{search}%"),
                Admin.last_name.ilike(f"%{search}%"),
                Admin.email.ilike(f"%{search}%")
            )
        )
    
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
    
    # Convert to response format with admin info
    logs = []
    for log in audit_logs:
        admin_result = await db.execute(select(Admin).where(Admin.id == log.admin_id))
        admin = admin_result.scalar_one_or_none()

        # Generate admin name for display
        admin_name = None
        if admin:
            admin_name = f"{admin.first_name} {admin.last_name}".strip() or admin.email

        # Generate enhanced fields using service methods
        log_type = AuditLogService.generate_log_type(log.resource_type)
        activity_description = AuditLogService.generate_activity_description(
            log.action, log.resource_type, log.details
        )
        reference_link = AuditLogService.generate_reference_link(
            log.resource_type, log.resource_id
        )

        log_dict = {
            "id": str(log.id),
            "admin_id": str(log.admin_id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": (log.created_at.astimezone(timezone.utc) if log.created_at.tzinfo else log.created_at.replace(tzinfo=timezone.utc)).strftime('%Y-%m-%dT%H:%M:%S.%f+00:00'),
            "admin_name": admin_name,
            # New enhanced fields
            "type": log_type,
            "activity_description": activity_description,
            "created_by": admin_name,
            "reference_link": reference_link,
            "admin": {
                "id": str(admin.id),
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "email": admin.email
            } if admin else None
        }
        logs.append(log_dict)
    
    # Calculate pagination info
    total_pages = (total_count + limit - 1) // limit
    current_page = (skip // limit) + 1
    has_next = skip + limit < total_count
    has_prev = skip > 0
    
    return BaseResponse.success_response(
        data={
            "logs": logs,
            "total": total_count,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        message="Audit logs retrieved successfully"
    )


@router.get("/actions", response_model=BaseResponse[List[str]])
async def get_audit_actions(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_audit_logs"))
):
    """Get all unique audit actions"""
    result = await db.execute(
        select(AuditLog.action).distinct().order_by(AuditLog.action)
    )
    actions = [row[0] for row in result.fetchall()]
    
    return BaseResponse.success_response(data=actions, message="Audit actions retrieved successfully")


@router.get("/resource-types", response_model=BaseResponse[List[str]])
async def get_audit_resource_types(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_audit_logs"))
):
    """Get all unique resource types"""
    result = await db.execute(
        select(AuditLog.resource_type).distinct().order_by(AuditLog.resource_type)
    )
    resource_types = [row[0] for row in result.fetchall()]
    
    return BaseResponse.success_response(data=resource_types, message="Resource types retrieved successfully")


@router.get("/stats", response_model=BaseResponse[dict])
async def get_audit_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_audit_logs"))
):
    """Get audit log statistics"""
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get total logs in period
    total_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= start_date
        )
    )
    total_logs = total_result.scalar()
    
    # Get unique admins count
    unique_admins_result = await db.execute(
        select(func.count(func.distinct(AuditLog.admin_id))).where(
            AuditLog.created_at >= start_date
        )
    )
    unique_admins = unique_admins_result.scalar()
    
    # Get actions today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    actions_today_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= today_start
        )
    )
    actions_today = actions_today_result.scalar()
    
    # Get most common action
    most_common_result = await db.execute(
        select(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.created_at >= start_date
        ).group_by(AuditLog.action).order_by(func.count(AuditLog.id).desc()).limit(1)
    )
    most_common_row = most_common_result.fetchone()
    most_common_action = most_common_row[0] if most_common_row else "N/A"
    
    # Get logs by action
    action_result = await db.execute(
        select(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.created_at >= start_date
        ).group_by(AuditLog.action).order_by(func.count(AuditLog.id).desc())
    )
    actions_stats = [{"action": row[0], "count": row[1]} for row in action_result.fetchall()]
    
    # Get logs by resource type
    resource_result = await db.execute(
        select(
            AuditLog.resource_type,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.created_at >= start_date
        ).group_by(AuditLog.resource_type).order_by(func.count(AuditLog.id).desc())
    )
    resource_stats = [{"resource_type": row[0], "count": row[1]} for row in resource_result.fetchall()]
    
    # Get most active admins
    admin_result = await db.execute(
        select(
            Admin.first_name,
            Admin.last_name,
            Admin.email,
            func.count(AuditLog.id).label('count')
        ).join(Admin, AuditLog.admin_id == Admin.id).where(
            AuditLog.created_at >= start_date
        ).group_by(Admin.id, Admin.first_name, Admin.last_name, Admin.email).order_by(func.count(AuditLog.id).desc()).limit(10)
    )
    admin_stats = [
        {
            "admin_name": f"{row[0]} {row[1]}",
            "admin_email": row[2],
            "count": row[3]
        } 
        for row in admin_result.fetchall()
    ]
    
    return BaseResponse.success_response(
        data={
            "total_logs": total_logs,
            "unique_admins": unique_admins,
            "actions_today": actions_today,
            "most_common_action": most_common_action,
            "period_days": days,
            "actions_breakdown": actions_stats,
            "resource_types_breakdown": resource_stats,
            "most_active_admins": admin_stats
        },
        message="Audit statistics retrieved successfully"
    )


@router.post("/", response_model=BaseResponse[AuditLogResponse])
async def create_audit_log(
    log_data: AuditLogCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Create new audit log entry"""
    
    # Get client IP and user agent
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    audit_log = AuditLog(
        admin_id=current_admin.id,
        action=log_data.action,
        resource_type=log_data.resource_type,
        resource_id=log_data.resource_id,
        details=log_data.details,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)
    
    return BaseResponse.success_response(data=audit_log, message="Audit log created successfully")

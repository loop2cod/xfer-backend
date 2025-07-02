"""
Audit logging decorator and utilities for admin actions
"""
from functools import wraps
from typing import Callable, Any, Optional, Dict
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
import inspect
import asyncio

from app.models.admin import Admin
from app.services.audit_log import AuditLogService, AdminAuditActions, AdminResourceTypes


class AuditLogger:
    """Utility class for audit logging"""
    
    @staticmethod
    async def log_activity(
        db: AsyncSession,
        admin: Admin,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log an admin activity"""
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
        
        await AuditLogService.log_admin_activity(
            db=db,
            admin_id=admin.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )


def audit_log(
    action: str,
    resource_type: str,
    resource_id_param: Optional[str] = None,
    include_request_body: bool = False,
    include_response: bool = False
):
    """
    Decorator to automatically log admin activities
    
    Args:
        action: The action being performed (e.g., "create", "update", "delete")
        resource_type: The type of resource being affected (e.g., "user", "transfer")
        resource_id_param: Name of the parameter that contains the resource ID
        include_request_body: Whether to include request body in details
        include_response: Whether to include response data in details
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the signature to find parameters
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Extract common parameters
            db = bound_args.arguments.get('db')
            current_admin = bound_args.arguments.get('current_admin')
            request = bound_args.arguments.get('request')
            
            # Extract resource ID if specified
            resource_id = None
            if resource_id_param and resource_id_param in bound_args.arguments:
                resource_id = str(bound_args.arguments[resource_id_param])
            
            # Prepare details
            details = {}
            
            if include_request_body:
                # Look for request body in common parameter names
                for param_name in ['data', 'update_data', 'create_data', 'user_data', 'admin_data', 'setting_data']:
                    if param_name in bound_args.arguments:
                        param_value = bound_args.arguments[param_name]
                        if hasattr(param_value, 'dict'):
                            details['request_body'] = param_value.dict()
                        elif hasattr(param_value, '__dict__'):
                            details['request_body'] = vars(param_value)
                        else:
                            details['request_body'] = str(param_value)
                        break
            
            # Execute the original function
            result = await func(*args, **kwargs)
            
            # Include response if requested
            if include_response and hasattr(result, 'data'):
                if hasattr(result.data, 'dict'):
                    details['response_data'] = result.data.dict()
                elif hasattr(result.data, 'id'):
                    details['response_data'] = {'id': str(result.data.id)}
            
            # Log the activity if we have the required parameters
            if db and current_admin:
                try:
                    await AuditLogger.log_activity(
                        db=db,
                        admin=current_admin,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details if details else None,
                        request=request
                    )
                except Exception as e:
                    # Log the error but don't fail the request
                    print(f"Failed to log audit activity: {e}")
            
            return result
        
        return wrapper
    return decorator


# Convenience decorators for common actions
def audit_create(resource_type: str, include_response: bool = True):
    return audit_log("create", resource_type, include_request_body=True, include_response=include_response)

def audit_update(resource_type: str, resource_id_param: str = "id", include_request_body: bool = True):
    return audit_log("update", resource_type, resource_id_param, include_request_body, include_response=True)

def audit_delete(resource_type: str, resource_id_param: str = "id"):
    return audit_log("delete", resource_type, resource_id_param)

def audit_view(resource_type: str, resource_id_param: Optional[str] = None):
    return audit_log("view", resource_type, resource_id_param)

def audit_approve(resource_type: str, resource_id_param: str = "id"):
    return audit_log("approve", resource_type, resource_id_param, include_request_body=True)

def audit_reject(resource_type: str, resource_id_param: str = "id"):
    return audit_log("reject", resource_type, resource_id_param, include_request_body=True)


# Auth-specific audit logging
async def log_admin_login(db: AsyncSession, admin: Admin, request: Request, success: bool = True):
    """Log admin login attempt"""
    await AuditLogger.log_activity(
        db=db,
        admin=admin,
        action=AdminAuditActions.LOGIN,
        resource_type=AdminResourceTypes.AUTH,
        details={"success": success},
        request=request
    )

async def log_admin_logout(db: AsyncSession, admin: Admin, request: Request):
    """Log admin logout"""
    await AuditLogger.log_activity(
        db=db,
        admin=admin,
        action=AdminAuditActions.LOGOUT,
        resource_type=AdminResourceTypes.AUTH,
        request=request
    )
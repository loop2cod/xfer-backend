from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, Dict, Any
from uuid import UUID

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

    @staticmethod
    def generate_log_type(resource_type: str) -> str:
        """Generate a human-readable log type from resource_type"""
        type_mapping = {
            AdminResourceTypes.AUTH: "Authentication",
            AdminResourceTypes.USER: "User Management",
            AdminResourceTypes.TRANSFER: "Transfer Management",
            AdminResourceTypes.ADMIN: "Admin Management",
            AdminResourceTypes.SETTINGS: "System Settings",
            AdminResourceTypes.REPORTS: "Reports & Analytics",
            AdminResourceTypes.WALLET: "Wallet Management",
            AdminResourceTypes.BANK_ACCOUNT: "Bank Account Management",
        }
        return type_mapping.get(resource_type, resource_type.replace("_", " ").title())

    @staticmethod
    def generate_activity_description(action: str, resource_type: str, details: Optional[Dict[str, Any]] = None) -> str:
        """Generate a human-readable activity description"""
        action_descriptions = {
            AdminAuditActions.LOGIN: "Admin logged into the system",
            "admin_login": "Admin logged into the system",
            AdminAuditActions.LOGOUT: "Admin logged out of the system",
            "admin_logout": "Admin logged out of the system",
            AdminAuditActions.CREATE_USER: "Created new user account",
            "create_user": "Created new user account",
            AdminAuditActions.UPDATE_USER: "Updated user account information",
            "update_user": "Updated user account information",
            AdminAuditActions.DELETE_USER: "Deleted user account",
            "delete_user": "Deleted user account",
            AdminAuditActions.APPROVE_TRANSFER: "Approved transfer request",
            "approve_transfer": "Approved transfer request",
            AdminAuditActions.REJECT_TRANSFER: "Rejected transfer request",
            "reject_transfer": "Rejected transfer request",
            AdminAuditActions.UPDATE_TRANSFER: "Updated transfer request",
            "update_transfer": "Updated transfer request",
            "update": "Updated record",
            "create": "Created record",
            "delete": "Deleted record",
            "view": "Viewed record",
            AdminAuditActions.CREATE_ADMIN: "Created new admin account",
            "create_admin": "Created new admin account",
            AdminAuditActions.UPDATE_ADMIN: "Updated admin account",
            "update_admin": "Updated admin account",
            AdminAuditActions.DELETE_ADMIN: "Deleted admin account",
            "delete_admin": "Deleted admin account",
            AdminAuditActions.UPDATE_SETTINGS: "Updated system settings",
            "update_settings": "Updated system settings",
            AdminAuditActions.VIEW_REPORTS: "Accessed reports and analytics",
            "view_reports": "Accessed reports and analytics",
            AdminAuditActions.EXPORT_DATA: "Exported system data",
            "export_data": "Exported system data",
        }

        base_description = action_descriptions.get(action, action.replace("_", " ").title())

        # Add resource-specific context
        if resource_type == "transfer_request":
            if action == "update":
                base_description = "Updated transfer request"
            elif action == "create":
                base_description = "Created transfer request"
            elif action == "view":
                base_description = "Viewed transfer request"

        # Add additional context from details if available
        if details:
            if "user_email" in details:
                base_description += f" for user {details['user_email']}"
            elif "admin_email" in details:
                base_description += f" for admin {details['admin_email']}"
            elif "transfer_id" in details:
                base_description += f" (Transfer ID: {details['transfer_id']})"
            elif "amount" in details and "currency" in details:
                base_description += f" (Amount: {details['amount']} {details['currency']})"

            # Special handling for transfer request updates
            if action == "update" and resource_type == "transfer_request":
                if "request_body" in details and "status" in details["request_body"]:
                    status = details["request_body"]["status"]
                    base_description += f" - Status changed to {status}"

        return base_description

    @staticmethod
    def generate_reference_link(resource_type: str, resource_id: Optional[str] = None) -> Optional[str]:
        """Generate a reference link to the related resource"""
        if not resource_id:
            return None

        # Map both constant values and actual database values
        link_mapping = {
            # Constant values
            AdminResourceTypes.USER: f"/customers/details/{resource_id}",
            AdminResourceTypes.TRANSFER: f"/requests/details/{resource_id}",
            AdminResourceTypes.ADMIN: f"/admin-users/details/{resource_id}",
            AdminResourceTypes.WALLET: f"/wallets/details/{resource_id}",
            AdminResourceTypes.BANK_ACCOUNT: f"/wallets/bank-accounts/{resource_id}",
            AdminResourceTypes.REPORTS: f"/reports",
            AdminResourceTypes.SETTINGS: f"/settings",
            # Actual database values
            "transfer_request": f"/requests/details/{resource_id}",
            "user": f"/customers/details/{resource_id}",
            "admin": f"/admin-users/details/{resource_id}",
            "wallet": f"/wallets/details/{resource_id}",
            "bank_account": f"/wallets/bank-accounts/{resource_id}",
            "system_settings": f"/settings",
        }

        return link_mapping.get(resource_type)




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
#!/usr/bin/env python3
"""
Script to populate audit logs with sample data for testing
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4
import random

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import get_async_session_context
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.services.audit_log import AuditLogService, AdminAuditActions, AdminResourceTypes
from app.core.security import get_password_hash
from sqlalchemy import select


async def create_sample_admin():
    """Create a sample admin for testing if none exists"""
    async with get_async_session_context() as db:
        # Check if admin exists
        result = await db.execute(select(Admin).where(Admin.email == "admin@example.com"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("Creating sample admin...")
            admin = Admin(
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                first_name="System",
                last_name="Administrator",
                role="super_admin",
                is_active=True,
                is_super_admin=True,
                permissions={
                    "can_view_audit_logs": True,
                    "can_manage_users": True,
                    "can_approve_transfers": True,
                    "can_manage_system_settings": True,
                    "can_view_reports": True,
                    "can_manage_wallets": True
                }
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            print(f"✅ Created admin: {admin.email}")
        else:
            print(f"✅ Using existing admin: {admin.email}")
        
        return admin


async def populate_audit_logs():
    """Populate audit logs with sample data"""
    print("🔄 Populating audit logs with sample data...")
    
    admin = await create_sample_admin()
    
    # Sample audit log data
    sample_actions = [
        {
            "action": AdminAuditActions.LOGIN,
            "resource_type": AdminResourceTypes.AUTH,
            "details": {"login_method": "email_password", "success": True}
        },
        {
            "action": AdminAuditActions.CREATE_USER,
            "resource_type": AdminResourceTypes.USER,
            "resource_id": str(uuid4()),
            "details": {"user_email": "john.doe@example.com", "kyc_status": "pending"}
        },
        {
            "action": AdminAuditActions.APPROVE_TRANSFER,
            "resource_type": AdminResourceTypes.TRANSFER,
            "resource_id": str(uuid4()),
            "details": {"amount": 1000.0, "currency": "USD", "crypto_type": "USDT"}
        },
        {
            "action": AdminAuditActions.UPDATE_USER,
            "resource_type": AdminResourceTypes.USER,
            "resource_id": str(uuid4()),
            "details": {"field_updated": "kyc_status", "old_value": "pending", "new_value": "approved"}
        },
        {
            "action": AdminAuditActions.REJECT_TRANSFER,
            "resource_type": AdminResourceTypes.TRANSFER,
            "resource_id": str(uuid4()),
            "details": {"amount": 500.0, "reason": "Insufficient documentation"}
        },
        {
            "action": AdminAuditActions.UPDATE_SETTINGS,
            "resource_type": AdminResourceTypes.SETTINGS,
            "details": {"setting": "max_transfer_amount", "old_value": 10000, "new_value": 15000}
        },
        {
            "action": AdminAuditActions.CREATE_ADMIN,
            "resource_type": AdminResourceTypes.ADMIN,
            "resource_id": str(uuid4()),
            "details": {"admin_email": "operator@example.com", "role": "operator"}
        },
        {
            "action": AdminAuditActions.VIEW_REPORTS,
            "resource_type": AdminResourceTypes.REPORTS,
            "details": {"report_type": "financial", "date_range": "2024-01-01 to 2024-01-31"}
        }
    ]
    
    async with get_async_session_context() as db:
        created_count = 0
        
        # Create logs with varied timestamps (last 30 days)
        for i in range(50):  # Create 50 sample logs
            action_data = random.choice(sample_actions)
            
            # Create timestamp between 30 days ago and now
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            timestamp = datetime.utcnow() - timedelta(
                days=days_ago, 
                hours=hours_ago, 
                minutes=minutes_ago
            )
            
            # Random IP addresses for diversity
            ip_addresses = [
                "192.168.1.100",
                "10.0.0.50",
                "172.16.0.25",
                "203.0.113.10",
                "198.51.100.15"
            ]
            
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            ]
            
            audit_log = AuditLog(
                admin_id=admin.id,
                action=action_data["action"],
                resource_type=action_data["resource_type"],
                resource_id=action_data.get("resource_id"),
                details=action_data.get("details"),
                ip_address=random.choice(ip_addresses),
                user_agent=random.choice(user_agents),
                created_at=timestamp
            )
            
            db.add(audit_log)
            created_count += 1
        
        await db.commit()
        print(f"✅ Created {created_count} sample audit logs")
        
        # Show statistics
        total_result = await db.execute(select(AuditLog).where(AuditLog.admin_id == admin.id))
        total_logs = len(list(total_result.scalars().all()))
        
        print(f"📊 Total audit logs for {admin.email}: {total_logs}")
        
        return True


async def main():
    """Main function"""
    print("🚀 Audit Logs Population Script")
    print("=" * 40)
    
    try:
        success = await populate_audit_logs()
        if success:
            print("\n🎉 Sample audit logs created successfully!")
            print("\nYou can now:")
            print("1. Login to admin dashboard with: admin@example.com / admin123")
            print("2. Navigate to /audit to view the logs")
            print("3. Test filtering and search functionality")
        else:
            print("\n❌ Failed to create sample audit logs")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
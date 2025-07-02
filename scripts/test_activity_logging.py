#!/usr/bin/env python3
"""
Test script to verify activity logging implementation
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import get_db
from app.models.user import User
from app.models.admin import Admin
from app.models.user_activity import UserActivity
from app.models.audit_log import AuditLog
from app.services.user_activity import UserActivityService, ActivityActions, ResourceTypes
from app.services.audit_log import AuditLogService, AdminAuditActions, AdminResourceTypes
from sqlalchemy import select


async def test_user_activity_logging():
    """Test user activity logging"""
    print("Testing User Activity Logging...")
    
    async for db in get_db():
        try:
            # Find a test user
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ No users found in database")
                return False
            
            print(f"✅ Found test user: {user.email}")
            
            # Test logging a login activity
            activity = await UserActivityService.log_activity(
                db=db,
                user_id=user.id,
                action=ActivityActions.LOGIN,
                resource_type=ResourceTypes.AUTH,
                details={"test": "login_test"},
                ip_address="127.0.0.1",
                user_agent="Test Agent"
            )
            
            print(f"✅ Logged user activity: {activity.id}")
            
            # Test retrieving activities
            activities, count = await UserActivityService.get_user_activities(
                db=db,
                user_id=user.id,
                limit=5
            )
            
            print(f"✅ Retrieved {len(activities)} activities (total: {count})")
            
            # Test activity stats
            stats = await UserActivityService.get_activity_stats(
                db=db,
                user_id=user.id,
                days=30
            )
            
            print(f"✅ Activity stats: {stats['total_activities']} activities in 30 days")
            
            return True
            
        except Exception as e:
            print(f"❌ User activity test failed: {e}")
            return False


async def test_admin_audit_logging():
    """Test admin audit logging"""
    print("\nTesting Admin Audit Logging...")
    
    async for db in get_db():
        try:
            # Find a test admin
            result = await db.execute(select(Admin).limit(1))
            admin = result.scalar_one_or_none()
            
            if not admin:
                print("❌ No admins found in database")
                return False
            
            print(f"✅ Found test admin: {admin.email}")
            
            # Test logging an admin login activity
            audit_log = await AuditLogService.log_admin_activity(
                db=db,
                admin_id=admin.id,
                action=AdminAuditActions.LOGIN,
                resource_type=AdminResourceTypes.AUTH,
                details={
                    "test": "admin_login_test",
                    "admin_email": admin.email,
                    "admin_role": admin.role
                },
                ip_address="127.0.0.1",
                user_agent="Test Agent"
            )
            
            print(f"✅ Logged admin audit: {audit_log.id}")
            
            # Test retrieving audit logs
            audit_logs, count = await AuditLogService.get_admin_audit_logs(
                db=db,
                limit=5
            )
            
            print(f"✅ Retrieved {len(audit_logs)} audit logs (total: {count})")
            
            return True
            
        except Exception as e:
            print(f"❌ Admin audit test failed: {e}")
            return False


async def test_database_tables():
    """Test if the required tables exist"""
    print("\nTesting Database Tables...")
    
    async for db in get_db():
        try:
            # Test user_activities table
            result = await db.execute(select(UserActivity).limit(1))
            print("✅ user_activities table exists")
            
            # Test audit_logs table
            result = await db.execute(select(AuditLog).limit(1))
            print("✅ audit_logs table exists")
            
            return True
            
        except Exception as e:
            print(f"❌ Database table test failed: {e}")
            return False


async def main():
    """Main test function"""
    print("🧪 Activity Logging Implementation Test")
    print("=" * 50)
    
    # Test database tables
    tables_ok = await test_database_tables()
    
    if not tables_ok:
        print("\n❌ Database tables not ready. Please run migrations first.")
        return
    
    # Test user activity logging
    user_activity_ok = await test_user_activity_logging()
    
    # Test admin audit logging
    admin_audit_ok = await test_admin_audit_logging()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Database Tables: {'✅ PASS' if tables_ok else '❌ FAIL'}")
    print(f"User Activity Logging: {'✅ PASS' if user_activity_ok else '❌ FAIL'}")
    print(f"Admin Audit Logging: {'✅ PASS' if admin_audit_ok else '❌ FAIL'}")
    
    if all([tables_ok, user_activity_ok, admin_audit_ok]):
        print("\n🎉 All tests passed! Activity logging is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Script to create initial admin user
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.admin import Admin
from app.core.security import get_password_hash


async def create_admin():
    """Create initial admin user"""
    
    email = input("Enter admin email: ").strip()
    if not email:
        print("Email is required")
        return
    
    password = input("Enter admin password: ").strip()
    if not password or len(password) < 8:
        print("Password must be at least 8 characters")
        return
    
    first_name = input("Enter first name: ").strip()
    if not first_name:
        print("First name is required")
        return
    
    last_name = input("Enter last name: ").strip()
    if not last_name:
        print("Last name is required")
        return
    
    async with AsyncSessionLocal() as db:
        # Check if admin already exists
        result = await db.execute(select(Admin).where(Admin.email == email))
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"Admin with email {email} already exists")
            return
        
        # Create admin
        hashed_password = get_password_hash(password)
        admin = Admin(
            email=email,
            password_hash=hashed_password,
            first_name=first_name,
            last_name=last_name,
            role="super_admin",
            is_super_admin=True,
            permissions={
                "can_manage_admins": True,
                "can_manage_users": True,
                "can_approve_transfers": True,
                "can_view_reports": True,
                "can_manage_wallets": True,
                "can_view_audit_logs": True,
                "can_manage_system_settings": True,
                "can_export_data": True
            }
        )
        
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        
        print(f"Super admin created successfully!")
        print(f"ID: {admin.id}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role}")


if __name__ == "__main__":
    print("Creating initial admin user...")
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error creating admin: {e}")
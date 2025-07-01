#!/usr/bin/env python3
"""
Test script to verify transfer status update functionality
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timezone

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.transfer import TransferRequest
from app.models.admin import Admin
from app.models.user import User
from app.schemas.transfer import TransferUpdate


async def test_status_update():
    """Test transfer status update functionality"""
    
    async for db in get_db():
        try:
            # Get the first transfer
            result = await db.execute(select(TransferRequest).limit(1))
            transfer = result.scalar_one_or_none()
            
            if not transfer:
                print("No transfers found in database")
                return
            
            print(f"Testing with transfer: {transfer.id}")
            print(f"Current status: {transfer.status}")
            print(f"Current status_history: {transfer.status_history}")
            
            # Get the first admin
            admin_result = await db.execute(select(Admin).limit(1))
            admin = admin_result.scalar_one_or_none()
            
            if not admin:
                print("No admin found in database")
                return
            
            print(f"Using admin: {admin.first_name} {admin.last_name}")
            
            # Test the status update logic
            old_status = transfer.status
            new_status = "processing" if old_status != "processing" else "completed"
            
            # Initialize status_history as a list if it's None
            if transfer.status_history is None:
                transfer.status_history = []
            
            # Create new history entry
            history_entry = {
                "from_status": old_status,
                "to_status": new_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "changed_by": str(admin.id),
                "changed_by_name": f"{admin.first_name} {admin.last_name}".strip(),
                "message": f"Test status change from {old_status} to {new_status}",
                "admin_remarks": "This is a test update",
                "internal_notes": "Internal test note"
            }
            
            # Create a new list to ensure SQLAlchemy detects the change
            current_history = list(transfer.status_history) if transfer.status_history else []
            current_history.append(history_entry)
            transfer.status_history = current_history
            
            # Update the status
            transfer.status = new_status
            transfer.processed_by = admin.id
            if new_status == "completed":
                transfer.completed_at = datetime.now(timezone.utc)
            
            # Update the updated_at timestamp
            transfer.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(transfer)
            
            print(f"\nStatus updated successfully!")
            print(f"New status: {transfer.status}")
            print(f"New status_history: {json.dumps(transfer.status_history, indent=2)}")
            
        except Exception as e:
            print(f"Error during test: {e}")
            await db.rollback()
            import traceback
            traceback.print_exc()
        
        break  # Only process the first db session


if __name__ == "__main__":
    asyncio.run(test_status_update())
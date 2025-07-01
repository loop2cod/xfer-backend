#!/usr/bin/env python3
"""
Script to fix status history for existing transfers that don't have proper history
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.models.transfer import TransferRequest


async def fix_status_history():
    """Add initial status history to transfers that don't have it"""
    
    async for db in get_db():
        try:
            # Get all transfers without status_history or with empty status_history
            result = await db.execute(
                select(TransferRequest).where(
                    (TransferRequest.status_history.is_(None)) | 
                    (TransferRequest.status_history == [])
                )
            )
            transfers = result.scalars().all()
            
            print(f"Found {len(transfers)} transfers without status history")
            
            for transfer in transfers:
                # Create initial status history entry
                initial_history = [{
                    "from_status": None,
                    "to_status": transfer.status,
                    "timestamp": transfer.created_at.isoformat() if transfer.created_at else datetime.now(timezone.utc).isoformat(),
                    "changed_by": "system",
                    "changed_by_name": "System",
                    "message": "Initial status from migration",
                    "admin_remarks": None,
                    "internal_notes": None
                }]
                
                # Add any status changes based on completion
                if transfer.status == "completed" and transfer.completed_at:
                    initial_history.append({
                        "from_status": "pending",
                        "to_status": "completed",
                        "timestamp": transfer.completed_at.isoformat(),
                        "changed_by": transfer.processed_by or "system",
                        "changed_by_name": "Admin" if transfer.processed_by else "System",
                        "message": "Transfer completed",
                        "admin_remarks": None,
                        "internal_notes": None
                    })
                
                transfer.status_history = initial_history
                
            await db.commit()
            print(f"Successfully updated {len(transfers)} transfers with status history")
            
        except Exception as e:
            print(f"Error updating status history: {e}")
            await db.rollback()
        
        break  # Only process the first db session


if __name__ == "__main__":
    asyncio.run(fix_status_history())
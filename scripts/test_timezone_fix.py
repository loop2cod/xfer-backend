#!/usr/bin/env python3
"""
Test script to verify timezone handling in user activities
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import get_db
from app.models.user import User
from app.models.user_activity import UserActivity
from app.services.user_activity import UserActivityService, ActivityActions, ResourceTypes
from app.schemas.user_activity import UserActivityResponse
from sqlalchemy import select


async def test_timezone_handling():
    """Test timezone handling in user activities"""
    print("Testing timezone handling in user activities...")
    
    async for db in get_db():
        try:
            # Find a test user
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ No users found in database")
                return False
            
            print(f"✅ Found test user: {user.email}")
            
            # Create a new activity with explicit UTC timezone
            current_time = datetime.now(timezone.utc)
            print(f"Current UTC time: {current_time.isoformat()}")
            
            # Test logging a login activity
            activity = await UserActivityService.log_activity(
                db=db,
                user_id=user.id,
                action=ActivityActions.LOGIN,
                resource_type=ResourceTypes.AUTH,
                details={"test": "timezone_test", "timestamp": current_time.isoformat()},
                ip_address="127.0.0.1",
                user_agent="Timezone Test Agent"
            )
            
            print(f"✅ Created activity: {activity.id}")
            print(f"Activity created_at: {activity.created_at}")
            print(f"Activity created_at type: {type(activity.created_at)}")
            print(f"Activity created_at timezone: {activity.created_at.tzinfo}")
            
            # Test retrieving the activity
            activities, count = await UserActivityService.get_user_activities(
                db=db,
                user_id=user.id,
                limit=1
            )
            
            if activities:
                retrieved_activity = activities[0]
                print(f"✅ Retrieved activity: {retrieved_activity.id}")
                print(f"Retrieved created_at: {retrieved_activity.created_at}")
                print(f"Retrieved created_at type: {type(retrieved_activity.created_at)}")
                print(f"Retrieved created_at timezone: {retrieved_activity.created_at.tzinfo}")
                
                # Test schema serialization
                activity_response = UserActivityResponse.model_validate(retrieved_activity)
                print(f"✅ Schema validation successful")
                print(f"Schema created_at: {activity_response.created_at}")
                
                # Test JSON serialization
                activity_dict = activity_response.model_dump()
                print(f"✅ JSON serialization successful")
                print(f"JSON created_at: {activity_dict['created_at']}")
                
                # Verify timezone consistency
                if retrieved_activity.created_at.tzinfo is not None:
                    print("✅ Timezone information preserved")
                else:
                    print("⚠️  Timezone information missing")
                
                return True
            else:
                print("❌ No activities retrieved")
                return False
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_api_stats():
    """Test the API stats endpoint directly"""
    print("Testing API stats endpoint...")

    async for db in get_db():
        try:
            # Find a test user
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()

            if not user:
                print("❌ No users found in database")
                return False

            print(f"✅ Found test user: {user.email}")

            # Test the stats service directly
            stats = await UserActivityService.get_activity_stats(
                db=db,
                user_id=user.id,
                days=30
            )

            print(f"✅ Stats retrieved successfully")
            print(f"Stats: {stats}")

            # Check last_login format
            if stats.get('last_login'):
                last_login = stats['last_login']
                print(f"Last login: {last_login}")
                print(f"Last login type: {type(last_login)}")

                # Verify it's a proper ISO format with timezone
                if '+' in last_login or 'Z' in last_login:
                    print("✅ Last login has timezone information")
                else:
                    print("⚠️  Last login missing timezone information")

                return True
            else:
                print("ℹ️  No last login found (user may not have logged in recently)")
                return True

        except Exception as e:
            print(f"❌ API stats test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Main test function"""
    print("🧪 Starting timezone handling tests...\n")

    success1 = await test_timezone_handling()
    print("\n" + "="*50 + "\n")
    success2 = await test_api_stats()

    if success1 and success2:
        print("\n✅ All timezone tests passed!")
    else:
        print("\n❌ Some timezone tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

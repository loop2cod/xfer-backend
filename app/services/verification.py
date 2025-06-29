import redis.asyncio as redis
import json
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class VerificationService:
    def __init__(self):
        self.redis_client = None
        self.prefix = "verification:"
        self.expiry_minutes = 10

    async def get_redis_client(self):
        """Get Redis client with lazy initialization"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                # Test connection
                await self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                raise
        return self.redis_client

    def generate_verification_code(self) -> str:
        """Generate a 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=6))

    async def store_verification_code(self, email: str, verification_code: str) -> bool:
        """Store verification code in Redis with expiration"""
        try:
            redis_client = await self.get_redis_client()
            key = f"{self.prefix}{email}"
            
            # Store verification data
            verification_data = {
                "code": verification_code,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(minutes=self.expiry_minutes)).isoformat()
            }
            
            # Store with expiration
            await redis_client.setex(
                key,
                timedelta(minutes=self.expiry_minutes),
                json.dumps(verification_data)
            )
            
            logger.info(f"Verification code stored for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store verification code for {email}: {str(e)}")
            return False

    async def verify_code(self, email: str, provided_code: str) -> Dict[str, Any]:
        """Verify the provided code against stored code"""
        try:
            redis_client = await self.get_redis_client()
            key = f"{self.prefix}{email}"
            
            # Get stored verification data
            stored_data = await redis_client.get(key)
            if not stored_data:
                return {
                    "valid": False,
                    "error": "No verification code found or code has expired"
                }
            
            verification_data = json.loads(stored_data)
            stored_code = verification_data.get("code")
            expires_at = datetime.fromisoformat(verification_data.get("expires_at"))
            
            # Check if code has expired
            if datetime.utcnow() > expires_at:
                await redis_client.delete(key)  # Clean up expired code
                return {
                    "valid": False,
                    "error": "Verification code has expired"
                }
            
            # Check if code matches
            if stored_code != provided_code:
                return {
                    "valid": False,
                    "error": "Invalid verification code"
                }
            
            # Code is valid - delete it to prevent reuse
            await redis_client.delete(key)
            
            logger.info(f"Verification successful for {email}")
            return {
                "valid": True,
                "message": "Verification code is valid"
            }
            
        except Exception as e:
            logger.error(f"Failed to verify code for {email}: {str(e)}")
            return {
                "valid": False,
                "error": "Verification failed due to server error"
            }

    async def cleanup_expired_codes(self):
        """Cleanup expired verification codes - called by background task"""
        try:
            redis_client = await self.get_redis_client()
            pattern = f"{self.prefix}*"
            
            async for key in redis_client.scan_iter(match=pattern):
                try:
                    stored_data = await redis_client.get(key)
                    if stored_data:
                        verification_data = json.loads(stored_data)
                        expires_at = datetime.fromisoformat(verification_data.get("expires_at"))
                        
                        if datetime.utcnow() > expires_at:
                            await redis_client.delete(key)
                            logger.info(f"Cleaned up expired verification code: {key}")
                except Exception as e:
                    logger.error(f"Error cleaning up key {key}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup expired codes: {str(e)}")

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()


# Global verification service instance
verification_service = VerificationService()
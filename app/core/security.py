from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """Verify JWT token and return subject"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        if payload.get("type") != token_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def generate_api_key() -> str:
    """Generate API key for admin access"""
    import secrets
    return secrets.token_urlsafe(32)


def generate_transfer_id() -> str:
    """Generate alphanumeric transfer ID in format TX-XXXXXXXX"""
    import random
    import string

    # Generate 8 random alphanumeric characters (digits only for now as requested)
    random_digits = ''.join(random.choices(string.digits, k=8))
    return f"TX-{random_digits}"


def generate_customer_id() -> str:
    """Generate alphanumeric customer ID in format CT-XXXXXXXX"""
    import random
    import string

    # Generate 8 random digits
    random_digits = ''.join(random.choices(string.digits, k=8))
    return f"CT-{random_digits}"
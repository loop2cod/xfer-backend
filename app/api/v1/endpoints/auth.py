from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime
import random
import string

from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    verify_token
)
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.admin import Admin
from app.schemas.auth import (
    Token, 
    RefreshToken, 
    EmailVerificationRequest, 
    ResendVerificationRequest,
    PreRegistrationVerificationRequest,
    PreRegistrationCodeVerifyRequest
)
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.schemas.base import BaseResponse, MessageResponse
from app.services.email import email_service
from app.services.verification import verification_service

router = APIRouter()


@router.post("/register", response_model=BaseResponse[UserResponse])
async def register(
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Register new user"""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    verification_code = generate_verification_code()
    expiration_time = datetime.utcnow() + timedelta(minutes=10)
    
    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        verification_code=verification_code,
        verification_code_expires=expiration_time
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Send verification email in background
    background_tasks.add_task(
        send_verification_email_task,
        user_data.email,
        verification_code
    )
    
    return BaseResponse.success_response(data=user, message="User registered successfully")


@router.post("/login", response_model=BaseResponse[Token])
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """User login"""
    # Find user
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    
    # Update last login
    from sqlalchemy.sql import func
    user.last_login = func.now()
    await db.commit()
    
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    
    return BaseResponse.success_response(data=token_data, message="Login successful")


@router.post("/admin/login", response_model=BaseResponse[Token])
async def admin_login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Admin login"""
    # Find admin
    result = await db.execute(select(Admin).where(Admin.email == user_data.email))
    admin = result.scalar_one_or_none()
    
    if not admin or not verify_password(user_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive admin"
        )
    
    # Create tokens
    access_token = create_access_token(subject=str(admin.id))
    refresh_token = create_refresh_token(subject=str(admin.id))
    
    # Update last login
    from sqlalchemy.sql import func
    admin.last_login = func.now()
    await db.commit()
    
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    
    return BaseResponse.success_response(data=token_data, message="Admin login successful")


@router.post("/refresh", response_model=BaseResponse[Token])
async def refresh_token(refresh_data: RefreshToken, db: AsyncSession = Depends(get_db)):
    """Refresh access token"""
    user_id = verify_token(refresh_data.refresh_token, token_type="refresh")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))
    
    token_data = {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
    
    return BaseResponse.success_response(data=token_data, message="Token refreshed successfully")


def generate_verification_code() -> str:
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))


@router.post("/send-verification", response_model=MessageResponse)
async def send_verification_code(
    request: ResendVerificationRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Send verification code to user's email"""
    # Find user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already verified"
        )
    
    # Generate verification code
    verification_code = generate_verification_code()
    
    # Set expiration time (10 minutes from now)
    expiration_time = datetime.utcnow() + timedelta(minutes=10)
    
    # Update user with verification code
    user.verification_code = verification_code
    user.verification_code_expires = expiration_time
    await db.commit()
    
    # Send email with verification code in background
    background_tasks.add_task(
        send_verification_email_task,
        request.email,
        verification_code
    )
    
    return MessageResponse.success_message("Verification code sent successfully")


@router.post("/verify-email", response_model=BaseResponse[Token])
async def verify_email(request: EmailVerificationRequest, db: AsyncSession = Depends(get_db)):
    """Verify user's email with verification code and return auth tokens"""
    # Find user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already verified"
        )
    
    # Check if verification code exists and is not expired
    if not user.verification_code or not user.verification_code_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found. Please request a new one."
        )
    
    if datetime.utcnow() > user.verification_code_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one."
        )
    
    # Verify the code
    if user.verification_code != request.verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Mark user as verified
    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    
    # Create tokens for automatic login
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    
    # Update last login
    from sqlalchemy.sql import func
    user.last_login = func.now()
    
    await db.commit()
    
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    
    return BaseResponse.success_response(data=token_data, message="Email verified successfully")


@router.post("/send-pre-registration-code", response_model=BaseResponse[dict])
async def send_pre_registration_verification_code(
    request: PreRegistrationVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Send verification code to email before registration (for new flow)"""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please use the login flow instead."
        )
    
    # Generate verification code
    verification_code = verification_service.generate_verification_code()
    
    # Store verification code in Redis
    code_stored = await verification_service.store_verification_code(
        request.email, 
        verification_code
    )
    
    if not code_stored:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code. Please try again."
        )
    
    # Send email with verification code in background
    background_tasks.add_task(
        send_verification_email_task,
        request.email,
        verification_code
    )
    
    response_data = {
        "email": request.email,
        "expires_in_minutes": 10
    }
    
    return BaseResponse.success_response(data=response_data, message="Verification code sent successfully")


@router.post("/verify-pre-registration-code", response_model=BaseResponse[dict])
async def verify_pre_registration_code(
    request: PreRegistrationCodeVerifyRequest
):
    """Verify the pre-registration verification code"""
    # Verify code using verification service
    verification_result = await verification_service.verify_code(
        request.email, 
        request.verification_code
    )
    
    if not verification_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification_result["error"]
        )
    
    response_data = {
        "verified": True,
        "email": request.email
    }
    
    return BaseResponse.success_response(data=response_data, message="Verification code is valid")


# Background task functions
async def send_verification_email_task(email: str, verification_code: str):
    """Background task to send verification email"""
    try:
            print(f"📧 Sending verification email to {email} with code: {verification_code}")
            await email_service.send_verification_email(email, verification_code)
    except Exception as e:
        # Log the error but don't fail the registration process
        print(f"❌ Failed to send email to {email}: {str(e)}")
        # You might want to use proper logging here:
        # logger.error(f"Failed to send verification email to {email}: {str(e)}")
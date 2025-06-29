from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
import json
from decimal import Decimal

from app.api.deps import get_current_user, get_current_admin, check_admin_permission
from app.db.database import get_db, get_redis
from app.models.user import User
from app.models.transfer import TransferRequest
from app.core.config import settings
from app.schemas.transfer import (
    TransferCreate, 
    TransferUpdate, 
    TransferResponse, 
    TransferStats
)
from app.schemas.base import BaseResponse, MessageResponse

router = APIRouter()


@router.post("/", response_model=BaseResponse[TransferResponse])
async def create_transfer(
    transfer_data: TransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new transfer request"""
    
    # Validate amount limits
    if transfer_data.amount < Decimal(str(settings.MINIMUM_TRANSFER_AMOUNT)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum transfer amount is {settings.MINIMUM_TRANSFER_AMOUNT}"
        )
    
    if transfer_data.amount > Decimal(str(settings.MAXIMUM_TRANSFER_AMOUNT)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum transfer amount is {settings.MAXIMUM_TRANSFER_AMOUNT}"
        )
    
    # Calculate fee and net amount
    fee = transfer_data.amount * Decimal(str(settings.TRANSFER_FEE_PERCENTAGE))
    net_amount = transfer_data.amount - fee
    
    # Create transfer request
    transfer = TransferRequest(
        user_id=current_user.id,
        type=transfer_data.type,
        amount=transfer_data.amount,
        fee=fee,
        net_amount=net_amount,
        currency=transfer_data.currency,
        deposit_wallet_address=transfer_data.deposit_wallet_address,
        crypto_tx_hash=transfer_data.crypto_tx_hash,
        admin_wallet_address=settings.ADMIN_WALLET_ADDRESS,
        bank_account_info=transfer_data.bank_account_info.dict() if transfer_data.bank_account_info else None,
        bank_accounts=[acc.dict() for acc in transfer_data.bank_accounts] if transfer_data.bank_accounts else None
    )
    
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)
    
    # Send to background task for processing
    # TODO: Add Celery task for blockchain monitoring
    
    return BaseResponse.success_response(data=transfer, message="Transfer operation completed successfully")


@router.get("/", response_model=BaseResponse[List[TransferResponse]])
async def get_user_transfers(
    skip: int = 0,
    limit: int = 20,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's transfer requests"""
    query = select(TransferRequest).where(TransferRequest.user_id == current_user.id)
    
    if type_filter:
        query = query.where(TransferRequest.type == type_filter)
    
    if status_filter:
        query = query.where(TransferRequest.status == status_filter)
    
    query = query.order_by(TransferRequest.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    transfers = result.scalars().all()
    
    return BaseResponse.success_response(data=transfers, message="Transfers retrieved successfully")


@router.get("/{transfer_id}", response_model=BaseResponse[TransferResponse])
async def get_transfer(
    transfer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific transfer request"""
    result = await db.execute(
        select(TransferRequest).where(
            and_(
                TransferRequest.id == transfer_id,
                TransferRequest.user_id == current_user.id
            )
        )
    )
    transfer = result.scalar_one_or_none()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    return BaseResponse.success_response(data=transfer, message="Transfer operation completed successfully")


@router.get("/{transfer_id}/status", response_model=BaseResponse[dict])
async def get_transfer_status(
    transfer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transfer status (fast endpoint for polling)"""
    try:
        redis_client = await get_redis()
        # Try to get from cache first
        cached_status = await redis_client.get(f"transfer_status:{transfer_id}")
        if cached_status:
            return json.loads(cached_status)
    except Exception:
        # Redis not available, continue without cache
        pass
    
    # Get from database
    result = await db.execute(
        select(TransferRequest.status, TransferRequest.status_message, TransferRequest.confirmation_count).where(
            and_(
                TransferRequest.id == transfer_id,
                TransferRequest.user_id == current_user.id
            )
        )
    )
    transfer_data = result.first()
    
    if not transfer_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    status_data = {
        "status": transfer_data.status,
        "status_message": transfer_data.status_message,
        "confirmation_count": transfer_data.confirmation_count or 0
    }
    
    # Cache for 30 seconds (if Redis is available)
    try:
        redis_client = await get_redis()
        await redis_client.setex(f"transfer_status:{transfer_id}", 30, json.dumps(status_data))
    except Exception:
        # Redis not available, skip caching
        pass
    
    return BaseResponse.success_response(data=status_data, message="Transfer status retrieved successfully")


# Admin endpoints
@router.get("/admin/all", response_model=BaseResponse[List[TransferResponse]])
async def get_all_transfers(
    skip: int = 0,
    limit: int = 50,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_transfers"))
):
    """Get all transfer requests (admin only)"""
    query = select(TransferRequest).options(selectinload(TransferRequest.user))
    
    if type_filter:
        query = query.where(TransferRequest.type == type_filter)
    
    if status_filter:
        query = query.where(TransferRequest.status == status_filter)
    
    if search:
        # Search in user email, transaction hash, or transfer ID
        query = query.join(User).where(
            or_(
                User.email.ilike(f"%{search}%"),
                TransferRequest.crypto_tx_hash.ilike(f"%{search}%"),
                TransferRequest.id.cast(str).ilike(f"%{search}%")
            )
        )
    
    query = query.order_by(TransferRequest.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    transfers = result.scalars().all()
    
    return BaseResponse.success_response(data=transfers, message="Transfers retrieved successfully")


@router.put("/admin/{transfer_id}", response_model=BaseResponse[TransferResponse])
async def update_transfer(
    transfer_id: UUID,
    update_data: TransferUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_approve_transfers"))
):
    """Update transfer request (admin only)"""
    result = await db.execute(select(TransferRequest).where(TransferRequest.id == transfer_id))
    transfer = result.scalar_one_or_none()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    # Update fields
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(transfer, field, value)
    
    # Set processed_by and completion time
    transfer.processed_by = current_admin.id
    if update_data.status == "completed":
        transfer.completed_at = func.now()
    
    await db.commit()
    await db.refresh(transfer)
    
    # Update cache (if Redis is available)
    try:
        redis_client = await get_redis()
        await redis_client.delete(f"transfer_status:{transfer_id}")
    except Exception:
        # Redis not available, skip cache update
        pass
    
    return BaseResponse.success_response(data=transfer, message="Transfer operation completed successfully")


@router.get("/admin/stats", response_model=BaseResponse[TransferStats])
async def get_transfer_stats(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_reports"))
):
    """Get transfer statistics (admin only)"""
    # Get counts by status
    result = await db.execute(
        select(
            func.count(TransferRequest.id).label("total"),
            func.count().filter(TransferRequest.status == "pending").label("pending"),
            func.count().filter(TransferRequest.status == "completed").label("completed"),
            func.count().filter(TransferRequest.status == "failed").label("failed"),
            func.sum(TransferRequest.amount).label("total_volume"),
            func.sum(TransferRequest.fee).label("total_fees")
        )
    )
    stats = result.first()
    
    transfer_stats = TransferStats(
        total_requests=stats.total or 0,
        pending_requests=stats.pending or 0,
        completed_requests=stats.completed or 0,
        failed_requests=stats.failed or 0,
        total_volume=float(stats.total_volume or 0),
        total_fees=float(stats.total_fees or 0)
    )
    
    return BaseResponse.success_response(data=transfer_stats, message="Transfer statistics retrieved successfully")


# WebSocket for real-time updates
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: UUID):
    """WebSocket endpoint for real-time transfer updates"""
    await websocket.accept()
    redis_client = await get_redis()
    
    try:
        while True:
            # Listen for updates specific to this user
            message = await websocket.receive_text()
            
            # You can implement pub/sub here for real-time updates
            # For now, send a simple acknowledgment
            await websocket.send_text(json.dumps({
                "type": "connection_confirmed",
                "user_id": str(user_id)
            }))
            
    except WebSocketDisconnect:
        pass
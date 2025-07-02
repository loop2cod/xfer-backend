from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, String
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID
import json
import asyncio
from decimal import Decimal
from datetime import datetime, timezone

from app.api.deps import get_current_user, check_admin_permission
from app.db.database import get_db, get_redis
from app.models.user import User
from app.models.admin import Admin
from app.models.transfer import TransferRequest
from app.models.admin_wallet import AdminWallet
from app.core.config import settings
from app.schemas.transfer import (
    TransferCreate,
    TransferUpdate,
    TransferResponse,
    TransferStats,
    HashVerificationRequest,
    HashVerificationResponse
)
from app.services.fee_service import FeeService
from app.services.blockchain_verification import blockchain_verification_service
from pydantic import BaseModel, Field
from app.schemas.base import BaseResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class PaginatedTransfersResponse(BaseModel):
    transfers: List[TransferResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


@router.post("/", response_model=BaseResponse[TransferResponse])
async def create_transfer(
    transfer_data: TransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new transfer request with dynamic fee calculation"""

    # Validate amount limits
    if transfer_data.amount < Decimal(str(settings.MINIMUM_TRANSFER_AMOUNT)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum transfer amount is ${settings.MINIMUM_TRANSFER_AMOUNT}"
        )

    if transfer_data.amount > Decimal(str(settings.MAXIMUM_TRANSFER_AMOUNT)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum transfer amount is ${settings.MAXIMUM_TRANSFER_AMOUNT}"
        )

    # Get primary wallet and calculate fees dynamically
    try:
        wallet, fee_percentage = await FeeService.get_wallet_fee_info(db)
        admin_wallet_address = wallet.address
        admin_wallet_id = wallet.id
        network = wallet.network
    except ValueError:
        # Fallback to settings if no wallet found
        fee_percentage = Decimal(str(settings.TRANSFER_FEE_PERCENTAGE * 100))  # Convert to percentage
        admin_wallet_address = settings.ADMIN_WALLET_ADDRESS
        admin_wallet_id = None
        network = "TRC20"

    # Calculate fee and net amount using FeeService
    net_amount, fee_amount = FeeService.calculate_amount_after_fee(transfer_data.amount, fee_percentage)

    # Validate bank accounts total if provided
    if transfer_data.bank_accounts:
        total_bank_amount = sum(Decimal(acc.transfer_amount) for acc in transfer_data.bank_accounts)
        if total_bank_amount > net_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total bank account amounts (${total_bank_amount}) exceed net amount (${net_amount})"
            )

    # Create transfer request with initial status history
    transfer = TransferRequest(
        user_id=current_user.id,
        transfer_type=transfer_data.type,
        type_=transfer_data.type,  # Backward compatibility
        amount=transfer_data.amount,
        fee_amount=fee_amount,
        fee=fee_amount,  # Backward compatibility
        amount_after_fee=net_amount,
        net_amount=net_amount,  # Backward compatibility
        currency=transfer_data.currency,
        deposit_wallet_address=transfer_data.deposit_wallet_address,
        crypto_tx_hash=transfer_data.crypto_tx_hash,
        admin_wallet_address=admin_wallet_address,
        admin_wallet_id=admin_wallet_id,
        network=network,
        bank_account_info=transfer_data.bank_account_info.model_dump() if transfer_data.bank_account_info else None,
        bank_accounts=[acc.model_dump() for acc in transfer_data.bank_accounts] if transfer_data.bank_accounts else None,
        expires_at=datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999),  # Expires end of day
        status_history=[{
            "from_status": None,
            "to_status": "pending",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changed_by": "system",
            "changed_by_name": "System",
            "message": "Transfer request created",
            "admin_remarks": None,
            "internal_notes": None
        }]
    )

    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)

    # Clear any cached status
    try:
        redis_client = await get_redis()
        await redis_client.delete(f"transfer_status:{transfer.id}")
    except Exception:
        pass  # Redis not available

    return BaseResponse.success_response(
        data=transfer,
        message=f"Transfer request created successfully. Fee: ${fee_amount}, Net amount: ${net_amount}"
    )


# Admin endpoints (must be defined before parameterized routes)
@router.get("/admin/pending-count", response_model=BaseResponse[dict])
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_transfers"))
):
    """Get count of pending transfers for sidebar badge"""
    try:
        # Count pending transfers
        count_query = select(func.count(TransferRequest.id)).where(TransferRequest.status == 'pending')
        result = await db.execute(count_query)
        count = result.scalar() or 0
        
        return BaseResponse(
            success=True,
            data={
                "pending_count": count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error getting pending count: {str(e)}")
        return BaseResponse(
            success=False,
            error="Failed to get pending count"
        )

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

@router.get("/admin/all", response_model=BaseResponse[PaginatedTransfersResponse])
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
    base_query = select(TransferRequest).options(selectinload(TransferRequest.user))
    count_query = select(func.count(TransferRequest.id))
    
    # Apply filters to both queries
    if type_filter:
        base_query = base_query.where(TransferRequest.type_ == type_filter)
        count_query = count_query.where(TransferRequest.type_ == type_filter)
    
    if status_filter:
        base_query = base_query.where(TransferRequest.status == status_filter)
        count_query = count_query.where(TransferRequest.status == status_filter)
    
    if search:
        # Search in user email, transaction hash, or transfer ID
        # Use exists() with subquery to avoid interfering with selectinload
        user_email_subquery = select(User.id).where(
            User.id == TransferRequest.user_id,
            User.email.ilike(f"%{search}%")
        ).exists()
        
        search_condition = or_(
            user_email_subquery,
            TransferRequest.crypto_tx_hash.ilike(f"%{search}%"),
            TransferRequest.transfer_id.ilike(f"%{search}%")
        )
        base_query = base_query.where(search_condition)
        count_query = count_query.where(search_condition)
    
    # Get total count
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0
    
    # Get transfers with pagination
    query = base_query.order_by(TransferRequest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    transfers = result.scalars().all()
    
    # Calculate pagination info
    page = (skip // limit) + 1
    total_pages = (total_count + limit - 1) // limit
    has_next = skip + limit < total_count
    has_prev = skip > 0
    
    response_data = PaginatedTransfersResponse(
        transfers=transfers,
        total_count=total_count,
        page=page,
        page_size=limit,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
    
    return BaseResponse.success_response(data=response_data, message="Transfers retrieved successfully")

@router.get("/admin/{transfer_id}", response_model=BaseResponse[TransferResponse])
async def get_transfer_by_id(
    transfer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_transfers"))
):
    """Get transfer by ID (admin only)"""
    result = await db.execute(
        select(TransferRequest)
        .options(selectinload(TransferRequest.user))
        .where(TransferRequest.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    return BaseResponse.success_response(data=transfer, message="Transfer retrieved successfully")

@router.put("/admin/{transfer_id}", response_model=BaseResponse[TransferResponse])
async def update_transfer(
    transfer_id: UUID,
    update_data: TransferUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_approve_transfers"))
):
    """Update transfer request (admin only)"""
    try:
        # Fetch transfer with user info for admin name
        result = await db.execute(
            select(TransferRequest)
            .options(selectinload(TransferRequest.user))
            .where(TransferRequest.id == transfer_id)
        )
        transfer = result.scalar_one_or_none()

        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer not found"
            )

        # Track status changes for history
        old_status = transfer.status
        new_status = update_data.status

        # Initialize status_history as a list if it's None
        if transfer.status_history is None:
            transfer.status_history = []

        # Update status history if status is changing
        if new_status and new_status != old_status:
            # Create new history entry with proper structure
            history_entry = {
                "from_status": old_status,
                "to_status": new_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "changed_by": str(current_admin.id),
                "changed_by_name": f"{current_admin.first_name} {current_admin.last_name}".strip(),
                "message": update_data.status_message or f"Status changed from {old_status} to {new_status}",
                "admin_remarks": update_data.admin_remarks,
                "internal_notes": update_data.internal_notes
            }
            
            # Create a new list to ensure SQLAlchemy detects the change
            current_history = list(transfer.status_history) if transfer.status_history else []
            current_history.append(history_entry)
            transfer.status_history = current_history

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(transfer, field) and value is not None:
                setattr(transfer, field, value)

        # Set processed_by and completion time for status changes
        if new_status and new_status != old_status:
            transfer.processed_by = current_admin.id
            if new_status == "completed":
                transfer.completed_at = datetime.now(timezone.utc)

        # Update the updated_at timestamp
        transfer.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(transfer)

        # Clear cache
        try:
            redis_client = await get_redis()
            await redis_client.delete(f"transfer_status:{transfer.id}")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")

        logger.info(f"Transfer {transfer_id} updated by admin {current_admin.id}. Status: {old_status} -> {new_status}")
        
        return BaseResponse.success_response(data=transfer, message="Transfer updated successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transfer {transfer_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating transfer"
        )

# User endpoints (parameterized routes come after specific admin routes)
@router.get("/", response_model=BaseResponse[PaginatedTransfersResponse])
async def get_user_transfers(
    skip: int = 0,
    limit: int = 20,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's transfer requests with pagination"""
    base_query = select(TransferRequest).where(TransferRequest.user_id == current_user.id)

    if type_filter:
        base_query = base_query.where(TransferRequest.type_ == type_filter)

    if status_filter:
        base_query = base_query.where(TransferRequest.status == status_filter)

    # Get total count
    count_query = select(func.count(TransferRequest.id)).where(TransferRequest.user_id == current_user.id)
    if type_filter:
        count_query = count_query.where(TransferRequest.type_ == type_filter)
    if status_filter:
        count_query = count_query.where(TransferRequest.status == status_filter)

    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    # Get transfers with pagination
    query = base_query.order_by(TransferRequest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    transfers = result.scalars().all()

    # Calculate pagination info
    page = (skip // limit) + 1
    total_pages = (total_count + limit - 1) // limit
    has_next = skip + limit < total_count
    has_prev = skip > 0

    response_data = PaginatedTransfersResponse(
        transfers=transfers,
        total_count=total_count,
        page=page,
        page_size=limit,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )

    return BaseResponse.success_response(data=response_data, message="Transfers retrieved successfully")


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
            cached_data = json.loads(cached_status)
            return BaseResponse.success_response(data=cached_data, message="Transfer status retrieved successfully")
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


@router.get("/fee-info", response_model=BaseResponse[dict])
async def get_fee_info(
    amount: Optional[Decimal] = None,
    wallet_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current fee information for transfers"""
    try:
        if amount and amount > 0:
            # Calculate fees for specific amount
            fee_info = await FeeService.calculate_crypto_transfer_fee(db, amount, wallet_id)
            return BaseResponse.success_response(data=fee_info, message="Fee calculation completed")
        else:
            # Get general fee information
            wallet, fee_percentage = await FeeService.get_wallet_fee_info(db, wallet_id)
            fee_info = {
                "wallet": {
                    "id": str(wallet.id),
                    "name": wallet.name,
                    "address": wallet.address,
                    "currency": wallet.currency,
                    "network": wallet.network
                },
                "fee_percentage": float(fee_percentage),
                "minimum_amount": float(settings.MINIMUM_TRANSFER_AMOUNT),
                "maximum_amount": float(settings.MAXIMUM_TRANSFER_AMOUNT)
            }
            return BaseResponse.success_response(data=fee_info, message="Fee information retrieved")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/verify-hash", response_model=BaseResponse[HashVerificationResponse])
async def verify_transaction_hash(
    verification_data: HashVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify transaction hash on blockchain with real verification"""
    # Input validation
    if len(verification_data.transaction_hash) < 20:
        return invalid_response("Invalid transaction hash format", verification_data.network)

    if len(verification_data.wallet_address) < 20:
        return invalid_response("Invalid wallet address", verification_data.network)

    # Real blockchain verification
    verification_response = await blockchain_verification_service.verify_transaction(
        verification_data, db
    )
    return BaseResponse.success_response(
        data=verification_response,
        message="Hash verification completed"
    )

def invalid_response(message: str, network: str) -> BaseResponse:
    return BaseResponse.success_response(
        data=HashVerificationResponse(
            is_valid=False,
            confirmations=0,
            amount=Decimal('0'),
            message=message,
            network=network
        ),
        message="Validation failed"
    )
@router.post("/bulk-update-status", response_model=BaseResponse[dict])
async def bulk_update_transfer_status(
    transfer_ids: List[UUID],
    status: str,
    status_message: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_approve_transfers"))
):
    """Bulk update transfer status (admin only)"""

    # Validate status
    valid_statuses = ['pending', 'processing', 'completed', 'failed', 'cancelled']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    # Get transfers
    result = await db.execute(
        select(TransferRequest).where(TransferRequest.id.in_(transfer_ids))
    )
    transfers = result.scalars().all()

    if not transfers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transfers found with provided IDs"
        )

    # Update transfers
    updated_count = 0
    for transfer in transfers:
        transfer.status = status
        if status_message:
            transfer.status_message = status_message
        transfer.processed_by = current_admin.id
        if status == "completed":
            transfer.completed_at = datetime.now(timezone.utc)
        updated_count += 1

    await db.commit()

    # Clear cache for updated transfers
    try:
        redis_client = await get_redis()
        for transfer_id in transfer_ids:
            await redis_client.delete(f"transfer_status:{transfer_id}")
    except Exception:
        pass  # Redis not available

    return BaseResponse.success_response(
        data={"updated_count": updated_count, "status": status},
        message=f"Successfully updated {updated_count} transfers to {status}"
    )




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



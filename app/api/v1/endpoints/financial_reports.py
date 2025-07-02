from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import io
import tempfile
import os

from app.api.deps import check_admin_permission
from app.db.database import get_db
from app.models.transfer import TransferRequest
from app.models.user import User
from app.schemas.base import BaseResponse

router = APIRouter()


@router.get("/financial", response_model=BaseResponse[dict])
async def get_financial_report(
    start_date: str,
    end_date: str,
    group_by: str = "day",
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_reports"))
):
    """Get financial report for specified date range"""
    
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)."
        )
    
    if start_dt >= end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date."
        )
    
    # Base query for the period
    base_query = select(TransferRequest).where(
        and_(
            TransferRequest.created_at >= start_dt,
            TransferRequest.created_at <= end_dt
        )
    )
    
    # Get overall statistics
    stats_result = await db.execute(
        select(
            func.count(TransferRequest.id).label("total_transfers"),
            func.count().filter(TransferRequest.status == "completed").label("completed_transfers"),
            func.count().filter(TransferRequest.status == "failed").label("failed_transfers"),
            func.sum(TransferRequest.amount).label("total_volume"),
            func.sum(TransferRequest.fee).label("total_fees"),
            func.avg(TransferRequest.amount).label("average_amount")
        ).where(
            and_(
                TransferRequest.created_at >= start_dt,
                TransferRequest.created_at <= end_dt
            )
        )
    )
    stats = stats_result.first()
    
    # Group by logic
    if group_by == "day":
        date_trunc = func.date(TransferRequest.created_at)
    elif group_by == "week":
        date_trunc = func.date_trunc('week', TransferRequest.created_at)
    elif group_by == "month":
        date_trunc = func.date_trunc('month', TransferRequest.created_at)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid group_by value. Use 'day', 'week', or 'month'."
        )
    
    # Get revenue by period
    revenue_result = await db.execute(
        select(
            date_trunc.label("period"),
            func.sum(TransferRequest.amount).label("volume"),
            func.sum(TransferRequest.fee).label("fees"),
            func.count(TransferRequest.id).label("transfers"),
            func.count().filter(TransferRequest.status == "completed").label("completed"),
            func.count().filter(TransferRequest.status == "failed").label("failed")
        ).where(
            and_(
                TransferRequest.created_at >= start_dt,
                TransferRequest.created_at <= end_dt
            )
        ).group_by(date_trunc).order_by(date_trunc)
    )
    
    revenue_by_period = []
    for row in revenue_result.fetchall():
        revenue_by_period.append({
            "date": row.period.isoformat() if row.period else None,
            "volume": float(row.volume or 0),
            "fees": float(row.fees or 0),
            "transfers": row.transfers or 0,
            "completed": row.completed or 0,
            "failed": row.failed or 0
        })
    
    # Get transfer type breakdown
    type_result = await db.execute(
        select(
            TransferRequest.type_,
            func.count(TransferRequest.id).label("count"),
            func.sum(TransferRequest.amount).label("volume"),
            func.sum(TransferRequest.fee).label("fees")
        ).where(
            and_(
                TransferRequest.created_at >= start_dt,
                TransferRequest.created_at <= end_dt
            )
        ).group_by(TransferRequest.type_)
    )
    
    type_breakdown = []
    for row in type_result.fetchall():
        type_breakdown.append({
            "type": row.type_,
            "count": row.count or 0,
            "volume": float(row.volume or 0),
            "fees": float(row.fees or 0)
        })
    
    # Get status breakdown
    status_result = await db.execute(
        select(
            TransferRequest.status,
            func.count(TransferRequest.id).label("count"),
            func.sum(TransferRequest.amount).label("volume")
        ).where(
            and_(
                TransferRequest.created_at >= start_dt,
                TransferRequest.created_at <= end_dt
            )
        ).group_by(TransferRequest.status)
    )
    
    status_breakdown = []
    for row in status_result.fetchall():
        status_breakdown.append({
            "status": row.status,
            "count": row.count or 0,
            "volume": float(row.volume or 0)
        })
    
    # Get top customers by volume
    customer_result = await db.execute(
        select(
            User.first_name,
            User.last_name,
            User.email,
            func.count(TransferRequest.id).label("transfer_count"),
            func.sum(TransferRequest.amount).label("total_volume"),
            func.sum(TransferRequest.fee).label("total_fees")
        ).join(User, TransferRequest.user_id == User.id).where(
            and_(
                TransferRequest.created_at >= start_dt,
                TransferRequest.created_at <= end_dt
            )
        ).group_by(User.id, User.first_name, User.last_name, User.email).order_by(
            func.sum(TransferRequest.amount).desc()
        ).limit(10)
    )
    
    top_customers = []
    for row in customer_result.fetchall():
        top_customers.append({
            "customer_name": f"{row.first_name} {row.last_name}",
            "customer_email": row.email,
            "transfer_count": row.transfer_count or 0,
            "total_volume": float(row.total_volume or 0),
            "total_fees": float(row.total_fees or 0)
        })
    
    return BaseResponse.success_response(
        data={
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "group_by": group_by
            },
            "summary": {
                "total_transfers": stats.total_transfers or 0,
                "completed_transfers": stats.completed_transfers or 0,
                "failed_transfers": stats.failed_transfers or 0,
                "total_volume": float(stats.total_volume or 0),
                "total_fees": float(stats.total_fees or 0),
                "average_transfer_amount": float(stats.average_amount or 0)
            },
            "revenue_by_period": revenue_by_period,
            "type_breakdown": type_breakdown,
            "status_breakdown": status_breakdown,
            "top_customers": top_customers
        },
        message="Financial report generated successfully"
    )


@router.post("/financial/export", response_model=BaseResponse[dict])
async def export_financial_report(
    start_date: str,
    end_date: str,
    format: str = "csv",
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(check_admin_permission("can_view_reports"))
):
    """Export financial report to CSV or Excel"""
    
    if format not in ["csv", "xlsx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Use 'csv' or 'xlsx'."
        )
    
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)."
        )
    
    # Get all transfers in the period
    result = await db.execute(
        select(TransferRequest).join(User, TransferRequest.user_id == User.id).where(
            and_(
                TransferRequest.created_at >= start_dt,
                TransferRequest.created_at <= end_dt
            )
        ).order_by(TransferRequest.created_at.desc())
    )
    transfers = result.scalars().all()
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format}')
    
    if format == "csv":
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Transfer ID', 'User Email', 'User Name', 'Type', 'Amount', 'Fee', 
            'Net Amount', 'Status', 'Created At', 'Completed At'
        ])
        
        # Write data
        for transfer in transfers:
            writer.writerow([
                transfer.transfer_id,
                transfer.user.email if transfer.user else '',
                f"{transfer.user.first_name} {transfer.user.last_name}" if transfer.user else '',
                transfer.type_,
                str(transfer.amount),
                str(transfer.fee),
                str(transfer.net_amount),
                transfer.status,
                transfer.created_at.isoformat(),
                transfer.completed_at.isoformat() if transfer.completed_at else ''
            ])
        
        # Write to file
        with open(temp_file.name, 'w', newline='', encoding='utf-8') as f:
            f.write(output.getvalue())
    
    # For now, return the file path (in production, you'd upload to S3 or similar)
    download_url = f"/api/v1/admin/reports/download/{os.path.basename(temp_file.name)}"
    
    return BaseResponse.success_response(
        data={
            "download_url": download_url,
            "filename": f"financial_report_{start_date}_to_{end_date}.{format}",
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        },
        message="Financial report export prepared successfully"
    )

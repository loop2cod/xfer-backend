from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, timezone

from app.models.user import User
from app.models.transfer import TransferRequest
from app.models.admin_wallet import AdminWallet
from app.models.admin_bank_account import AdminBankAccount
from app.services.fee_service import FeeService
from app.services.email import email_service


class PurchaseService:
    """Service to handle crypto purchase transactions"""
    
    @staticmethod
    async def create_crypto_purchase(
        db: AsyncSession,
        user: User,
        amount: Decimal,
        recipient_wallet: str,
        wallet_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a crypto purchase transaction
        
        Args:
            db: Database session
            user: User making the purchase
            amount: Amount in USD
            recipient_wallet: User's wallet address to receive crypto
            wallet_id: Specific admin wallet ID (optional)
        
        Returns:
            Transaction details with fee information
        """
        
        # Get wallet and calculate fees
        fee_info = await FeeService.calculate_crypto_payment_fee(
            db=db,
            amount=amount,
            wallet_id=wallet_id
        )
        
        # Create transfer request
        transfer_data = {
            "id": str(uuid4()),
            "user_id": str(user.id),
            "transfer_type": "crypto_purchase",
            "amount": float(amount),
            "fee_amount": fee_info["fee_amount"],
            "amount_after_fee": fee_info["amount_after_fee"],
            "currency": fee_info["currency"],
            "recipient_wallet": recipient_wallet,
            "admin_wallet_id": fee_info["wallet"]["id"],
            "admin_wallet_address": fee_info["wallet"]["address"],
            "network": fee_info["wallet"]["network"],
            "status": "pending",
            "payment_method": "crypto",
            "notes": f"Crypto purchase via {fee_info['wallet']['network']} network"
        }
        
        transfer = TransferRequest(**transfer_data)
        db.add(transfer)
        await db.commit()
        await db.refresh(transfer)
        
        # Send notification email
        try:
            text_content = f"""
                Your crypto purchase order has been created successfully.
                
                Order Details:
                - Amount: ${amount} USD
                - Fee: ${fee_info['fee_amount']} USD ({fee_info['fee_percentage']}%)
                - You'll receive: {fee_info['amount_after_fee']} {fee_info['currency']}
                - Your wallet: {recipient_wallet}
                - Payment to: {fee_info['wallet']['address']} ({fee_info['wallet']['network']})
                
                Please send the payment to complete your order.
                """
            
            html_content = f"""
                <h2>Crypto Purchase Order Created</h2>
                <p>Your crypto purchase order has been created successfully.</p>
                
                <h3>Order Details:</h3>
                <ul>
                    <li><strong>Amount:</strong> ${amount} USD</li>
                    <li><strong>Fee:</strong> ${fee_info['fee_amount']} USD ({fee_info['fee_percentage']}%)</li>
                    <li><strong>You'll receive:</strong> {fee_info['amount_after_fee']} {fee_info['currency']}</li>
                    <li><strong>Your wallet:</strong> {recipient_wallet}</li>
                    <li><strong>Payment to:</strong> {fee_info['wallet']['address']} ({fee_info['wallet']['network']})</li>
                </ul>
                
                <p><strong>Please send the payment to complete your order.</strong></p>
                """
            
            await email_service.send_email(
                to_email=user.email,
                subject="Crypto Purchase Order Created",
                html_content=html_content,
                text_content=text_content
            )
        except Exception as e:
            print(f"Failed to send email notification: {e}")
        
        return {
            "transfer": transfer,
            "fee_info": fee_info,
            "status": "created"
        }
    
    @staticmethod
    async def create_bank_purchase(
        db: AsyncSession,
        user: User,
        amount: Decimal,
        recipient_wallet: str,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a bank purchase transaction
        
        Args:
            db: Database session
            user: User making the purchase
            amount: Amount in USD
            recipient_wallet: User's wallet address to receive crypto
            account_id: Specific admin bank account ID (optional)
        
        Returns:
            Transaction details with fee information
        """
        
        # Get bank account and calculate fees
        fee_info = await FeeService.calculate_bank_purchase_fee(
            db=db,
            amount=amount,
            account_id=account_id
        )
        
        # Create transfer request
        transfer_data = {
            "id": str(uuid4()),
            "user_id": str(user.id),
            "transfer_type": "bank_purchase",
            "amount": float(amount),
            "fee_amount": fee_info["fee_amount"],
            "amount_after_fee": fee_info["amount_after_fee"],
            "currency": "USD",  # Bank purchases are in USD
            "recipient_wallet": recipient_wallet,
            "admin_bank_account_id": fee_info["bank_account"]["id"],
            "status": "pending",
            "payment_method": "bank_transfer",
            "notes": f"Bank purchase via {fee_info['bank_account']['bank_name']}"
        }
        
        transfer = TransferRequest(**transfer_data)
        db.add(transfer)
        await db.commit()
        await db.refresh(transfer)
        
        # Send notification email
        try:
            text_content = f"""
                Your bank purchase order has been created successfully.
                
                Order Details:
                - Amount: ${amount} USD
                - Fee: ${fee_info['fee_amount']} USD ({fee_info['fee_percentage']}%)
                - You'll receive: ${fee_info['amount_after_fee']} worth of crypto
                - Your wallet: {recipient_wallet}
                - Bank: {fee_info['bank_account']['bank_name']}
                
                Please complete the bank transfer to process your order.
                """
            
            html_content = f"""
                <h2>Bank Purchase Order Created</h2>
                <p>Your bank purchase order has been created successfully.</p>
                
                <h3>Order Details:</h3>
                <ul>
                    <li><strong>Amount:</strong> ${amount} USD</li>
                    <li><strong>Fee:</strong> ${fee_info['fee_amount']} USD ({fee_info['fee_percentage']}%)</li>
                    <li><strong>You'll receive:</strong> ${fee_info['amount_after_fee']} worth of crypto</li>
                    <li><strong>Your wallet:</strong> {recipient_wallet}</li>
                    <li><strong>Bank:</strong> {fee_info['bank_account']['bank_name']}</li>
                </ul>
                
                <p><strong>Please complete the bank transfer to process your order.</strong></p>
                """
            
            await email_service.send_email(
                to_email=user.email,
                subject="Bank Purchase Order Created",
                html_content=html_content,
                text_content=text_content
            )
        except Exception as e:
            print(f"Failed to send email notification: {e}")
        
        return {
            "transfer": transfer,
            "fee_info": fee_info,
            "status": "created"
        }
    
    @staticmethod
    async def get_user_purchases(
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> list:
        """Get user's purchase history"""
        query = (
            select(TransferRequest)
            .where(
                TransferRequest.user_id == user_id,
                TransferRequest.transfer_type.in_(["crypto_purchase", "bank_purchase"])
            )
            .order_by(TransferRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def update_purchase_status(
        db: AsyncSession,
        transfer_id: str,
        status: str,
        admin_notes: Optional[str] = None
    ) -> Optional[TransferRequest]:
        """Update purchase status (admin only)"""
        result = await db.execute(
            select(TransferRequest).where(TransferRequest.id == transfer_id)
        )
        transfer = result.scalar_one_or_none()
        
        if not transfer:
            return None
        
        transfer.status = status
        transfer.updated_at = datetime.now(timezone.utc)
        
        if admin_notes:
            current_notes = transfer.notes or ""
            transfer.notes = f"{current_notes}\n[Admin] {admin_notes}" if current_notes else f"[Admin] {admin_notes}"
        
        await db.commit()
        await db.refresh(transfer)
        
        # Send status update email
        if transfer.user:
            try:
                text_content = f"""
                    Your purchase order status has been updated.
                    
                    Order ID: {transfer_id}
                    New Status: {status.title()}
                    Amount: ${transfer.amount} USD
                    
                    {admin_notes if admin_notes else ''}
                    """
                
                html_content = f"""
                    <h2>Purchase Order Status Update</h2>
                    <p>Your purchase order status has been updated.</p>
                    
                    <ul>
                        <li><strong>Order ID:</strong> {transfer_id}</li>
                        <li><strong>New Status:</strong> {status.title()}</li>
                        <li><strong>Amount:</strong> ${transfer.amount} USD</li>
                    </ul>
                    
                    {f'<p><strong>Admin Notes:</strong> {admin_notes}</p>' if admin_notes else ''}
                    """
                
                await email_service.send_email(
                    to_email=transfer.user.email,
                    subject=f"Purchase Order Status Update - {status.title()}",
                    html_content=html_content,
                    text_content=text_content
                )
            except Exception as e:
                print(f"Failed to send status update email: {e}")
        
        return transfer
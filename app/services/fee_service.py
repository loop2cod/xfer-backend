from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.admin_wallet import AdminWallet
from app.models.admin_bank_account import AdminBankAccount


class FeeService:
    """Service to handle fee calculations for transactions"""
    
    @staticmethod
    def calculate_fee_amount(amount: Decimal, fee_percentage: Decimal) -> Decimal:
        """
        Calculate the fee amount based on the percentage
        
        Args:
            amount: The original amount
            fee_percentage: The fee percentage (e.g., 1.5 for 1.5%)
        
        Returns:
            The fee amount
        """
        if fee_percentage <= 0:
            return Decimal('0')
        
        fee_amount = (amount * fee_percentage / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return fee_amount
    
    @staticmethod
    def calculate_amount_after_fee(amount: Decimal, fee_percentage: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Calculate the amount after deducting the fee
        
        Args:
            amount: The original amount
            fee_percentage: The fee percentage (e.g., 1.5 for 1.5%)
        
        Returns:
            Tuple of (amount_after_fee, fee_amount)
        """
        fee_amount = FeeService.calculate_fee_amount(amount, fee_percentage)
        amount_after_fee = amount - fee_amount
        
        return amount_after_fee, fee_amount
    
    @staticmethod
    def calculate_amount_with_fee(net_amount: Decimal, fee_percentage: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Calculate the total amount including fee (reverse calculation)
        
        Args:
            net_amount: The desired net amount after fee
            fee_percentage: The fee percentage (e.g., 1.5 for 1.5%)
        
        Returns:
            Tuple of (total_amount, fee_amount)
        """
        if fee_percentage <= 0:
            return net_amount, Decimal('0')
        
        # Formula: net_amount = total_amount - (total_amount * fee_percentage / 100)
        # Solving for total_amount: total_amount = net_amount / (1 - fee_percentage/100)
        fee_multiplier = Decimal('1') - (fee_percentage / Decimal('100'))
        total_amount = (net_amount / fee_multiplier).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        fee_amount = total_amount - net_amount
        
        return total_amount, fee_amount
    
    @staticmethod
    async def get_wallet_fee_info(db: AsyncSession, wallet_id: Optional[str] = None) -> Tuple[AdminWallet, Decimal]:
        """
        Get wallet and its fee percentage
        
        Args:
            db: Database session
            wallet_id: Specific wallet ID, if None gets primary wallet
        
        Returns:
            Tuple of (wallet, fee_percentage)
        """
        if wallet_id:
            result = await db.execute(
                select(AdminWallet).where(
                    AdminWallet.id == wallet_id,
                    AdminWallet.is_active == True
                )
            )
        else:
            result = await db.execute(
                select(AdminWallet).where(
                    AdminWallet.is_primary == True,
                    AdminWallet.is_active == True
                )
            )
        
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise ValueError("Wallet not found or not active")
        
        return wallet, wallet.fee_percentage
    
    @staticmethod
    async def get_bank_account_fee_info(db: AsyncSession, account_id: Optional[str] = None) -> Tuple[AdminBankAccount, Decimal]:
        """
        Get bank account and its fee percentage
        
        Args:
            db: Database session
            account_id: Specific account ID, if None gets primary account
        
        Returns:
            Tuple of (account, fee_percentage)
        """
        if account_id:
            result = await db.execute(
                select(AdminBankAccount).where(
                    AdminBankAccount.id == account_id,
                    AdminBankAccount.is_active == True
                )
            )
        else:
            result = await db.execute(
                select(AdminBankAccount).where(
                    AdminBankAccount.is_primary == True,
                    AdminBankAccount.is_active == True
                )
            )
        
        account = result.scalar_one_or_none()
        if not account:
            raise ValueError("Bank account not found or not active")
        
        return account, account.fee_percentage
    
    @staticmethod
    async def calculate_crypto_payment_fee(
        db: AsyncSession, 
        amount: Decimal, 
        wallet_id: Optional[str] = None
    ) -> dict:
        """
        Calculate fee for crypto payment
        
        Args:
            db: Database session
            amount: Payment amount
            wallet_id: Specific wallet ID, if None uses primary wallet
        
        Returns:
            Dict with fee calculation details
        """
        wallet, fee_percentage = await FeeService.get_wallet_fee_info(db, wallet_id)
        amount_after_fee, fee_amount = FeeService.calculate_amount_after_fee(amount, fee_percentage)
        
        return {
            "wallet": {
                "id": str(wallet.id),
                "name": wallet.name,
                "address": wallet.address,
                "currency": wallet.currency,
                "network": wallet.network
            },
            "original_amount": float(amount),
            "fee_percentage": float(fee_percentage),
            "fee_amount": float(fee_amount),
            "amount_after_fee": float(amount_after_fee),
            "currency": wallet.currency
        }
    
    @staticmethod
    async def calculate_bank_purchase_fee(
        db: AsyncSession, 
        amount: Decimal, 
        account_id: Optional[str] = None
    ) -> dict:
        """
        Calculate fee for crypto purchase via bank account
        
        Args:
            db: Database session
            amount: Purchase amount
            account_id: Specific account ID, if None uses primary account
        
        Returns:
            Dict with fee calculation details
        """
        account, fee_percentage = await FeeService.get_bank_account_fee_info(db, account_id)
        amount_after_fee, fee_amount = FeeService.calculate_amount_after_fee(amount, fee_percentage)
        
        return {
            "bank_account": {
                "id": str(account.id),
                "name": account.name,
                "bank_name": account.bank_name,
                "account_type": account.account_type
            },
            "original_amount": float(amount),
            "fee_percentage": float(fee_percentage),
            "fee_amount": float(fee_amount),
            "amount_after_fee": float(amount_after_fee),
            "currency": "USD"  # Assuming USD for bank transactions
        }
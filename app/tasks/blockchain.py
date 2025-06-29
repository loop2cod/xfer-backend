from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional
import asyncio
import logging
from datetime import datetime, timedelta
import json

from app.worker import celery_app
from app.db.database import AsyncSessionLocal, redis_client
from app.models.transfer import TransferRequest
from app.models.wallet import Wallet
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_tron_client():
    """Get TRON client for blockchain operations"""
    try:
        # from tronapi import Tron
        # tron = Tron(
        #     full_node='https://api.trongrid.io',
        #     solidity_node='https://api.trongrid.io',
        #     event_server='https://api.trongrid.io'
        # )
        # if settings.TRON_GRID_API_KEY:
        #     tron.set_api_key(settings.TRON_GRID_API_KEY)
        # return tron
        logger.info("TRON client not available - blockchain dependencies not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize TRON client: {e}")
        return None


@celery_app.task(bind=True, name="app.tasks.blockchain.monitor_transaction")
def monitor_transaction(self, transfer_id: str, tx_hash: str):
    """Monitor specific transaction for confirmations"""
    return asyncio.run(_monitor_transaction_async(transfer_id, tx_hash))


async def _monitor_transaction_async(transfer_id: str, tx_hash: str):
    """Async function to monitor transaction"""
    async with AsyncSessionLocal() as db:
        try:
            # Get transfer request
            result = await db.execute(
                select(TransferRequest).where(TransferRequest.id == transfer_id)
            )
            transfer = result.scalar_one_or_none()
            
            if not transfer:
                logger.error(f"Transfer {transfer_id} not found")
                return {"status": "error", "message": "Transfer not found"}
            
            # Get TRON client
            tron = await get_tron_client()
            if not tron:
                return {"status": "error", "message": "TRON client not available"}
            
            # Get transaction info
            tx_info = tron.trx.get_transaction_info(tx_hash)
            
            if not tx_info or 'blockNumber' not in tx_info:
                logger.warning(f"Transaction {tx_hash} not found on blockchain")
                return {"status": "pending", "message": "Transaction not confirmed yet"}
            
            # Get current block number
            current_block = tron.trx.get_block()['block_header']['raw_data']['number']
            confirmations = current_block - tx_info['blockNumber']
            
            # Update transfer with confirmation count
            transfer.confirmation_count = confirmations
            
            # Check if transaction is successful
            if tx_info.get('receipt', {}).get('result') == 'SUCCESS':
                if confirmations >= transfer.required_confirmations:
                    transfer.status = "completed"
                    transfer.status_message = f"Transaction confirmed with {confirmations} confirmations"
                    transfer.completed_at = func.now()
                else:
                    transfer.status = "processing"
                    transfer.status_message = f"Waiting for confirmations ({confirmations}/{transfer.required_confirmations})"
            else:
                transfer.status = "failed"
                transfer.status_message = "Transaction failed on blockchain"
            
            await db.commit()
            
            # Update cache
            await _update_transfer_cache(transfer_id, transfer.status, transfer.status_message, confirmations)
            
            return {
                "status": "success",
                "transfer_status": transfer.status,
                "confirmations": confirmations,
                "required_confirmations": transfer.required_confirmations
            }
            
        except Exception as e:
            logger.error(f"Error monitoring transaction {tx_hash}: {e}")
            await db.rollback()
            return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.blockchain.monitor_pending_transactions")
def monitor_pending_transactions():
    """Monitor all pending transactions"""
    return asyncio.run(_monitor_pending_transactions_async())


async def _monitor_pending_transactions_async():
    """Monitor all pending transactions"""
    async with AsyncSessionLocal() as db:
        try:
            # Get all pending/processing transfers with tx_hash
            result = await db.execute(
                select(TransferRequest).where(
                    and_(
                        TransferRequest.status.in_(["pending", "processing"]),
                        TransferRequest.crypto_tx_hash.isnot(None)
                    )
                )
            )
            transfers = result.scalars().all()
            
            logger.info(f"Monitoring {len(transfers)} pending transactions")
            
            processed = 0
            for transfer in transfers:
                try:
                    await _monitor_transaction_async(str(transfer.id), transfer.crypto_tx_hash)
                    processed += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing transfer {transfer.id}: {e}")
                    continue
            
            return {"status": "success", "processed": processed, "total": len(transfers)}
            
        except Exception as e:
            logger.error(f"Error in monitor_pending_transactions: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.blockchain.cleanup_expired_transfers")
def cleanup_expired_transfers():
    """Cleanup expired transfer requests"""
    return asyncio.run(_cleanup_expired_transfers_async())


async def _cleanup_expired_transfers_async():
    """Cleanup expired transfers"""
    async with AsyncSessionLocal() as db:
        try:
            # Mark transfers as expired if they're older than 24 hours and still pending
            expiry_time = datetime.utcnow() - timedelta(hours=24)
            
            result = await db.execute(
                select(TransferRequest).where(
                    and_(
                        TransferRequest.status == "pending",
                        TransferRequest.created_at < expiry_time,
                        TransferRequest.crypto_tx_hash.is_(None)  # No transaction hash provided
                    )
                )
            )
            expired_transfers = result.scalars().all()
            
            expired_count = 0
            for transfer in expired_transfers:
                transfer.status = "failed"
                transfer.status_message = "Transfer expired - no transaction provided within 24 hours"
                expired_count += 1
            
            await db.commit()
            
            logger.info(f"Marked {expired_count} transfers as expired")
            return {"status": "success", "expired_count": expired_count}
            
        except Exception as e:
            logger.error(f"Error in cleanup_expired_transfers: {e}")
            await db.rollback()
            return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.blockchain.update_wallet_balances")
def update_wallet_balances():
    """Update wallet balances from blockchain"""
    return asyncio.run(_update_wallet_balances_async())


async def _update_wallet_balances_async():
    """Update wallet balances"""
    async with AsyncSessionLocal() as db:
        try:
            # Get all active wallets
            result = await db.execute(
                select(Wallet).where(Wallet.is_active == True)
            )
            wallets = result.scalars().all()
            
            tron = await get_tron_client()
            if not tron:
                return {"status": "error", "message": "TRON client not available"}
            
            updated = 0
            for wallet in wallets:
                try:
                    if wallet.currency == "USDT" and wallet.network == "TRC20":
                        # Get USDT balance on TRON
                        balance = await _get_usdt_balance_tron(tron, wallet.address)
                        
                        if balance is not None and balance != wallet.balance:
                            wallet.balance = balance
                            wallet.last_activity_at = func.now()
                            updated += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error updating wallet {wallet.address}: {e}")
                    continue
            
            await db.commit()
            
            logger.info(f"Updated {updated} wallet balances")
            return {"status": "success", "updated": updated, "total": len(wallets)}
            
        except Exception as e:
            logger.error(f"Error in update_wallet_balances: {e}")
            await db.rollback()
            return {"status": "error", "message": str(e)}


async def _get_usdt_balance_tron(tron, address: str) -> Optional[float]:
    """Get USDT balance for TRON address"""
    try:
        # USDT TRC20 contract address
        usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
        # Get balance using TronGrid API
        balance_info = tron.trx.get_account_balance(address)
        
        # For TRC20 tokens, we need to call the contract
        # This is a simplified version - in production, you'd use proper contract calls
        return 0.0  # Placeholder
        
    except Exception as e:
        logger.error(f"Error getting USDT balance for {address}: {e}")
        return None


async def _update_transfer_cache(transfer_id: str, status: str, status_message: str, confirmations: int):
    """Update transfer status in Redis cache"""
    try:
        cache_data = {
            "status": status,
            "status_message": status_message,
            "confirmation_count": confirmations
        }
        await redis_client.setex(
            f"transfer_status:{transfer_id}",
            300,  # 5 minutes
            json.dumps(cache_data)
        )
    except Exception as e:
        logger.error(f"Error updating cache for transfer {transfer_id}: {e}")
"""
Blockchain verification service for TRC20, ERC20, and BEP20 networks
"""
import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.admin_wallet import AdminWallet
from app.schemas.transfer import HashVerificationRequest, HashVerificationResponse

logger = logging.getLogger(__name__)

# Token contract addresses
USDT_CONTRACTS = {
    "TRC20": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # USDT on TRON
    "ERC20": "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT on Ethereum
    "BEP20": "0x55d398326f99059fF775485246999027B3197955",  # USDT on BSC
}

# Token decimals
TOKEN_DECIMALS = {
    "USDT": 6,  # USDT has 6 decimals
    "BNB": 18,  # BNB has 18 decimals
    "ETH": 18,  # ETH has 18 decimals
}

# Network configurations
NETWORK_CONFIGS = {
    "TRC20": {
        "api_url": "https://api.trongrid.io",
        "explorer_url": "https://tronscan.org",
        "required_confirmations": 19,
    },
    "ERC20": {
        "api_url": f"https://mainnet.infura.io/v3/{settings.INFURA_PROJECT_ID}",
        "explorer_url": "https://etherscan.io",
        "required_confirmations": 12,
    },
    "BEP20": {
        "api_url": settings.BSC_RPC_URL or "https://bsc-dataseed.binance.org/",
        "explorer_url": "https://bscscan.com",
        "required_confirmations": 15,
    },
}


class BlockchainVerificationService:
    """Service for verifying blockchain transactions"""

    def __init__(self):
        self.timeout = 30  # seconds
        self.tolerance = Decimal("0.01")  # 0.01 tolerance for amount validation

    async def verify_transaction(
        self, 
        verification_data: HashVerificationRequest,
        db: AsyncSession
    ) -> HashVerificationResponse:
        """
        Verify transaction hash on blockchain
        """
        try:
            # Get admin wallet address for verification
            admin_wallet_address = await self._get_admin_wallet_address(db, verification_data.network)
            if not admin_wallet_address:
                return self._create_error_response(
                    "Admin wallet not configured for this network",
                    verification_data.network
                )

            # Validate addresses
            if not self._validate_address_format(verification_data.wallet_address, verification_data.network):
                return self._create_error_response(
                    "Invalid sender wallet address format",
                    verification_data.network
                )

            if not self._validate_address_format(admin_wallet_address, verification_data.network):
                return self._create_error_response(
                    "Invalid admin wallet address format",
                    verification_data.network
                )

            # Verify transaction based on network
            if verification_data.network == "TRC20":
                return await self._verify_trc20_transaction(
                    verification_data, admin_wallet_address
                )
            elif verification_data.network in ["ERC20", "BEP20"]:
                return await self._verify_evm_transaction(
                    verification_data, admin_wallet_address
                )
            else:
                return self._create_error_response(
                    f"Unsupported network: {verification_data.network}",
                    verification_data.network
                )

        except Exception as e:
            logger.error(f"Error verifying transaction {verification_data.transaction_hash}: {str(e)}")
            return self._create_error_response(
                f"Verification failed: {str(e)}",
                verification_data.network
            )

    async def _get_admin_wallet_address(self, db: AsyncSession, network: str) -> Optional[str]:
        """Get admin wallet address for the specified network"""
        try:
            # First try to get from database (primary wallet for the network)
            result = await db.execute(
                select(AdminWallet).where(
                    AdminWallet.network == network,
                    AdminWallet.is_active == True,
                    AdminWallet.is_primary == True
                )
            )
            wallet = result.scalar_one_or_none()
            
            if wallet:
                return wallet.address
            
            # Fallback to any active wallet for the network
            result = await db.execute(
                select(AdminWallet).where(
                    AdminWallet.network == network,
                    AdminWallet.is_active == True
                ).limit(1)
            )
            wallet = result.scalar_one_or_none()
            
            if wallet:
                return wallet.address
            
            # Final fallback to settings
            if network == "TRC20":
                return settings.ADMIN_WALLET_ADDRESS
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting admin wallet address: {str(e)}")
            return settings.ADMIN_WALLET_ADDRESS if network == "TRC20" else None

    def _validate_address_format(self, address: str, network: str) -> bool:
        """Validate address format for the given network"""
        if not address:
            return False
            
        if network == "TRC20":
            return address.startswith('T') and len(address) == 34
        elif network in ["ERC20", "BEP20"]:
            return address.startswith('0x') and len(address) == 42
        
        return False

    def _normalize_address(self, address: str, network: str) -> str:
        """Normalize address for comparison"""
        if network in ["ERC20", "BEP20"]:
            # Convert to checksum address for EVM chains
            try:
                from web3 import Web3
                return Web3.to_checksum_address(address.lower())
            except Exception:
                return address.lower()
        
        return address  # TRON addresses are case-sensitive

    async def _verify_trc20_transaction(
        self, 
        verification_data: HashVerificationRequest,
        admin_wallet_address: str
    ) -> HashVerificationResponse:
        """Verify TRC20 transaction using TronGrid API"""
        try:
            from tronpy import Tron
            from tronpy.providers import HTTPProvider
            
            # Initialize Tron client
            provider = HTTPProvider(api_key=settings.TRON_GRID_API_KEY)
            tron = Tron(provider=provider)
            
            # Get transaction info
            tx_info = tron.get_transaction_info(verification_data.transaction_hash)
            
            if not tx_info:
                return self._create_error_response(
                    "Transaction not found on TRON network",
                    verification_data.network
                )
            
            # Get transaction details
            tx_details = tron.get_transaction(verification_data.transaction_hash)
            
            if not tx_details:
                return self._create_error_response(
                    "Transaction details not found",
                    verification_data.network
                )
            
            # Check transaction status
            if tx_info.get('receipt', {}).get('result') != 'SUCCESS':
                return self._create_error_response(
                    "Transaction failed on blockchain",
                    verification_data.network
                )
            
            # Validate transaction details
            validation_result = await self._validate_trc20_transaction(
                tx_details, tx_info, verification_data, admin_wallet_address
            )
            
            if not validation_result["valid"]:
                return self._create_error_response(
                    validation_result["error"],
                    verification_data.network
                )
            
            # Calculate confirmations
            current_block = tron.get_latest_block_number()
            tx_block = tx_info.get('blockNumber', 0)
            confirmations = max(0, current_block - tx_block)
            
            # Get block timestamp
            block_info = tron.get_block(tx_block)
            timestamp = datetime.fromtimestamp(
                block_info.get('block_header', {}).get('raw_data', {}).get('timestamp', 0) / 1000,
                tz=timezone.utc
            )
            
            return HashVerificationResponse(
                is_valid=True,
                confirmations=confirmations,
                amount=validation_result["amount"],
                message=f"Transaction verified successfully on {verification_data.network}",
                network=verification_data.network,
                block_height=tx_block,
                timestamp=timestamp
            )
            
        except ImportError:
            logger.error("TronPy library not installed")
            return self._create_error_response(
                "TronPy library not available",
                verification_data.network
            )
        except Exception as e:
            logger.error(f"Error verifying TRC20 transaction: {str(e)}")
            return self._create_error_response(
                f"TRC20 verification failed: {str(e)}",
                verification_data.network
            )

    async def _validate_trc20_transaction(
        self,
        tx_details: Dict[str, Any],
        tx_info: Dict[str, Any],
        verification_data: HashVerificationRequest,
        admin_wallet_address: str
    ) -> Dict[str, Any]:
        """Validate TRC20 transaction details"""
        try:
            # Get contract transactions from the transaction
            contracts = tx_details.get('raw_data', {}).get('contract', [])
            
            for contract in contracts:
                if contract.get('type') == 'TransferContract':
                    # Direct TRX transfer
                    parameter = contract.get('parameter', {}).get('value', {})
                    
                    # Validate sender
                    from_address = parameter.get('owner_address', '')
                    if from_address != verification_data.wallet_address:
                        continue
                    
                    # Validate recipient
                    to_address = parameter.get('to_address', '')
                    if to_address != admin_wallet_address:
                        continue
                    
                    # Validate amount (TRX has 6 decimals)
                    amount_sun = parameter.get('amount', 0)
                    amount = Decimal(str(amount_sun)) / Decimal('1000000')  # Convert from SUN to TRX
                    
                    if abs(amount - verification_data.amount) <= self.tolerance:
                        return {"valid": True, "amount": amount}
                
                elif contract.get('type') == 'TriggerSmartContract':
                    # TRC20 token transfer
                    parameter = contract.get('parameter', {}).get('value', {})
                    contract_address = parameter.get('contract_address', '')
                    
                    # Check if it's USDT contract
                    if contract_address == USDT_CONTRACTS["TRC20"]:
                        # Parse transfer data from logs
                        logs = tx_info.get('log', [])
                        for log in logs:
                            if log.get('address') == contract_address:
                                topics = log.get('topics', [])
                                data = log.get('data', '')
                                
                                if len(topics) >= 3:
                                    # Transfer event: Transfer(address,address,uint256)
                                    from_addr = topics[1][-40:]  # Last 40 chars (20 bytes)
                                    to_addr = topics[2][-40:]    # Last 40 chars (20 bytes)
                                    
                                    # Convert hex addresses to base58
                                    from tronpy.keys import to_base58check_address
                                    from_address = to_base58check_address('41' + from_addr)
                                    to_address = to_base58check_address('41' + to_addr)
                                    
                                    # Validate addresses
                                    if (from_address == verification_data.wallet_address and 
                                        to_address == admin_wallet_address):
                                        
                                        # Parse amount from data
                                        amount_hex = data
                                        amount_wei = int(amount_hex, 16) if amount_hex else 0
                                        amount = Decimal(str(amount_wei)) / Decimal('1000000')  # USDT has 6 decimals
                                        
                                        if abs(amount - verification_data.amount) <= self.tolerance:
                                            return {"valid": True, "amount": amount}
            
            return {"valid": False, "error": "Transaction validation failed - sender, recipient, or amount mismatch"}
            
        except Exception as e:
            logger.error(f"Error validating TRC20 transaction: {str(e)}")
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    async def _verify_evm_transaction(
        self,
        verification_data: HashVerificationRequest,
        admin_wallet_address: str
    ) -> HashVerificationResponse:
        """Verify ERC20/BEP20 transaction using Web3"""
        try:
            from web3 import Web3

            # Get network configuration
            network_config = NETWORK_CONFIGS.get(verification_data.network)
            if not network_config:
                return self._create_error_response(
                    f"Network configuration not found for {verification_data.network}",
                    verification_data.network
                )

            # Initialize Web3
            if verification_data.network == "ERC20":
                # Ethereum mainnet via Infura
                if not settings.INFURA_PROJECT_ID:
                    return self._create_error_response(
                        "Infura project ID not configured",
                        verification_data.network
                    )
                w3 = Web3(Web3.HTTPProvider(network_config["api_url"]))
            else:
                # BSC mainnet
                w3 = Web3(Web3.HTTPProvider(network_config["api_url"]))

            if not w3.is_connected():
                return self._create_error_response(
                    f"Failed to connect to {verification_data.network} network",
                    verification_data.network
                )

            # Get transaction receipt
            try:
                tx_receipt = w3.eth.get_transaction_receipt(verification_data.transaction_hash)
                tx_details = w3.eth.get_transaction(verification_data.transaction_hash)
            except Exception as e:
                return self._create_error_response(
                    f"Transaction not found: {str(e)}",
                    verification_data.network
                )

            # Check transaction status
            if tx_receipt.status != 1:
                return self._create_error_response(
                    "Transaction failed on blockchain",
                    verification_data.network
                )

            # Validate transaction details
            validation_result = await self._validate_evm_transaction(
                tx_details, tx_receipt, verification_data, admin_wallet_address, w3
            )

            if not validation_result["valid"]:
                return self._create_error_response(
                    validation_result["error"],
                    verification_data.network
                )

            # Calculate confirmations
            current_block = w3.eth.block_number
            tx_block = tx_receipt.blockNumber
            confirmations = max(0, current_block - tx_block)

            # Get block timestamp
            block = w3.eth.get_block(tx_block)
            timestamp = datetime.fromtimestamp(block.timestamp, tz=timezone.utc)

            return HashVerificationResponse(
                is_valid=True,
                confirmations=confirmations,
                amount=validation_result["amount"],
                message=f"Transaction verified successfully on {verification_data.network}",
                network=verification_data.network,
                block_height=tx_block,
                timestamp=timestamp
            )

        except ImportError:
            logger.error("Web3 library not installed")
            return self._create_error_response(
                "Web3 library not available",
                verification_data.network
            )
        except Exception as e:
            logger.error(f"Error verifying {verification_data.network} transaction: {str(e)}")
            return self._create_error_response(
                f"{verification_data.network} verification failed: {str(e)}",
                verification_data.network
            )

    async def _validate_evm_transaction(
        self,
        tx_details: Any,
        tx_receipt: Any,
        verification_data: HashVerificationRequest,
        admin_wallet_address: str,
        w3: Any
    ) -> Dict[str, Any]:
        """Validate EVM transaction details"""
        try:
            from web3 import Web3

            # Normalize addresses for comparison
            sender_address = self._normalize_address(verification_data.wallet_address, verification_data.network)
            admin_address = self._normalize_address(admin_wallet_address, verification_data.network)
            tx_from = self._normalize_address(tx_details['from'], verification_data.network)
            tx_to = self._normalize_address(tx_details.get('to', ''), verification_data.network)

            # Check if it's a direct ETH/BNB transfer
            if tx_to == admin_address and tx_from == sender_address:
                # Direct native token transfer
                amount_wei = tx_details['value']
                amount = Decimal(str(amount_wei)) / Decimal('10') ** 18  # ETH/BNB has 18 decimals

                if abs(amount - verification_data.amount) <= self.tolerance:
                    return {"valid": True, "amount": amount}

            # Check if it's a token transfer (ERC20/BEP20)
            token_contract = USDT_CONTRACTS.get(verification_data.network)
            if token_contract and tx_to.lower() == token_contract.lower():
                # Parse transfer events from logs
                for log in tx_receipt.logs:
                    if log.address.lower() == token_contract.lower():
                        # Check if it's a Transfer event
                        if len(log.topics) >= 3:
                            # Transfer event signature: Transfer(address,address,uint256)
                            transfer_signature = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

                            if log.topics[0].hex() == transfer_signature:
                                # Extract addresses from topics
                                from_addr = "0x" + log.topics[1].hex()[-40:]
                                to_addr = "0x" + log.topics[2].hex()[-40:]

                                # Normalize addresses
                                from_address = self._normalize_address(from_addr, verification_data.network)
                                to_address = self._normalize_address(to_addr, verification_data.network)

                                # Validate addresses
                                if (from_address == sender_address and to_address == admin_address):
                                    # Parse amount from data
                                    amount_hex = log.data.hex()
                                    amount_wei = int(amount_hex, 16) if amount_hex else 0

                                    # Get token decimals (USDT has 6 decimals)
                                    decimals = TOKEN_DECIMALS.get("USDT", 6)
                                    amount = Decimal(str(amount_wei)) / Decimal('10') ** decimals

                                    if abs(amount - verification_data.amount) <= self.tolerance:
                                        return {"valid": True, "amount": amount}

            return {"valid": False, "error": "Transaction validation failed - sender, recipient, or amount mismatch"}

        except Exception as e:
            logger.error(f"Error validating EVM transaction: {str(e)}")
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _create_error_response(self, message: str, network: str) -> HashVerificationResponse:
        """Create error response"""
        return HashVerificationResponse(
            is_valid=False,
            confirmations=0,
            amount=Decimal('0'),
            message=message,
            network=network,
            block_height=None,
            timestamp=None
        )


# Global service instance
blockchain_verification_service = BlockchainVerificationService()

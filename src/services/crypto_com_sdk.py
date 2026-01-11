"""
Crypto.com AI Agent SDK Integration for Wallet Management.

This module provides integration with the Crypto.com AI Agent SDK
for wallet operations including balance checking, transfers, and
spending limit management.
"""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from web3 import Web3

from src.core.config import settings

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)

# Cronos Testnet RPC
CRONOS_TESTNET_RPC = "https://evm-t3.cronos.org"
CRONOS_MAINNET_RPC = "https://evm.cronos.org"


class CryptoComAgentSDKError(Exception):
    """Crypto.com Agent SDK specific error."""
    pass


class CryptoComAgentSDK:
    """
    Crypto.com AI Agent SDK integration for wallet management.

    This class provides a wrapper around the Crypto.com AI Agent SDK
    for wallet operations including balance checking, transfers, and
    spending limit management.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Crypto.com Agent SDK integration.

        Args:
            api_key: Crypto.com API key. If None, uses settings.crypto_com_api_key
        """
        self.api_key = api_key or settings.crypto_com_api_key
        self.base_url = "https://api.crypto.com/ai-agent"
        
        # Get private key from environment
        self.private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY")
        
        # Initialize Web3 with Cronos testnet
        self.rpc_url = os.getenv("CRONOS_RPC_URL", CRONOS_TESTNET_RPC)
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Derive wallet address from private key
        if self.private_key:
            try:
                # Ensure private key has 0x prefix
                pk = self.private_key if self.private_key.startswith("0x") else f"0x{self.private_key}"
                account = self.w3.eth.account.from_key(pk)
                self.wallet_address = account.address
                logger.info(f"Wallet address derived: {self.wallet_address}")
            except Exception as e:
                logger.warning(f"Could not derive wallet address from private key: {e}")
                self.wallet_address = settings.default_wallet_address
        else:
            self.wallet_address = settings.default_wallet_address

        if not self.api_key:
            raise CryptoComAgentSDKError("Crypto.com API key is required")

        logger.info(f"Crypto.com AI Agent SDK initialized with wallet: {self.wallet_address}")

    async def check_balance(self, tokens: list[str] | None = None) -> dict[str, Any]:
        """
        Check wallet balance for specified tokens.

        Args:
            tokens: List of token symbols to check (e.g., ["CRO", "USDC", "tUSDC"])

        Returns:
            Dict containing balance information for each token
        """
        try:
            if not tokens:
                tokens = ["CRO", "USDC"]

            balances = {}
            
            # Ensure wallet address is properly checksummed
            checksum_address = self.w3.to_checksum_address(self.wallet_address)
            
            # tUSDC contract address on Cronos testnet (from vvs-testnet.json)
            TUSDC_ADDRESS = "0x1C4719F10f0ADc7A8AcBC688Ecb1AfE1611D16ED"
            
            # Minimal ERC20 ABI for balanceOf
            ERC20_ABI = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }
            ]

            for token in tokens:
                token_upper = token.upper()
                if token_upper == "CRO":
                    # Get native CRO balance from chain
                    try:
                        balance_wei = self.w3.eth.get_balance(checksum_address)
                        balance = float(self.w3.from_wei(balance_wei, "ether"))
                        balances["CRO"] = balance
                        logger.info(f"CRO balance: {balance}")
                    except Exception as e:
                        logger.error(f"Failed to get CRO balance: {e}")
                        balances["CRO"] = 0.0
                elif token_upper in ("USDC", "TUSDC"):
                    # Query real tUSDC balance from ERC20 contract
                    try:
                        tusdc_contract = self.w3.eth.contract(
                            address=self.w3.to_checksum_address(TUSDC_ADDRESS),
                            abi=ERC20_ABI
                        )
                        balance_raw = tusdc_contract.functions.balanceOf(checksum_address).call()
                        # tUSDC has 6 decimals
                        balance = float(balance_raw) / 1e6
                        # Store under both keys for compatibility
                        balances["tUSDC"] = balance
                        balances["USDC"] = balance
                        logger.info(f"tUSDC balance: {balance}")
                    except Exception as e:
                        logger.error(f"Failed to get tUSDC balance: {e}")
                        balances["tUSDC"] = 0.0
                        balances["USDC"] = 0.0
                else:
                    balances[token] = 0.0

            logger.info(f"Retrieved balances: {balances}")
            return {
                "balances": balances,
                "wallet_address": self.wallet_address,
                "network": "Cronos Testnet" if "t3" in self.rpc_url else "Cronos Mainnet",
            }

        except Exception as e:
            logger.error(f"Failed to check balance: {e}")
            raise CryptoComAgentSDKError(f"Balance check failed: {e}")

    async def transfer(
        self,
        recipient_address: str,
        amount: float,
        token: str,
        description: str = ""
    ) -> dict[str, Any]:
        """
        Execute a token transfer using the AI Agent SDK.

        Args:
            recipient_address: Destination wallet address
            amount: Amount to transfer
            token: Token symbol (e.g., "CRO", "USDC")
            description: Optional transfer description

        Returns:
            Dict containing transfer result

        Example:
            {
                "success": True,
                "tx_hash": "0xabc123...",
                "amount": 10.0,
                "token": "CRO",
                "recipient": "0x...",
                "status": "completed"
            }
        """
        try:
            # This would integrate with the actual Crypto.com AI Agent SDK
            # For now, return mock data structure

            # Validate inputs
            if not recipient_address:
                raise CryptoComAgentSDKError("Recipient address is required")

            if amount <= 0:
                raise CryptoComAgentSDKError("Transfer amount must be positive")

            if not token:
                raise CryptoComAgentSDKError("Token symbol is required")

            # Mock implementation - in real implementation, this would call
            # the Crypto.com AI Agent SDK transfer function
            transfer_result = {
                "success": True,
                "tx_hash": f"0x{hash(f'{recipient_address}{amount}{token}') & 0xffffffff:016x}",
                "amount": amount,
                "token": token,
                "recipient": recipient_address,
                "status": "completed",
                "description": description,
                "timestamp": "2025-12-25T13:00:00Z"
            }

            logger.info(f"Transfer completed: {amount} {token} to {recipient_address}")
            return transfer_result

        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            raise CryptoComAgentSDKError(f"Transfer failed: {e}")

    async def get_transaction_history(
        self,
        limit: int = 100,
        token: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get transaction history for the wallet.

        Args:
            limit: Maximum number of transactions to return
            token: Optional token to filter transactions

        Returns:
            List of transaction records
        """
        try:
            # This would integrate with the actual Crypto.com AI Agent SDK
            # For now, return mock data structure

            # Mock implementation
            transactions = [
                {
                    "tx_hash": f"0x{hash(f'tx_{i}') & 0xffffffff:016x}",
                    "amount": 10.0 + i,
                    "token": "CRO",
                    "type": "transfer_out" if i % 2 == 0 else "transfer_in",
                    "counterparty": "0xrecipient123",
                    "status": "completed",
                    "timestamp": "2025-12-25T12:00:00Z",
                    "description": f"Transaction {i}"
                }
                for i in range(limit)
            ]

            logger.info(f"Retrieved {len(transactions)} transactions")
            return transactions

        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            raise CryptoComAgentSDKError(f"Transaction history failed: {e}")

    async def check_spending_limit(self, token: str = "USDC") -> dict[str, Any]:
        """
        Check current spending limits for a token.

        Args:
            token: Token symbol to check limits for

        Returns:
            Dict containing spending limit information
        """
        try:
            # This would integrate with the actual Crypto.com AI Agent SDK
            # For now, return mock data structure

            # Mock implementation
            limit_info = {
                "token": token,
                "daily_limit": 1000.0,
                "daily_spent": 250.0,
                "remaining": 750.0,
                "spending_percentage": 25.0,
                "limit_currency": "USD",
                "reset_time": "2025-12-26T00:00:00Z",
                "status": "within_limit"
            }

            logger.info(f"Spending limit check for {token}: {limit_info}")
            return limit_info

        except Exception as e:
            logger.error(f"Failed to check spending limit: {e}")
            raise CryptoComAgentSDKError(f"Spending limit check failed: {e}")

    async def set_spending_limit(
        self,
        daily_limit: float,
        token: str = "USDC"
    ) -> dict[str, Any]:
        """
        Set a new daily spending limit for a token.

        Args:
            daily_limit: New daily limit in USD
            token: Token symbol to set limit for

        Returns:
            Dict containing confirmation of limit change
        """
        try:
            # This would integrate with the actual Crypto.com AI Agent SDK
            # For now, return mock data structure

            # Validate inputs
            if daily_limit <= 0:
                raise CryptoComAgentSDKError("Daily limit must be positive")

            # Mock implementation
            result = {
                "success": True,
                "token": token,
                "previous_limit": 1000.0,
                "new_limit": daily_limit,
                "status": "limit_updated",
                "effective_immediately": True
            }

            logger.info(f"Spending limit updated for {token}: {daily_limit} USD")
            return result

        except Exception as e:
            logger.error(f"Failed to set spending limit: {e}")
            raise CryptoComAgentSDKError(f"Set spending limit failed: {e}")

    async def get_wallet_info(self) -> dict[str, Any]:
        """
        Get comprehensive wallet information.

        Returns:
            Dict containing wallet details
        """
        try:
            # This would integrate with the actual Crypto.com AI Agent SDK
            # For now, return mock data structure

            # Mock implementation
            wallet_info = {
                "wallet_address": self.wallet_address,
                "network": "Cronos",
                "total_usd_value": 1500.0,
                "tokens_supported": ["CRO", "USDC", "USDT", "BTC", "ETH"],
                "features": {
                    "spending_limits": True,
                    "transaction_history": True,
                    "real_time_balances": True,
                    "transfer_approval": True
                },
                "status": "active",
                "last_updated": "2025-12-25T13:00:00Z"
            }

            logger.info("Retrieved wallet information")
            return wallet_info

        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}")
            raise CryptoComAgentSDKError(f"Wallet info retrieval failed: {e}")

    async def health_check(self) -> bool:
        """
        Check if the Crypto.com AI Agent SDK connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # This would integrate with the actual Crypto.com AI Agent SDK
            # For now, return mock health check

            # Mock implementation - in real implementation, this would ping
            # the Crypto.com AI Agent SDK health endpoint
            return True

        except Exception as e:
            logger.error(f"Crypto.com AI Agent SDK health check failed: {e}")
            return False


# Global Crypto.com Agent SDK instance
_crypto_com_sdk: CryptoComAgentSDK | None = None


def get_crypto_com_sdk() -> CryptoComAgentSDK:
    """
    Get the global Crypto.com Agent SDK instance.

    Returns:
        CryptoComAgentSDK instance
    """
    global _crypto_com_sdk
    if _crypto_com_sdk is None:
        _crypto_com_sdk = CryptoComAgentSDK()
    return _crypto_com_sdk


def create_crypto_com_sdk(api_key: str | None = None) -> CryptoComAgentSDK:
    """
    Create a new Crypto.com Agent SDK instance.

    Args:
        api_key: Optional API key

    Returns:
        CryptoComAgentSDK instance
    """
    return CryptoComAgentSDK(api_key)

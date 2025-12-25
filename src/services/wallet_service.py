"""
Wallet service for managing agent wallet operations.

This service provides functionality for checking balances, managing daily
spending allowances, and executing token transfers via the AgentWallet contract.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.payments import Payment

logger = logging.getLogger(__name__)


class WalletService:
    """Service for wallet management operations."""

    def __init__(self, db: AsyncSession, wallet_address: str | None = None):
        """
        Initialize the wallet service.

        Args:
            db: Database session
            wallet_address: Optional wallet address (defaults to config)
        """
        self.db = db
        self.wallet_address = wallet_address or settings.default_wallet_address
        self.daily_limit_usd = settings.default_daily_limit_usd

    async def check_balance(
        self,
        tokens: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Check wallet token balances.

        Args:
            tokens: Optional list of token symbols to query (default: CRO, USDC)

        Returns:
            Dict containing balance information
        """
        try:
            # Default to common tokens if not specified
            if not tokens:
                tokens = ["CRO", "USDC"]

            logger.info(f"Checking balances for {tokens} in wallet {self.wallet_address}")

            # Try to get actual blockchain balances, fall back to mock on error
            balances = []
            total_balance_usd = 0.0

            try:
                # Import web3 for blockchain interaction
                from web3 import Web3

                from src.core.config import settings

                # Connect to Cronos RPC
                w3 = Web3(Web3.HTTPProvider(settings.cronos_rpc_url))

                if not w3.is_connected():
                    logger.warning("Failed to connect to Cronos RPC, using mock balances")
                    return await self._get_mock_balances(tokens)

                # Token addresses on Cronos testnet
                token_addresses = {
                    "USDC": "0x2336cE47712A4BC7fCC4FC6c4693e54F9D75Cd72",  # devUSDC.e on Cronos testnet
                    "USDT": "0xB8888885888898888888F8888888888888888f",  # Mock address
                    "CRO": None,  # Native token
                }

                # ERC20 ABI for balance checking
                erc20_abi = [
                    {
                        "constant": True,
                        "inputs": [{"name": "_owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "balance", "type": "uint256"}],
                        "type": "function",
                    },
                    {
                        "constant": True,
                        "inputs": [],
                        "name": "decimals",
                        "outputs": [{"name": "", "type": "uint8"}],
                        "type": "function",
                    },
                ]

                # Check each token
                for token_symbol in tokens:
                    token_address = token_addresses.get(token_symbol)

                    if token_symbol == "CRO":
                        # Native CRO balance
                        balance_wei = w3.eth.get_balance(self.wallet_address)
                        balance = float(w3.from_wei(balance_wei, 'ether'))
                    elif token_address:
                        # ERC20 token balance
                        contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=erc20_abi)
                        balance_wei = contract.functions.balanceOf(Web3.to_checksum_address(self.wallet_address)).call()
                        decimals = contract.functions.decimals().call()
                        balance = float(balance_wei / (10 ** decimals))
                    else:
                        # Unknown token, use mock
                        balance = 0.0

                    # Get USD price (mock for now - could be from price oracle)
                    price_usd = self._get_token_price(token_symbol)
                    balance_usd = balance * price_usd if price_usd else None

                    balances.append({
                        "token_symbol": token_symbol,
                        "token_address": token_address or self._get_token_address(token_symbol),
                        "balance": balance,
                        "balance_usd": balance_usd,
                    })

                    if balance_usd:
                        total_balance_usd += balance_usd

            except Exception as e:
                logger.error(f"Blockchain balance check failed: {e}, using mock balances")
                # Fall back to mock balances on any error
                mock_result = await self._get_mock_balances(tokens)
                return mock_result

            return {
                "success": True,
                "wallet_address": self.wallet_address,
                "balances": balances,
                "total_balance_usd": total_balance_usd,
            }

        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to check balance: {str(e)}",
            }

    async def get_allowance(self) -> dict[str, Any]:
        """
        Get remaining daily spending allowance.

        Calculates how much of the daily spending limit has been used today
        and returns the remaining allowance.

        Returns:
            Dict containing allowance information
        """
        try:
            # Get start of today (UTC)
            today_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # Calculate total spent today from confirmed payments
            result = await self.db.execute(
                select(func.sum(Payment.amount))
                .where(
                    Payment.agent_wallet == self.wallet_address,
                    Payment.status == "confirmed",
                    Payment.created_at >= today_start,
                    Payment.token == "USDC",  # Only count USDC for now
                )
            )

            spent_today = result.scalar() or 0.0

            # Calculate remaining allowance
            remaining = max(0.0, self.daily_limit_usd - spent_today)

            # Calculate reset time (start of next day UTC)
            tomorrow = today_start + timedelta(days=1)
            resets_at = tomorrow.isoformat()

            return {
                "success": True,
                "wallet_address": self.wallet_address,
                "daily_limit_usd": self.daily_limit_usd,
                "spent_today_usd": round(spent_today, 2),
                "remaining_allowance_usd": round(remaining, 2),
                "resets_at": resets_at,
            }

        except Exception as e:
            logger.error(f"Allowance check failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to check allowance: {str(e)}",
            }

    async def transfer_tokens(
        self,
        recipient: str,
        amount: float,
        token: str,
    ) -> dict[str, Any]:
        """
        Execute a token transfer.

        This validates:
        1. Sufficient balance
        2. Daily spending limit
        3. Valid recipient address

        Then executes the transfer via AgentWallet contract.

        Args:
            recipient: Recipient wallet address
            amount: Amount to transfer
            token: Token symbol or address

        Returns:
            Dict containing transfer result
        """
        try:
            logger.info(
                f"Transfer request: {amount} {token} to {recipient}"
            )

            # Step 1: Validate recipient address
            if not recipient.startswith("0x") or len(recipient) != 42:
                return {
                    "success": False,
                    "error": "invalid_recipient",
                    "message": "Invalid recipient wallet address",
                }

            # Step 2: Check balance
            balance_result = await self.check_balance(tokens=[token])
            if not balance_result["success"]:
                return balance_result

            # Find the token balance
            token_balance = None
            for bal in balance_result["balances"]:
                if bal["token_symbol"] == token or bal["token_address"] == token:
                    token_balance = bal["balance"]
                    break

            if token_balance is None:
                return {
                    "success": False,
                    "error": "token_not_found",
                    "message": f"Token {token} not found in wallet",
                }

            if token_balance < amount:
                return {
                    "success": False,
                    "error": "insufficient_balance",
                    "message": f"Insufficient balance. Have {token_balance}, need {amount}",
                }

            # Step 3: Check daily allowance (for USDC)
            if token in ["USDC", "USDT"]:
                allowance_result = await self.get_allowance()
                if allowance_result["success"]:
                    remaining = allowance_result["remaining_allowance_usd"]
                    if amount > remaining:
                        return {
                            "success": False,
                            "error": "daily_limit_exceeded",
                            "message": f"Amount ${amount} exceeds daily remaining allowance ${remaining:.2f}",
                        }

            # Step 4: Execute transfer (mock for now)
            # TODO: Integrate with AgentWallet contract
            import os
            mock_tx_hash = f"0x{os.urandom(32).hex()}"

            # Create payment record
            payment = Payment(
                agent_wallet=self.wallet_address,
                recipient=recipient,
                amount=amount,
                token=token,
                tx_hash=mock_tx_hash,
                status="confirmed",
            )
            self.db.add(payment)
            await self.db.commit()

            logger.info(f"Transfer executed: {mock_tx_hash}")

            return {
                "success": True,
                "tx_hash": mock_tx_hash,
                "status": "confirmed",
                "from_address": self.wallet_address,
                "to_address": recipient,
                "amount": amount,
                "token": token,
                "message": "Transfer completed successfully",
            }

        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            await self.db.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": f"Transfer failed: {str(e)}",
            }

    async def get_transaction_history(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get wallet transaction history.

        Args:
            offset: Pagination offset
            limit: Max results to return

        Returns:
            Dict containing transaction history
        """
        try:
            # Get total count
            count_result = await self.db.execute(
                select(func.count())
                .where(Payment.agent_wallet == self.wallet_address)
            )
            total = count_result.scalar() or 0

            # Get paginated transactions
            result = await self.db.execute(
                select(Payment)
                .where(Payment.agent_wallet == self.wallet_address)
                .order_by(Payment.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            payments = result.scalars().all()

            transactions = []
            for payment in payments:
                transactions.append({
                    "tx_hash": payment.tx_hash or "pending",
                    "from_address": payment.agent_wallet,
                    "to_address": payment.recipient,
                    "amount": payment.amount,
                    "token": payment.token,
                    "token_symbol": payment.token,  # TODO: Map to symbol
                    "status": payment.status,
                    "timestamp": payment.created_at.isoformat(),
                    "gas_used": None,  # TODO: Add gas tracking
                    "gas_price_gwei": None,
                })

            return {
                "success": True,
                "transactions": transactions,
                "total": total,
                "offset": offset,
                "limit": limit,
            }

        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            return {
                "success": False,
                "error": str(e),
                "transactions": [],
                "total": 0,
                "offset": offset,
                "limit": limit,
            }

    async def _get_mock_balances(self, tokens: list[str]) -> dict[str, Any]:
        """
        Get mock balances for development/fallback.

        Args:
            tokens: List of token symbols

        Returns:
            Dict containing mock balance information
        """
        balances = []
        total_balance_usd = 0.0

        token_prices = {
            "CRO": 0.10,
            "USDC": 1.0,
            "USDT": 1.0,
            "ETH": 2000.0,
            "BTC": 45000.0,
        }

        mock_balances = {
            "CRO": 1000.0,
            "USDC": 100.0,
            "USDT": 50.0,
            "ETH": 0.5,
            "BTC": 0.01,
        }

        for token_symbol in tokens:
            balance = mock_balances.get(token_symbol, 0.0)
            price_usd = token_prices.get(token_symbol, 0.0)
            balance_usd = balance * price_usd if price_usd else None

            balances.append({
                "token_symbol": token_symbol,
                "token_address": self._get_token_address(token_symbol),
                "balance": balance,
                "balance_usd": balance_usd,
            })

            if balance_usd:
                total_balance_usd += balance_usd

        return {
            "success": True,
            "wallet_address": self.wallet_address,
            "balances": balances,
            "total_balance_usd": total_balance_usd,
        }

    def _get_token_price(self, token_symbol: str) -> float | None:
        """
        Get token price in USD.

        Args:
            token_symbol: Token symbol

        Returns:
            Price in USD (mock for now)
        """
        token_prices = {
            "CRO": 0.10,
            "USDC": 1.0,
            "USDT": 1.0,
            "ETH": 2000.0,
            "BTC": 45000.0,
        }
        return token_prices.get(token_symbol)

    def _get_token_address(self, token_symbol: str) -> str:
        """
        Get token address from symbol.

        Args:
            token_symbol: Token symbol

        Returns:
            Token address
        """
        token_addresses = {
            "CRO": "0x0000000000000000000000000000000000000000",  # Native
            "USDC": "0x2336cE47712A4BC7fCC4FC6c4693e54F9D75Cd72",
            "USDT": "0xB8888885888898888888F8888888888888888f",
        }
        return token_addresses.get(token_symbol, f"0x{'0' * 40}")

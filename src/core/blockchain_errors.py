"""
Blockchain Error Handling Module

This module provides comprehensive error handling for blockchain operations
including revert reasons, gas estimation failures, and other blockchain-specific
error scenarios.
"""

import logging
import re
from typing import Any, Optional

from eth_account.exceptions import (
    InvalidTransaction,
    TimeExhausted,
    TransactionNotFound,
)
from eth_typing import HexStr
from web3.exceptions import (
    ContractLogicError,
    ContractPanicError,
    InsufficientFunds,
)
from web3.exceptions import (
    TimeExhausted as Web3TimeExhausted,
)
from web3.exceptions import (
    TransactionNotFound as Web3TransactionNotFound,
)

from src.core.errors import SafeException, create_safe_error_message

logger = logging.getLogger(__name__)


class BlockchainError(SafeException):
    """Base exception for blockchain-related errors."""

    def __init__(
        self,
        message: str,
        error_type: str = "blockchain_error",
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize blockchain error.

        Args:
            message: User-friendly error message
            error_type: Type of blockchain error
            details: Additional error details
        """
        self.error_type = error_type
        self.details = details or {}
        super().__init__(message, detail=self.get_error_guidance(error_type))

    def get_error_guidance(self, error_type: str) -> str:
        """Get user guidance for specific error types."""
        guidance_map = {
            "revert": "The transaction was reverted by the contract. This usually means insufficient funds, expired transaction, or contract-specific validation failed. Please check your balance and try again.",
            "insufficient_gas": "The transaction ran out of gas. This means the gas limit was too low or gas price was too high. Please try increasing the gas limit or adjusting the gas price.",
            "insufficient_funds": "Your wallet doesn't have enough funds to cover this transaction. Please add more cryptocurrency to your wallet and try again.",
            "contract_error": "The contract execution failed. This could be due to contract logic or invalid parameters. Please verify the transaction details.",
            "timeout": "The transaction took too long to confirm. This can happen during network congestion. Please try again later or increase the gas price.",
            "nonce_too_low": "The transaction nonce is too low. This usually means a previous transaction is still pending. Please wait for confirmation or use a higher nonce.",
            "replacement_transaction_underpriced": "The replacement transaction has a lower gas price than the original. Please use a higher gas price.",
            "unknown": "An unknown blockchain error occurred. Our team has been notified. Please try again or contact support."
        }
        return guidance_map.get(error_type, guidance_map["unknown"])


class RevertError(BlockchainError):
    """Exception for contract revert errors."""

    def __init__(self, revert_reason: str, tx_hash: Optional[HexStr] = None):
        """
        Initialize revert error.

        Args:
            revert_reason: The reason for the revert
            tx_hash: Transaction hash (optional)
        """
        self.revert_reason = revert_reason
        self.tx_hash = tx_hash

        # Parse revert reason for user-friendly message
        user_message = self.parse_revert_reason(revert_reason)

        super().__init__(
            message=f"Transaction reverted: {user_message}",
            error_type="revert",
            details={
                "revert_reason": revert_reason,
                "tx_hash": tx_hash,
                "parsed_reason": user_message,
            },
        )

    def parse_revert_reason(self, reason: str) -> str:
        """Parse revert reason for user-friendly display."""
        if not reason:
            return "Unknown contract error"

        # Common revert reasons and their user-friendly equivalents
        reason_map = {
            r"insufficient.*balance": "Insufficient balance to complete the transaction",
            r"allowance.*too.*low": "Token allowance is too low",
            r"deadline.*exceeded": "Transaction deadline has passed",
            r"slippage.*too.*high": "Slippage tolerance exceeded",
            r"insufficient.*liquidity": "Insufficient liquidity for this swap",
            r"contract.*paused": "Contract is currently paused",
            r"access.*denied": "Access denied - insufficient permissions",
            r"invalid.*input": "Invalid input parameters",
            r"execution.*reverted": "Transaction execution failed",
            r"out.*of.*gas": "Transaction ran out of gas",
        }

        reason_lower = reason.lower()
        for pattern, friendly_message in reason_map.items():
            if re.search(pattern, reason_lower):
                return friendly_message

        # Return original reason if no pattern matches
        return reason


class GasError(BlockchainError):
    """Exception for gas-related errors."""

    def __init__(
        self,
        gas_error: InsufficientFunds | ContractLogicError | str,
        estimated_gas: Optional[int] = None,
        current_gas_price: Optional[int] = None,
        tx_hash: Optional[HexStr] = None,
    ):
        """
        Initialize gas error.

        Args:
            gas_error: The gas-related error
            estimated_gas: Estimated gas required
            current_gas_price: Current gas price in wei
            tx_hash: Transaction hash (optional)
        """
        self.gas_error = gas_error
        self.estimated_gas = estimated_gas
        self.current_gas_price = current_gas_price
        self.tx_hash = tx_hash

        # Determine error type and message
        if isinstance(gas_error, InsufficientFunds):
            message = "Insufficient funds to cover gas costs"
            error_type = "insufficient_funds"
        elif isinstance(gas_error, ContractLogicError):
            message = "Transaction would fail due to contract logic"
            error_type = "contract_error"
        else:
            message = str(gas_error)
            error_type = "insufficient_gas"

        # Add gas estimation details
        details = {
            "estimated_gas": estimated_gas,
            "current_gas_price": current_gas_price,
            "tx_hash": tx_hash,
        }

        super().__init__(message=message, error_type=error_type, details=details)


class TimeoutError(BlockchainError):
    """Exception for transaction timeout errors."""

    def __init__(
        self,
        timeout_duration: int,
        tx_hash: HexStr,
        current_status: str = "pending",
    ):
        """
        Initialize timeout error.

        Args:
            timeout_duration: Timeout duration in seconds
            tx_hash: Transaction hash
            current_status: Current transaction status
        """
        self.timeout_duration = timeout_duration
        self.tx_hash = tx_hash
        self.current_status = current_status

        message = f"Transaction confirmation timed out after {timeout_duration}s"
        details = {
            "timeout_duration": timeout_duration,
            "tx_hash": tx_hash,
            "current_status": current_status,
        }

        super().__init__(
            message=message,
            error_type="timeout",
            details=details,
        )


class TransactionError(BlockchainError):
    """Exception for general transaction errors."""

    def __init__(self, error: Exception, tx_hash: Optional[HexStr] = None):
        """
        Initialize transaction error.

        Args:
            error: The underlying error
            tx_hash: Transaction hash (optional)
        """
        self.error = error
        self.tx_hash = tx_hash

        # Determine error type based on error content
        error_str = str(error).lower()
        error_type = "unknown"

        if "nonce" in error_str and "too low" in error_str:
            error_type = "nonce_too_low"
        elif "replacement" in error_str and "underpriced" in error_str:
            error_type = "replacement_transaction_underpriced"
        elif "insufficient" in error_str and "funds" in error_str:
            error_type = "insufficient_funds"
        elif "revert" in error_str or "execution" in error_str:
            error_type = "revert"
        elif "gas" in error_str:
            error_type = "insufficient_gas"

        message = create_safe_error_message(error)

        super().__init__(
            message=message,
            error_type=error_type,
            details={
                "original_error": str(error),
                "tx_hash": tx_hash,
                "error_type_detected": error_type,
            },
        )


class BlockchainErrorHandler:
    """Centralized handler for blockchain errors."""

    @staticmethod
    def handle_revert_error(
        error: ContractLogicError | ContractPanicError,
        tx_hash: Optional[HexStr] = None,
    ) -> RevertError:
        """
        Handle contract revert errors.

        Args:
            error: The revert error
            tx_hash: Transaction hash (optional)

        Returns:
            RevertError with parsed information
        """
        logger.error(f"Transaction reverted: {error}")

        # Extract revert reason from error
        revert_reason = str(error)
        if hasattr(error, "args") and len(error.args) > 0:
            revert_reason = error.args[0]

        return RevertError(revert_reason=revert_reason, tx_hash=tx_hash)

    @staticmethod
    def handle_gas_error(
        error: InsufficientFunds | ContractLogicError,
        estimated_gas: Optional[int] = None,
        current_gas_price: Optional[int] = None,
        tx_hash: Optional[HexStr] = None,
    ) -> GasError:
        """
        Handle gas-related errors.

        Args:
            error: The gas error
            estimated_gas: Estimated gas required
            current_gas_price: Current gas price in wei
            tx_hash: Transaction hash (optional)

        Returns:
            GasError with detailed information
        """
        logger.error(f"Gas error: {error}")

        return GasError(
            gas_error=error,
            estimated_gas=estimated_gas,
            current_gas_price=current_gas_price,
            tx_hash=tx_hash,
        )

    @staticmethod
    def handle_timeout_error(
        timeout_duration: int,
        tx_hash: HexStr,
        current_status: str = "pending",
    ) -> TimeoutError:
        """
        Handle transaction timeout errors.

        Args:
            timeout_duration: Timeout duration in seconds
            tx_hash: Transaction hash
            current_status: Current transaction status

        Returns:
            TimeoutError with timeout details
        """
        logger.error(f"Transaction timeout: {tx_hash} after {timeout_duration}s")

        return TimeoutError(
            timeout_duration=timeout_duration,
            tx_hash=tx_hash,
            current_status=current_status,
        )

    @staticmethod
    def handle_general_transaction_error(
        error: Exception,
        tx_hash: Optional[HexStr] = None,
    ) -> TransactionError:
        """
        Handle general transaction errors.

        Args:
            error: The transaction error
            tx_hash: Transaction hash (optional)

        Returns:
            TransactionError with error details
        """
        logger.error(f"Transaction error: {error}")

        return TransactionError(error=error, tx_hash=tx_hash)

    @staticmethod
    def parse_web3_error(error: Exception) -> BlockchainError:
        """
        Parse web3.py errors into specific blockchain error types.

        Args:
            error: The web3.py error

        Returns:
            Appropriate BlockchainError subclass
        """
        if isinstance(error, (ContractLogicError, ContractPanicError)):
            return BlockchainErrorHandler.handle_revert_error(error)

        elif isinstance(error, InsufficientFunds):
            return BlockchainErrorHandler.handle_gas_error(error)

        elif isinstance(error, (Web3TimeExhausted, TimeExhausted)):
            # For timeout errors, we need the transaction hash
            # which might not always be available
            return BlockchainErrorHandler.handle_timeout_error(
                timeout_duration=300,  # Default 5 minutes
                tx_hash=getattr(error, "transaction_hash", None),
            )

        elif isinstance(error, Web3TransactionNotFound):
            return BlockchainErrorHandler.handle_general_transaction_error(
                error, tx_hash=getattr(error, "transaction_hash", None)
            )

        elif isinstance(error, TransactionNotFound):
            return BlockchainErrorHandler.handle_general_transaction_error(
                error, tx_hash=getattr(error, "transaction_hash", None)
            )

        elif isinstance(error, InvalidTransaction):
            return BlockchainErrorHandler.handle_general_transaction_error(error)

        else:
            # Unknown error type
            return BlockchainErrorHandler.handle_general_transaction_error(error)

    @staticmethod
    async def estimate_transaction_safety(
        web3_client,
        transaction: dict[str, Any],
        wallet_address: str,
    ) -> dict[str, Any]:
        """
        Estimate transaction safety before execution.

        Args:
            web3_client: Web3 client instance
            transaction: Transaction parameters
            wallet_address: Wallet address for balance check

        Returns:
            Dictionary with safety assessment
        """
        try:
            # Check wallet balance
            balance = await web3_client.eth.get_balance(wallet_address)

            # Estimate gas
            estimated_gas = await web3_client.eth.estimate_gas(transaction)

            # Get current gas price
            gas_price = await web3_client.eth.gas_price

            # Calculate total cost
            total_cost = estimated_gas * gas_price

            # Safety assessment
            has_sufficient_funds = balance >= total_cost
            recommended_gas_limit = estimated_gas * 110 // 100  # Add 10% buffer

            return {
                "safe": has_sufficient_funds,
                "balance": balance,
                "estimated_gas": estimated_gas,
                "recommended_gas_limit": recommended_gas_limit,
                "gas_price": gas_price,
                "total_cost": total_cost,
                "has_sufficient_funds": has_sufficient_funds,
                "safety_score": 100 if has_sufficient_funds else 0,
            }

        except Exception as e:
            logger.error(f"Transaction safety estimation failed: {e}")
            return {
                "safe": False,
                "error": str(e),
                "safety_score": 0,
            }

    @staticmethod
    def format_error_for_user(error: Exception | BlockchainError) -> dict[str, Any]:
        """
        Format error for user display with actionable guidance.

        Args:
            error: The error to format

        Returns:
            Dictionary with user-friendly error information
        """
        if isinstance(error, BlockchainError):
            return {
                "error": error.message,
                "type": error.error_type,
                "guidance": error.detail,
                "details": error.details,
            }
        else:
            # Convert to BlockchainError first
            blockchain_error = BlockchainErrorHandler.parse_web3_error(error)
            return BlockchainErrorHandler.format_error_for_user(blockchain_error)


def create_blockchain_error_handler():
    """Create and configure a blockchain error handler."""
    return BlockchainErrorHandler()


# Global error handler instance
blockchain_error_handler = create_blockchain_error_handler()

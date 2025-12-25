"""
EIP-712 signature generation for x402 payment protocol.

This module implements typed data signing according to EIP-712 for payment
authorization on the Cronos blockchain.
"""

import logging
import time
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data
from pydantic import BaseModel, Field

from src.core.config import settings

logger = logging.getLogger(__name__)


class PaymentSignatureData(BaseModel):
    """Data model for payment signature."""

    service_url: str = Field(..., description="URL of the service being paid")
    amount: int = Field(..., description="Payment amount in smallest unit")
    token: str = Field(..., description="Token symbol (e.g., USDC)")
    description: str | None = Field(None, description="Optional payment description")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="Payment timestamp")
    nonce: int = Field(..., description="Unique nonce for replay protection")
    wallet_address: str = Field(..., description="Payer's wallet address")


class EIP712SignatureGenerator:
    """
    EIP-712 signature generator for x402 payments.

    This class handles the creation of EIP-712 typed data signatures
    for payment authorization on the Cronos blockchain.
    """

    # EIP-712 Domain separator for Paygent
    DOMAIN = {
        "name": "PaygentPayment",
        "version": "1.0",
        "chainId": None,  # Set from config
        "verifyingContract": None,  # Set from config when deployed
    }

    # EIP-712 Type definitions
    TYPES = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "Payment": [
            {"name": "serviceUrl", "type": "string"},
            {"name": "amount", "type": "uint256"},
            {"name": "token", "type": "string"},
            {"name": "description", "type": "string"},
            {"name": "timestamp", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "walletAddress", "type": "address"},
        ],
    }

    def __init__(self, private_key: str | None = None):
        """
        Initialize the signature generator.

        Args:
            private_key: Private key for signing (in development).
                        In production, should use HSM or key management service.
        """
        self.chain_id = settings.cronos_chain_id
        self.verifying_contract = getattr(settings, 'payment_router_address', None)

        # Update domain with chain ID
        self.domain = self.DOMAIN.copy()
        self.domain["chainId"] = self.chain_id
        # For development, use zero address if no contract deployed
        self.domain["verifyingContract"] = self.verifying_contract or "0x0000000000000000000000000000000000000000"

        # Initialize account with private key (development only)
        self.account = None
        if private_key:
            try:
                self.account = Account.from_key(private_key)
                logger.info(f"Initialized signer with address: {self.account.address}")
            except Exception as e:
                logger.error(f"Failed to initialize account: {e}")

        # Nonce tracking (in production, use Redis or database)
        self._nonces = {}

    def get_nonce(self, wallet_address: str) -> int:
        """
        Get next nonce for wallet address.

        Args:
            wallet_address: Wallet address

        Returns:
            Nonce value
        """
        if wallet_address not in self._nonces:
            self._nonces[wallet_address] = 0
        else:
            self._nonces[wallet_address] += 1
        return self._nonces[wallet_address]

    def create_payment_data(
        self,
        service_url: str,
        amount: float,
        token: str,
        wallet_address: str,
        description: str | None = None,
    ) -> PaymentSignatureData:
        """
        Create payment signature data.

        Args:
            service_url: URL of the service being paid
            amount: Payment amount (will be converted to smallest unit)
            token: Token symbol
            wallet_address: Payer's wallet address
            description: Optional payment description

        Returns:
            PaymentSignatureData instance
        """
        return PaymentSignatureData(
            service_url=service_url,
            amount=int(amount * 1e6),  # Convert to 6 decimal places (USDC standard)
            token=token,
            description=description or "",
            wallet_address=wallet_address,
            nonce=self.get_nonce(wallet_address),
        )

    def sign_payment(self, payment_data: PaymentSignatureData) -> dict[str, Any]:
        """
        Sign payment data using EIP-712.

        Args:
            payment_data: Payment signature data

        Returns:
            Dict containing signature and metadata
        """
        try:
            if not self.account:
                return {
                    "success": False,
                    "error": "no_signer_configured",
                    "message": "No signer account configured",
                }

            # Create message - ensure wallet address is a proper string
            # The payment_data.wallet_address might be coming in with extra quotes
            wallet_address = str(payment_data.wallet_address)
            # Remove any surrounding quotes that might have been added
            if wallet_address.startswith(("'", '"')) and wallet_address.endswith(("'", '"')):
                wallet_address = wallet_address[1:-1]

            message = {
                "serviceUrl": payment_data.service_url,
                "amount": payment_data.amount,
                "token": payment_data.token,
                "description": payment_data.description or "",
                "timestamp": payment_data.timestamp,
                "nonce": payment_data.nonce,
                "walletAddress": wallet_address,
            }

            # Encode typed data
            encoded_message = encode_typed_data(
                domain_data=self.domain,
                message_types={"Payment": self.TYPES["Payment"]},
                message_data=message,
            )

            # Sign message
            signed_message = self.account.sign_message(encoded_message)

            # Create signature object - ensure signature has 0x prefix
            signature_hex = signed_message.signature.hex()
            if not signature_hex.startswith("0x"):
                signature_hex = "0x" + signature_hex

            signature = {
                "domain": self.domain,
                "types": {"Payment": self.TYPES["Payment"]},
                "message": message,
                "signature": signature_hex,
                "signerAddress": self.account.address,
            }

            return {
                "success": True,
                "signature": signature,
                "signer": self.account.address,
                "message": "Payment signed successfully",
            }

        except Exception as e:
            logger.error(f"Payment signing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Payment signing failed: {str(e)}",
            }

    def verify_signature(
        self,
        signature: str,
        message: dict[str, Any],
        expected_address: str,
    ) -> bool:
        """
        Verify EIP-712 signature.

        Args:
            signature: Signature hex string
            message: Message data that was signed
            expected_address: Expected signer address

        Returns:
            True if signature is valid
        """
        try:
            # Encode typed data
            encoded_message = encode_typed_data(
                domain_data=self.domain,
                message_types={"Payment": self.TYPES["Payment"]},
                message_data=message,
            )

            # Recover address from signature
            recovered_address = Account.recover_message(encoded_message, signature=signature)

            # Verify address matches
            return recovered_address.lower() == expected_address.lower()

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


# Singleton instance
_generator: EIP712SignatureGenerator | None = None


def get_signature_generator() -> EIP712SignatureGenerator:
    """
    Get the singleton signature generator instance.

    Returns:
        EIP712SignatureGenerator instance
    """
    global _generator

    if _generator is None:
        # Get private key from environment (development only)
        private_key = getattr(settings, 'agent_wallet_private_key', None)
        _generator = EIP712SignatureGenerator(private_key=private_key)

    return _generator

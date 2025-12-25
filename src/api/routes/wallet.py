"""
Wallet management API routes.

This module provides endpoints for checking wallet balances, allowances,
executing transfers, and viewing transaction history.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.models.payments import Payment
from src.services.wallet_service import WalletService

router = APIRouter()
logger = logging.getLogger(__name__)

# Use the default wallet address from config
# In production, this comes from the authenticated user
DEFAULT_WALLET_ADDRESS = settings.default_wallet_address


class TokenBalance(BaseModel):
    """Token balance information."""

    token_address: str
    token_symbol: str
    balance: float
    balance_usd: float | None = None


class WalletBalanceResponse(BaseModel):
    """Response for wallet balance query."""

    wallet_address: str
    balances: list[TokenBalance]
    total_balance_usd: float | None = None


class WalletAllowanceResponse(BaseModel):
    """Response for wallet allowance query."""

    wallet_address: str
    daily_limit_usd: float
    spent_today_usd: float
    remaining_allowance_usd: float
    resets_at: str


class TransferRequest(BaseModel):
    """Request body for token transfer."""

    recipient: str = Field(..., description="Recipient wallet address")
    amount: float = Field(..., gt=0, description="Amount to transfer")
    token: str = Field(..., description="Token address to transfer")


class TransferResponse(BaseModel):
    """Response from a token transfer."""

    tx_hash: str
    status: str
    from_address: str
    to_address: str
    amount: float
    token: str


class TransactionInfo(BaseModel):
    """Information about a wallet transaction."""

    tx_hash: str
    from_address: str
    to_address: str
    amount: float
    token: str
    token_symbol: str
    status: str
    timestamp: str
    gas_used: int | None = None
    gas_price_gwei: float | None = None


class TransactionListResponse(BaseModel):
    """Response for listing transactions."""

    transactions: list[TransactionInfo]
    total: int
    offset: int
    limit: int


@router.get(
    "/balance",
    response_model=WalletBalanceResponse,
    summary="Get wallet balance",
    description="Get token balances for the configured wallet.",
)
async def get_wallet_balance(
    tokens: list[str] | None = Query(
        default=None, description="Specific token addresses to query"
    ),
    db: AsyncSession = Depends(get_db),
) -> WalletBalanceResponse:
    """
    Get wallet token balances.

    If no tokens are specified, returns balances for common tokens
    (CRO, USDC, etc.).

    NOTE: This is a mock implementation. In production, this would query
    the blockchain using web3.py or ethers.js.
    """
    # Mock token balances for common Cronos tokens
    mock_balances = {
        "0x...CRO": {
            "token_address": "0x...CRO",
            "token_symbol": "CRO",
            "balance": 1000.0,
            "balance_usd": 100.0,  # Assuming $0.10 per CRO
        },
        "0x...USDC": {
            "token_address": "0x...USDC",
            "token_symbol": "USDC",
            "balance": 500.0,
            "balance_usd": 500.0,
        },
        "0x...USDC.e": {
            "token_address": "0x...USDC.e",
            "token_symbol": "USDC.e",
            "balance": 250.0,
            "balance_usd": 250.0,
        },
    }

    # If specific tokens requested, filter mock data
    if tokens:
        balances = [mock_balances.get(t, {
            "token_address": t,
            "token_symbol": "UNKNOWN",
            "balance": 0.0,
            "balance_usd": 0.0,
        }) for t in tokens]
    else:
        balances = list(mock_balances.values())

    # Calculate total USD balance
    total_usd = sum(b.get("balance_usd", 0) for b in balances)

    return WalletBalanceResponse(
        wallet_address=DEFAULT_WALLET_ADDRESS,
        balances=[TokenBalance(**b) for b in balances],
        total_balance_usd=total_usd,
    )


@router.get(
    "/allowance",
    response_model=WalletAllowanceResponse,
    summary="Get daily allowance",
    description="Get remaining daily spending allowance.",
)
async def get_wallet_allowance(
    db: AsyncSession = Depends(get_db),
) -> WalletAllowanceResponse:
    """
    Get the remaining daily spending allowance for the wallet.

    NOTE: This is a mock implementation. In production, this would query
    the AgentWallet contract for daily limit and spent amount.
    """
    # Mock daily limit settings
    daily_limit_usd = 100.0

    # Query how much has been spent today from payments table
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(Payment)
        .where(Payment.agent_wallet == DEFAULT_WALLET_ADDRESS)
        .where(Payment.created_at >= start_of_day)
        .where(Payment.status == "confirmed")
    )
    payments = result.scalars().all()

    # Calculate total spent today (simplified - assumes all amounts are in USD)
    spent_today_usd = sum(float(p.amount) for p in payments)

    # Calculate remaining
    remaining_usd = max(0, daily_limit_usd - spent_today_usd)

    # Calculate when daily limit resets (next midnight UTC)
    tomorrow = now + timedelta(days=1)
    resets_at = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)

    return WalletAllowanceResponse(
        wallet_address=DEFAULT_WALLET_ADDRESS,
        daily_limit_usd=daily_limit_usd,
        spent_today_usd=spent_today_usd,
        remaining_allowance_usd=remaining_usd,
        resets_at=resets_at.isoformat(),
    )


@router.post(
    "/transfer",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Transfer tokens",
    description="Execute a token transfer from the wallet.",
)
async def transfer_tokens(
    request: TransferRequest,
    db: AsyncSession = Depends(get_db),
) -> TransferResponse:
    """
    Execute a token transfer.

    This will:
    1. Validate recipient address
    2. Validate sufficient balance
    3. Check daily spending limit
    4. Execute the transfer via AgentWallet contract
    5. Return the transaction hash

    NOTE: This is a mock implementation. In production, this would interact
    with the AgentWallet smart contract.
    """
    # Use WalletService for transfer with validation
    wallet_service = WalletService(db, wallet_address=DEFAULT_WALLET_ADDRESS)
    result = await wallet_service.transfer_tokens(
        recipient=request.recipient,
        amount=request.amount,
        token=request.token,
    )

    if not result["success"]:
        # Map error types to HTTP status codes
        error_type = result.get("error", "unknown")

        if error_type == "invalid_recipient":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Invalid recipient address"),
            )
        elif error_type == "insufficient_balance":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Insufficient balance"),
            )
        elif error_type == "daily_limit_exceeded":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result.get("message", "Daily spending limit exceeded"),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Transfer failed"),
            )

    return TransferResponse(
        tx_hash=result["tx_hash"],
        status=result["status"],
        from_address=result["from_address"],
        to_address=result["to_address"],
        amount=result["amount"],
        token=result["token"],
    )


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    summary="Get transaction history",
    description="Get wallet transaction history.",
)
async def get_transaction_history(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """Get wallet transaction history with pagination."""
    wallet_service = WalletService(db)
    result = await wallet_service.get_transaction_history(
        offset=offset,
        limit=limit,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to get transaction history"),
        )

    transactions = [
        TransactionInfo(**tx) for tx in result["transactions"]
    ]

    return TransactionListResponse(
        transactions=transactions,
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
    )


class EIP712Domain(BaseModel):
    """EIP-712 domain separator."""

    name: str | None = None
    version: str | None = None
    chainId: int | None = None
    verifyingContract: str | None = None


class EIP712Type(BaseModel):
    """EIP-712 type definition."""

    name: str
    type: str


class EIP712Message(BaseModel):
    """EIP-712 message data."""

    types: dict[str, list[EIP712Type]]
    primaryType: str
    domain: EIP712Domain
    message: dict[str, Any]


class EIP712SignRequest(BaseModel):
    """Request body for EIP-712 signature generation."""

    domain: EIP712Domain
    types: dict[str, list[EIP712Type]]
    message: dict[str, Any]


class EIP712SignResponse(BaseModel):
    """Response from EIP-712 signature generation."""

    signature: str
    signer: str
    signed_at: str


@router.post(
    "/sign-eip712",
    response_model=EIP712SignResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate EIP-712 signature",
    description="Generate an EIP-712 typed data signature for x402 payments or other operations.",
)
async def sign_eip712(
    request: EIP712SignRequest,
    db: AsyncSession = Depends(get_db),
) -> EIP712SignResponse:
    """
    Generate an EIP-712 signature for the provided typed data.

    This endpoint is used by Vercel Workflows to generate signatures for x402 payments.
    In production, this would use the wallet's private key to sign the data.

    The signature follows the EIP-712 standard:
    - Domain separator is hashed
    - Message type is hashed
    - Message data is hashed
    - All are signed together

    Returns:
        EIP712SignResponse: Contains the signature and signer address
    """
    import hashlib
    from eth_account import Account
    from eth_utils import to_bytes, to_hex

    # Get the agent wallet's private key from config
    # In production, this would be stored securely in a key management system
    private_key = settings.agent_wallet_private_key

    if not private_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Wallet private key not configured",
        )

    # Encode the EIP-712 data
    # This is a simplified implementation - in production use a proper EIP-712 library
    try:
        # Get signer address
        account = Account.from_key(private_key)
        signer = account.address

        # Create a deterministic signature for testing
        # In production, this would use account.sign_typed_data()
        # For now, we'll create a mock signature that follows EIP-712 format

        # Hash the domain
        domain_separator = _hash_eip712_domain(request.domain)

        # Hash the message
        message_hash = _hash_eip712_message(
            request.types,
            request.primaryType,
            request.message
        )

        # Combine and hash (EIP-712 structure)
        final_hash = to_bytes(hexstr=to_hex(
            hashlib.sha256(
                b'\x19\x01' + domain_separator + message_hash
            ).digest()
        ))

        # Sign the hash
        signed = account.signHash(final_hash)

        # Format signature as hex string with v, r, s components
        signature = to_hex(signed.signature)

        return EIP712SignResponse(
            signature=signature,
            signer=signer,
            signed_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"EIP-712 signature generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signature generation failed: {str(e)}",
        )


def _hash_eip712_domain(domain: EIP712Domain) -> bytes:
    """Hash EIP-712 domain separator."""
    import hashlib
    from eth_utils import to_bytes

    # EIP-712 domain type encoding
    domain_type = "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    domain_type_hash = hashlib.sha256(domain_type.encode()).digest()

    # Encode domain values
    name_hash = hashlib.sha256(domain.name.encode() if domain.name else b"").digest()
    version_hash = hashlib.sha256(domain.version.encode() if domain.version else b"").digest()
    chain_id_bytes = domain.chainId.to_bytes(32, 'big') if domain.chainId else b'\x00' * 32
    verifying_contract_bytes = to_bytes(hexstr=domain.verifyingContract) if domain.verifyingContract else b'\x00' * 20

    # Combine and hash
    encoded = domain_type_hash + name_hash + version_hash + chain_id_bytes + verifying_contract_bytes
    return hashlib.sha256(encoded).digest()


def _hash_eip712_message(types: dict[str, list[EIP712Type]], primary_type: str, message: dict) -> bytes:
    """Hash EIP-712 message data."""
    import hashlib
    from eth_utils import to_bytes

    # For simplicity, create a hash of the encoded data
    # In production, use a proper EIP-712 encoding library
    type_str = primary_type
    for type_name, fields in types.items():
        if type_name != primary_type:
            continue
        for field in fields:
            type_str += f"({field.type} {field.name})"

    type_hash = hashlib.sha256(type_str.encode()).digest()

    # Hash message values
    value_bytes = b''
    for key, value in message.items():
        if isinstance(value, str):
            if value.startswith('0x'):
                value_bytes += to_bytes(hexstr=value)
            else:
                value_bytes += hashlib.sha256(value.encode()).digest()
        elif isinstance(value, int):
            value_bytes += value.to_bytes(32, 'big')
        else:
            value_bytes += hashlib.sha256(str(value).encode()).digest()

    encoded = type_hash + value_bytes
    return hashlib.sha256(encoded).digest()

"""
Wallet management API routes.

This module provides endpoints for checking wallet balances, allowances,
executing transfers, and viewing transaction history.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.config import settings
from src.models.payments import Payment
from src.services.wallet_service import WalletService

router = APIRouter()

# Mock wallet address - in production this comes from authenticated user
MOCK_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


class TokenBalance(BaseModel):
    """Token balance information."""

    token_address: str
    token_symbol: str
    balance: float
    balance_usd: Optional[float] = None


class WalletBalanceResponse(BaseModel):
    """Response for wallet balance query."""

    wallet_address: str
    balances: list[TokenBalance]
    total_balance_usd: Optional[float] = None


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
    gas_used: Optional[int] = None
    gas_price_gwei: Optional[float] = None


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
    tokens: Optional[List[str]] = Query(
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
        wallet_address=MOCK_WALLET_ADDRESS,
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
        .where(Payment.agent_wallet == MOCK_WALLET_ADDRESS)
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
        wallet_address=MOCK_WALLET_ADDRESS,
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
    1. Validate sufficient balance
    2. Check daily spending limit
    3. Execute the transfer via AgentWallet contract
    4. Return the transaction hash

    NOTE: This is a mock implementation. In production, this would interact
    with the AgentWallet smart contract.
    """
    # Generate a mock transaction hash
    tx_hash = "0x" + uuid4().hex + "0" * 24

    # Create a payment record to track this transfer
    payment = Payment(
        id=uuid4(),
        agent_wallet=MOCK_WALLET_ADDRESS,
        service_id=None,  # Direct transfer, not to a service
        recipient=request.recipient,
        amount=request.amount,
        token=request.token,
        tx_hash=tx_hash,
        status="confirmed",  # Mock: always succeeds
    )
    db.add(payment)
    await db.commit()

    return TransferResponse(
        tx_hash=tx_hash,
        status="confirmed",
        from_address=MOCK_WALLET_ADDRESS,
        to_address=request.recipient,
        amount=request.amount,
        token=request.token,
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

"""
Wallet management API routes.

This module provides endpoints for checking wallet balances, allowances,
executing transfers, and viewing transaction history.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

router = APIRouter()


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
    """
    # TODO: Implement balance checking
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Balance checking not yet implemented",
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
    """Get the remaining daily spending allowance for the wallet."""
    # TODO: Implement allowance checking
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Allowance checking not yet implemented",
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
    """
    # TODO: Implement token transfer
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token transfer not yet implemented",
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
    # TODO: Implement transaction history
    return TransactionListResponse(
        transactions=[],
        total=0,
        offset=offset,
        limit=limit,
    )

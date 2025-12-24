"""
Payment API routes.

This module provides endpoints for viewing payment history, executing
x402 payments, and getting payment statistics.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.config import settings
from src.services.payment_service import PaymentService
from src.services.x402_service import X402PaymentService
from src.services.service_registry import ServiceRegistryService

router = APIRouter()
logger = logging.getLogger(__name__)


class PaymentInfo(BaseModel):
    """Information about a payment."""

    id: UUID
    agent_wallet: str
    service_id: Optional[UUID] = None
    recipient: str
    amount: float
    token: str
    tx_hash: Optional[str] = None
    status: str = Field(..., description="pending, confirmed, or failed")
    created_at: str


class PaymentListResponse(BaseModel):
    """Response for listing payments."""

    payments: list[PaymentInfo]
    total: int
    offset: int
    limit: int


class PaymentStats(BaseModel):
    """Payment statistics."""

    total_payments: int
    total_amount_usd: float
    confirmed_payments: int
    pending_payments: int
    failed_payments: int
    success_rate: float = Field(..., ge=0, le=1)


class ExecuteX402Request(BaseModel):
    """Request body for executing an x402 payment."""

    service_url: str = Field(..., description="URL of the service to pay")
    amount: float = Field(..., gt=0, description="Amount to pay")
    token: str = Field(..., description="Token address for payment")
    service_id: Optional[UUID] = Field(default=None, description="Service ID for reputation tracking")


class ExecuteX402Response(BaseModel):
    """Response from executing an x402 payment."""

    payment_id: UUID
    tx_hash: Optional[str] = None
    status: str
    service_response: Optional[dict] = None


@router.get(
    "/history",
    response_model=PaymentListResponse,
    summary="Get payment history",
    description="Get payment history with optional filtering.",
)
async def get_payment_history(
    status: Optional[str] = Query(
        default=None, description="Filter by status (pending, confirmed, failed)"
    ),
    start_date: Optional[datetime] = Query(default=None, description="Start date filter"),
    end_date: Optional[datetime] = Query(default=None, description="End date filter"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    """
    Get payment history with filtering options.

    Supports filtering by:
    - status: Payment status
    - start_date/end_date: Date range
    """
    payment_service = PaymentService(db)
    result = await payment_service.get_payment_history(
        status=status,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to get payment history"),
        )

    # Format payments
    payments = [
        PaymentInfo(**p) for p in result["payments"]
    ]

    return PaymentListResponse(
        payments=payments,
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
    )


@router.get(
    "/stats",
    response_model=PaymentStats,
    summary="Get payment statistics",
    description="Get aggregate statistics about payments.",
)
async def get_payment_stats(
    db: AsyncSession = Depends(get_db),
) -> PaymentStats:
    """Get aggregate payment statistics."""
    payment_service = PaymentService(db)
    result = await payment_service.get_payment_stats()

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to get payment stats"),
        )

    stats = result["stats"]
    return PaymentStats(**stats)


@router.get(
    "/{payment_id}",
    response_model=PaymentInfo,
    summary="Get payment details",
    description="Get detailed information about a specific payment.",
)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PaymentInfo:
    """Get details of a specific payment."""
    payment_service = PaymentService(db)
    result = await payment_service.get_payment(payment_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("message", f"Payment {payment_id} not found"),
        )

    return PaymentInfo(**result["payment"])


@router.post(
    "/x402",
    response_model=ExecuteX402Response,
    status_code=status.HTTP_200_OK,
    summary="Execute x402 payment",
    description="Execute an x402 payment flow to access a paid service.",
)
async def execute_x402_payment(
    request: ExecuteX402Request,
    db: AsyncSession = Depends(get_db),
) -> ExecuteX402Response:
    """
    Execute an x402 payment flow.

    This will:
    1. Request the service (may receive 402)
    2. Generate EIP-712 signature
    3. Submit payment to facilitator
    4. Retry request with payment header
    5. Create payment record in database
    6. Update service reputation if successful
    7. Return service response

    NOTE: This is a mock implementation. In production, this would
    interact with the actual x402 facilitator.
    """
    payment_service = PaymentService(db)
    x402_service = X402PaymentService()
    registry_service = ServiceRegistryService(db)

    # Try to execute payment and ALWAYS create a payment record
    payment_success = False
    payment_status = "failed"
    tx_hash = None
    error_message = None

    try:
        result = await x402_service.execute_payment(
            service_url=request.service_url,
            amount=request.amount,
            token=request.token,
        )

        if result["success"]:
            payment_success = True
            payment_status = result.get("status", "confirmed")
            tx_hash = result.get("tx_hash")
        else:
            error_message = result.get("message", "x402 payment execution failed")
    except Exception as e:
        error_message = str(e)
        logger.error(f"x402 payment execution exception: {e}")

    # Always create payment record
    try:
        payment = await payment_service.create_payment(
            agent_wallet=settings.default_wallet_address,
            recipient=request.service_url,
            amount=request.amount,
            token=request.token,
            service_id=request.service_id,
            tx_hash=tx_hash,
            status=payment_status,
        )

        if payment_success:
            # Update service reputation if service_id is provided
            if request.service_id:
                try:
                    # Use a default rating of 4.5 for successful payments
                    # In production, this could be based on actual service quality
                    await registry_service.update_service_reputation(
                        str(request.service_id), 4.5
                    )
                    logger.info(f"Updated reputation for service {request.service_id}")
                except Exception as e:
                    logger.warning(f"Failed to update service reputation: {e}")

            return ExecuteX402Response(
                payment_id=payment.id,
                tx_hash=tx_hash,
                status=payment_status,
                service_response=result.get("service_response") if payment_success else None,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message or "x402 payment execution failed",
            )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Failed to create payment record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment record: {str(e)}",
        )

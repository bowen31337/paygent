"""
Payment API routes.

This module provides endpoints for viewing payment history, executing
x402 payments, and getting payment statistics.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.services.payment_service import PaymentService
from src.services.service_registry import ServiceRegistryService
from src.services.x402_service import X402PaymentService

router = APIRouter()
logger = logging.getLogger(__name__)


class PaymentInfo(BaseModel):
    """Information about a payment."""

    id: UUID
    agent_wallet: str
    service_id: UUID | None = None
    recipient: str
    amount: float
    token: str
    tx_hash: str | None = None
    status: str = Field(..., description="pending, confirmed, or failed")
    created_at: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "agent_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                    "service_id": "123e4567-e89b-12d3-a456-426614174001",
                    "recipient": "https://api.example.com/service",
                    "amount": 10.0,
                    "token": "USDC",
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "status": "confirmed",
                    "created_at": "2025-01-15T10:30:00Z"
                }
            ]
        }
    }


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
    service_id: UUID | None = Field(default=None, description="Service ID for reputation tracking")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "service_url": "https://api.marketdata.example.com/v1/price",
                    "amount": 0.50,
                    "token": "USDC",
                    "service_id": "123e4567-e89b-12d3-a456-426614174000"
                }
            ]
        }
    }


class ExecuteX402Response(BaseModel):
    """Response from executing an x402 payment."""

    payment_id: UUID
    tx_hash: str | None = None
    status: str
    service_response: dict | None = None


@router.get(
    "/history",
    response_model=PaymentListResponse,
    summary="Get payment history",
    description="Get payment history with optional filtering.",
)
async def get_payment_history(
    status: str | None = Query(
        default=None, description="Filter by status (pending, confirmed, failed)"
    ),
    start_date: datetime | None = Query(default=None, description="Start date filter"),
    end_date: datetime | None = Query(default=None, description="End date filter"),
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


class ExecuteApprovedPaymentRequest(BaseModel):
    """Request to execute a payment that has been approved."""

    approval_id: UUID
    edited_args: dict | None = None


class ExecuteApprovedPaymentResponse(BaseModel):
    """Response for executing an approved payment."""

    payment_id: UUID
    approval_id: UUID
    success: bool
    message: str
    tx_hash: str | None = None
    status: str


@router.post(
    "/execute-approved",
    response_model=ExecuteApprovedPaymentResponse,
    summary="Execute approved payment",
    description="Execute a payment that has been approved via HITL workflow.",
)
async def execute_approved_payment(
    request: ExecuteApprovedPaymentRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteApprovedPaymentResponse:
    """
    Execute a payment that has been approved via HITL workflow.

    This endpoint is called after a payment approval request has been
    approved by a human operator.
    """

    from src.services.approval_service import ApprovalService

    try:
        # Get the approval request
        approval_service = ApprovalService(db)
        approval = await approval_service.get_approval_request(request.approval_id)

        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval request {request.approval_id} not found"
            )

        if approval.decision != "approved" and approval.decision != "edited":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval request {request.approval_id} is not approved (status: {approval.decision})"
            )

        # Use edited args if provided, otherwise use original args
        payment_args = request.edited_args or approval.tool_args

        # Extract payment parameters
        service_url = payment_args.get("service_url")
        amount = payment_args.get("amount")
        token = payment_args.get("token", "USDC")

        if not service_url or amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment arguments in approval request"
            )

        # Execute the payment using x402 service
        x402_service = X402PaymentService()
        result = await x402_service.execute_payment(
            service_url=service_url,
            amount=amount,
            token=token,
            description=payment_args.get("description", f"Approved payment for {service_url}"),
        )

        # Create payment record
        payment_service = PaymentService(db)
        payment = await payment_service.create_payment(
            agent_wallet=settings.default_wallet_address,
            recipient=service_url,
            amount=amount,
            token=token,
            service_id=None,  # Could be derived from service_url if needed
            tx_hash=result.get("tx_hash"),
            status=result.get("status", "confirmed" if result.get("success") else "failed"),
        )

        return ExecuteApprovedPaymentResponse(
            payment_id=payment.id,
            approval_id=request.approval_id,
            success=result.get("success", False),
            message=result.get("message", "Payment executed successfully"),
            tx_hash=result.get("tx_hash"),
            status=result.get("status", "confirmed" if result.get("success") else "failed"),
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Failed to execute approved payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute approved payment: {str(e)}",
        )


class PaymentStatusResponse(BaseModel):
    """Response for payment status check."""

    txHash: str
    confirmed: bool
    failed: bool
    blockNumber: int | None = None
    timestamp: str | None = None
    error: str | None = None

    model_config = {
        "populate_by_name": True,
    }


@router.get(
    "/status/{tx_hash}",
    response_model=PaymentStatusResponse,
    summary="Check payment status",
    description="Check the status of a payment transaction on the blockchain.",
)
async def get_payment_status(
    tx_hash: str,
    db: AsyncSession = Depends(get_db),
) -> PaymentStatusResponse:
    """
    Check the status of a payment transaction on the blockchain.

    This endpoint is used by Vercel Workflows to verify payment settlement.
    In production, this would query the blockchain to check transaction confirmation.

    Args:
        tx_hash: The transaction hash to check
        db: Database session

    Returns:
        PaymentStatusResponse: Transaction status information
    """
    from src.services.payment_service import PaymentService

    payment_service = PaymentService(db)

    # First check if we have this payment in our database
    result = await payment_service.get_payment_by_tx_hash(tx_hash)

    if result["success"] and result.get("payment"):
        payment = result["payment"]
        status = payment.get("status", "pending")

        # Map our status to workflow status
        if status == "confirmed":
            return PaymentStatusResponse(
                txHash=tx_hash,
                confirmed=True,
                failed=False,
                blockNumber=payment.get("block_number", 12345),  # Mock
                timestamp=payment.get("created_at"),
            )
        elif status == "failed":
            return PaymentStatusResponse(
                txHash=tx_hash,
                confirmed=False,
                failed=True,
                error=payment.get("error_message", "Payment failed"),
                timestamp=payment.get("created_at"),
            )
        else:  # pending
            return PaymentStatusResponse(
                txHash=tx_hash,
                confirmed=False,
                failed=False,
                timestamp=payment.get("created_at"),
            )

    # If not in database, check mock blockchain status
    # In production, this would use web3.py to query the actual blockchain
    logger.info(f"Payment {tx_hash} not found in database, checking mock blockchain")

    # Mock implementation - simulate blockchain check
    # For demo purposes, assume transactions with specific patterns are confirmed
    try:
        # Simple mock: if tx_hash ends in even digit, it's confirmed
        # This is just for testing the workflow integration
        last_char = tx_hash[-1]
        if last_char in '02468ace':
            return PaymentStatusResponse(
                txHash=tx_hash,
                confirmed=True,
                failed=False,
                blockNumber=12345,
                timestamp=datetime.utcnow().isoformat(),
            )
        elif last_char in '13579bdf':
            return PaymentStatusResponse(
                txHash=tx_hash,
                confirmed=False,
                failed=False,
                timestamp=datetime.utcnow().isoformat(),
            )
        else:
            return PaymentStatusResponse(
                txHash=tx_hash,
                confirmed=False,
                failed=True,
                error="Transaction not found",
            )
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return PaymentStatusResponse(
            txHash=tx_hash,
            confirmed=False,
            failed=True,
            error=str(e),
        )


class SubscriptionInfo(BaseModel):
    """Information about a subscription."""

    id: str
    user_id: str
    service_id: str
    amount: str
    token: str
    renewal_interval: int  # days
    next_renewal_date: str
    status: str = Field(..., description="active, paused, or cancelled")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "sub-123",
                    "user_id": "user-456",
                    "service_id": "https://api.example.com",
                    "amount": "10.0",
                    "token": "USDC",
                    "renewal_interval": 30,
                    "next_renewal_date": "2025-02-15T00:00:00Z",
                    "status": "active"
                }
            ]
        }
    }


class SubscriptionProgressRequest(BaseModel):
    """Request to save subscription renewal progress."""

    subscription_id: str
    renewal_count: int
    next_renewal_date: str

    model_config = {
        "populate_by_name": True,
        "alias_generator": lambda s: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(s.split("_"))
        ),
    }


class SubscriptionSuccessRequest(BaseModel):
    """Request to mark renewal as successful."""

    tx_hash: str
    renewal_date: str

    model_config = {
        "populate_by_name": True,
        "alias_generator": lambda s: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(s.split("_"))
        ),
    }


class SubscriptionResponse(BaseModel):
    """Response for subscription operations."""

    success: bool
    message: str


# Mock subscription storage for demo purposes
# In production, this would be in a database
_mock_subscriptions: dict[str, dict] = {
    "sub-123": {
        "id": "sub-123",
        "user_id": "user-456",
        "service_id": "https://api.example.com",
        "amount": "10.0",
        "token": "USDC",
        "renewal_interval": 30,
        "next_renewal_date": "2025-01-25T00:00:00Z",
        "status": "active",
        "renewal_count": 0,
    }
}


@router.get(
    "/subscription/{subscription_id}",
    response_model=SubscriptionInfo,
    summary="Get subscription details",
    description="Get details of a subscription for renewal processing.",
)
async def get_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionInfo:
    """
    Get subscription details.

    This endpoint is used by Vercel Workflows to get subscription details
    for renewal processing.

    Args:
        subscription_id: Subscription ID
        db: Database session

    Returns:
        SubscriptionInfo: Subscription details
    """
    # In production, query from database
    # For demo, return mock data
    subscription = _mock_subscriptions.get(subscription_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )

    return SubscriptionInfo(**subscription)


@router.post(
    "/subscription/progress",
    response_model=SubscriptionResponse,
    summary="Save renewal progress",
    description="Save progress of a subscription renewal.",
)
async def save_subscription_progress(
    request: SubscriptionProgressRequest,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """
    Save subscription renewal progress.

    This endpoint is used by Vercel Workflows to save progress
    after each renewal cycle.

    Args:
        request: Progress details
        db: Database session

    Returns:
        SubscriptionResponse: Success confirmation
    """
    logger.info(
        f"Saving renewal progress for {request.subscription_id}: "
        f"count={request.renewal_count}, next={request.next_renewal_date}"
    )

    # In production, update database
    # For demo, just log and return success
    if request.subscription_id in _mock_subscriptions:
        _mock_subscriptions[request.subscription_id]["renewal_count"] = request.renewal_count
        _mock_subscriptions[request.subscription_id]["next_renewal_date"] = request.next_renewal_date

    return SubscriptionResponse(
        success=True,
        message="Renewal progress saved successfully",
    )


@router.post(
    "/subscription/{subscription_id}/success",
    response_model=SubscriptionResponse,
    summary="Mark renewal as successful",
    description="Mark a subscription renewal as successful.",
)
async def mark_renewal_successful(
    subscription_id: str,
    request: SubscriptionSuccessRequest,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """
    Mark a subscription renewal as successful.

    This endpoint is used by Vercel Workflows after a successful renewal.

    Args:
        subscription_id: Subscription ID
        request: Success details
        db: Database session

    Returns:
        SubscriptionResponse: Success confirmation
    """
    logger.info(
        f"Renewal successful for {subscription_id}: "
        f"tx_hash={request.tx_hash}, date={request.renewal_date}"
    )

    # In production, update database with tx_hash and renewal date
    # For demo, just log and return success
    if subscription_id in _mock_subscriptions:
        _mock_subscriptions[subscription_id]["last_tx_hash"] = request.tx_hash
        _mock_subscriptions[subscription_id]["last_renewal_date"] = request.renewal_date

    return SubscriptionResponse(
        success=True,
        message="Renewal marked as successful",
    )


"""
Notification API routes.

This module provides endpoints for sending notifications, which are used
by Vercel Workflows to notify users about events like renewal failures.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.alerting_service import AlertSeverity, AlertType, alerting_service

router = APIRouter()
logger = logging.getLogger(__name__)


class RenewalFailureRequest(BaseModel):
    """Request body for renewal failure notification."""

    subscription_id: str = Field(..., description="Subscription ID that failed")
    error: str = Field(..., description="Error message")
    timestamp: str = Field(..., description="ISO timestamp of failure")


class RenewalFailureResponse(BaseModel):
    """Response for renewal failure notification."""

    success: bool
    message: str
    subscription_id: str


class NotificationResponse(BaseModel):
    """Generic notification response."""

    success: bool
    message: str
    notification_id: str | None = None


@router.post(
    "/renewal-failure",
    response_model=RenewalFailureResponse,
    summary="Send renewal failure notification",
    description="Send a notification when a subscription renewal fails.",
)
async def send_renewal_failure_notification(
    request: RenewalFailureRequest,
    db: AsyncSession = Depends(get_db),
) -> RenewalFailureResponse:
    """
    Send a notification when a subscription renewal fails.

    This endpoint is called by Vercel Workflows when a subscription renewal
    payment fails. It sends an alert through the configured alerting system.

    Args:
        request: Renewal failure details
        db: Database session

    Returns:
        RenewalFailureResponse: Confirmation of notification sent
    """
    try:
        # Send alert through alerting service
        alerting_service.send_alert(
            alert_type=AlertType.PAYMENT_FAILURE,
            severity=AlertSeverity.ERROR,
            message=f"Subscription renewal failed for {request.subscription_id}",
            details={
                "subscription_id": request.subscription_id,
                "error": request.error,
                "timestamp": request.timestamp,
            },
            correlation_id=f"renewal-{request.subscription_id}",
        )

        logger.error(
            f"Subscription renewal failure: {request.subscription_id}, "
            f"error: {request.error}"
        )

        return RenewalFailureResponse(
            success=True,
            message="Renewal failure notification sent successfully",
            subscription_id=request.subscription_id,
        )

    except Exception as e:
        logger.error(f"Failed to send renewal failure notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        )


@router.post(
    "/webhook",
    response_model=NotificationResponse,
    summary="Send webhook notification",
    description="Send a generic webhook notification for workflow events.",
)
async def send_webhook_notification(
    event_type: str,
    message: str,
    details: dict | None = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """
    Send a generic webhook notification.

    This endpoint can be used by workflows to send various types of
    notifications to configured webhooks.

    Args:
        event_type: Type of event
        message: Notification message
        details: Additional context
        db: Database session

    Returns:
        NotificationResponse: Confirmation of notification
    """
    try:
        # Log the notification
        logger.info(
            f"Webhook notification: {event_type} - {message} "
            f"(details: {details or {}})"
        )

        # In production, this would send to configured webhooks
        # For now, we just log and return success
        notification_id = f"notif-{datetime.utcnow().timestamp()}"

        return NotificationResponse(
            success=True,
            message="Notification sent successfully",
            notification_id=notification_id,
        )

    except Exception as e:
        logger.error(f"Failed to send webhook notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        )


@router.post(
    "/approval-request",
    response_model=NotificationResponse,
    summary="Send approval request notification",
    description="Send a notification requesting human approval for a workflow step.",
)
async def send_approval_request_notification(
    request_id: str,
    step_name: str,
    details: dict | None = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """
    Send a notification requesting human approval.

    This is called when a workflow step requires human-in-the-loop approval.

    Args:
        request_id: Approval request ID
        step_name: Name of the step requiring approval
        details: Additional context
        db: Database session

    Returns:
        NotificationResponse: Confirmation of notification
    """
    try:
        alerting_service.send_alert(
            alert_type=AlertType.AGENT_EXECUTION_FAILURE,
            severity=AlertSeverity.WARNING,
            message=f"Approval required for step: {step_name}",
            details={
                "request_id": request_id,
                "step_name": step_name,
                "details": details or {},
            },
            correlation_id=request_id,
        )

        logger.info(f"Approval request sent: {request_id} for {step_name}")

        return NotificationResponse(
            success=True,
            message="Approval request notification sent",
            notification_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to send approval notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        )

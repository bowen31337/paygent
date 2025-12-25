"""
Subscription Renewal API

This module provides APIs for managing subscription renewals including
automatic renewal triggering, manual renewal requests, and subscription
status management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db, get_current_user
from src.core.blockchain_errors import BlockchainErrorHandler
from src.models.agent_sessions import ServiceSubscription
from src.services.subscription_service import SubscriptionService
from src.services.x402_service import X402PaymentService
from src.services.notification_service import NotificationService
from src.services.service_registry import ServiceRegistryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


class SubscriptionRenewalRequest:
    """Request model for subscription renewal."""
    subscription_id: str
    auto_renew: bool = True
    max_renewal_attempts: int = 3


class SubscriptionRenewalResponse:
    """Response model for subscription renewal."""
    success: bool
    subscription_id: str
    status: str
    tx_hash: Optional[str] = None
    message: str


@router.post("/renew/{subscription_id}", response_model=SubscriptionRenewalResponse)
async def renew_subscription(
    subscription_id: str,
    request: SubscriptionRenewalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Renew a specific subscription.

    Args:
        subscription_id: ID of the subscription to renew
        request: Renewal request parameters
        background_tasks: Background task manager
        db: Database session
        user_id: Current user ID

    Returns:
        Renewal result with transaction details
    """
    subscription_service = SubscriptionService(db)
    payment_service = X402PaymentService()
    notification_service = NotificationService()
    blockchain_error_handler = BlockchainErrorHandler()

    try:
        # Validate subscription ID format
        try:
            sub_id = UUID(subscription_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid subscription ID format: {subscription_id}"
            )

        # Get subscription details
        subscription = await subscription_service.get_subscription(sub_id)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=f"Subscription {subscription_id} not found"
            )

        # Check if user owns the subscription
        if str(subscription.session_id) != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to renew this subscription"
            )

        # Check subscription status
        if subscription.status != "active":
            return SubscriptionRenewalResponse(
                success=False,
                subscription_id=subscription_id,
                status="invalid_status",
                message=f"Cannot renew subscription with status: {subscription.status}"
            )

        # Check if subscription is expired
        if subscription.expires_at <= datetime.utcnow():
            return SubscriptionRenewalResponse(
                success=False,
                subscription_id=subscription_id,
                status="expired",
                message="Subscription has already expired"
            )

        # Process renewal
        renewal_result = await process_subscription_renewal(
            subscription,
            subscription_service,
            payment_service,
            notification_service,
            blockchain_error_handler,
            request.max_renewal_attempts
        )

        # Schedule background renewal check if auto_renew is enabled
        if request.auto_renew:
            background_tasks.add_task(
                schedule_future_renewal,
                subscription_id,
                db
            )

        return renewal_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Renewal failed for {subscription_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during renewal"
        )


@router.post("/auto-renewal/trigger")
async def trigger_auto_renewal(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Trigger automatic renewal for all expiring subscriptions.

    Args:
        background_tasks: Background task manager
        db: Database session
        user_id: Current user ID

    Returns:
        Trigger result summary
    """
    subscription_service = SubscriptionService(db)
    blockchain_error_handler = BlockchainErrorHandler()

    try:
        # Get expiring subscriptions for this user
        expiring_subscriptions = await subscription_service.get_expiring_subscriptions(24)

        # Filter by user
        user_subscriptions = [
            sub for sub in expiring_subscriptions
            if str(sub.session_id) == user_id
        ]

        if not user_subscriptions:
            return {
                "message": "No subscriptions expiring soon",
                "count": 0,
                "user_id": user_id
            }

        # Process renewals in background
        background_tasks.add_task(
            process_bulk_renewals,
            user_subscriptions,
            subscription_service,
            blockchain_error_handler
        )

        return {
            "message": f"Started renewal process for {len(user_subscriptions)} subscriptions",
            "count": len(user_subscriptions),
            "user_id": user_id
        }

    except Exception as e:
        logger.error(f"Auto-renewal trigger failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to trigger auto-renewal"
        )


@router.get("/expiring/{hours}")
async def get_expiring_subscriptions(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get subscriptions expiring within the specified hours.

    Args:
        hours: Number of hours to look ahead
        db: Database session
        user_id: Current user ID

    Returns:
        List of expiring subscriptions
    """
    subscription_service = SubscriptionService(db)

    try:
        expiring_subscriptions = await subscription_service.get_expiring_subscriptions(hours)

        # Filter by user
        user_subscriptions = [
            sub for sub in expiring_subscriptions
            if str(sub.session_id) == user_id
        ]

        # Format response
        result = []
        for sub in user_subscriptions:
            result.append({
                "id": str(sub.id),
                "session_id": str(sub.session_id),
                "service_id": str(sub.service_id),
                "amount": float(sub.amount) if sub.amount else 0.0,
                "token": sub.token or "USDC",
                "expires_at": sub.expires_at.isoformat(),
                "status": sub.status,
                "renewal_interval_days": sub.renewal_interval_days or 30,
                "renewal_count": sub.renewal_count or 0
            })

        return result

    except Exception as e:
        logger.error(f"Failed to get expiring subscriptions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve expiring subscriptions"
        )


@router.post("/cancel/{subscription_id}")
async def cancel_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel a subscription.

    Args:
        subscription_id: ID of the subscription to cancel
        db: Database session
        user_id: Current user ID

    Returns:
        Cancellation result
    """
    subscription_service = SubscriptionService(db)

    try:
        # Validate subscription ID format
        try:
            sub_id = UUID(subscription_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid subscription ID format: {subscription_id}"
            )

        # Get subscription
        subscription = await subscription_service.get_subscription(sub_id)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=f"Subscription {subscription_id} not found"
            )

        # Check ownership
        if str(subscription.session_id) != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to cancel this subscription"
            )

        # Cancel subscription
        success = await subscription_service.cancel_subscription(sub_id)

        if success:
            return {
                "success": True,
                "subscription_id": subscription_id,
                "message": "Subscription cancelled successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to cancel subscription"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription cancellation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during cancellation"
        )


# Helper functions

async def process_subscription_renewal(
    subscription: ServiceSubscription,
    subscription_service: SubscriptionService,
    payment_service: X402PaymentService,
    notification_service: NotificationService,
    blockchain_error_handler: BlockchainErrorHandler,
    max_attempts: int = 3
) -> SubscriptionRenewalResponse:
    """Process a single subscription renewal."""
    attempts = 0

    while attempts < max_attempts:
        try:
            attempts += 1

            # Calculate renewal parameters
            renewal_amount = float(subscription.amount) if subscription.amount else 10.0
            renewal_token = subscription.token or "USDC"

            # Execute payment
            payment_result = await payment_service.execute_payment(
                service_url=f"https://api.example.com/subscriptions/{subscription.id}",
                amount=renewal_amount,
                token=renewal_token,
                description=f"Subscription renewal for {subscription.id}"
            )

            if not payment_result["success"]:
                raise Exception(f"Payment failed: {payment_result.get('message', 'Unknown error')}")

            # Renew subscription
            renewal_success = await subscription_service.renew_subscription(
                subscription.id,
                payment_result.get("tx_hash")
            )

            if renewal_success:
                return SubscriptionRenewalResponse(
                    success=True,
                    subscription_id=str(subscription.id),
                    status="renewed",
                    tx_hash=payment_result.get("tx_hash"),
                    message=f"Subscription renewed successfully for {renewal_amount} {renewal_token}"
                )
            else:
                raise Exception("Subscription renewal failed in database")

        except Exception as e:
            logger.error(f"Renewal attempt {attempts} failed for {subscription.id}: {e}")

            if attempts >= max_attempts:
                # Final failure - send notification
                await notification_service.send_renewal_failed_notification(
                    str(subscription.session_id),
                    f"Subscription {subscription.id}",
                    str(e)
                )

                return SubscriptionRenewalResponse(
                    success=False,
                    subscription_id=str(subscription.id),
                    status="failed",
                    message=f"Renewal failed after {max_attempts} attempts: {str(e)}"
                )

            # Wait before retry
            await asyncio.sleep(2 ** attempts)  # Exponential backoff


async def process_bulk_renewals(
    subscriptions: List[ServiceSubscription],
    subscription_service: SubscriptionService,
    blockchain_error_handler: BlockchainErrorHandler
):
    """Process multiple subscription renewals in bulk."""
    results = []

    for subscription in subscriptions:
        try:
            result = await process_subscription_renewal(
                subscription,
                subscription_service,
                None,  # Payment service would be injected
                None,  # Notification service would be injected
                blockchain_error_handler
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Bulk renewal failed for {subscription.id}: {e}")
            results.append({
                "subscription_id": str(subscription.id),
                "success": False,
                "status": "error",
                "message": str(e)
            })

    logger.info(f"Bulk renewal completed: {len(results)} subscriptions processed")
    return results


async def schedule_future_renewal(
    subscription_id: str,
    db: AsyncSession
):
    """Schedule future renewal checks for a subscription."""
    # This would integrate with a scheduler system
    logger.info(f"Scheduled future renewal checks for {subscription_id}")


async def get_service_details(service_id: UUID) -> Dict[str, Any]:
    """Get service details for renewal."""
    # This would fetch service details from the service registry
    return {
        "id": str(service_id),
        "name": f"Service {service_id}",
        "endpoint": f"https://api.example.com/services/{service_id}"
    }
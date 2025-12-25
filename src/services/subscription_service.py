"""
Subscription service for managing service subscriptions and automatic renewals.

This service handles subscription lifecycle including creation, renewal,
expiration checking, and access control.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_sessions import ServiceSubscription
from src.models.services import Service
from src.services.cache import CacheService

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing service subscriptions and renewals."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the subscription service.

        Args:
            db: Database session
        """
        self.db = db
        self.cache_service = CacheService()

    async def create_subscription(
        self,
        session_id: UUID,
        service_id: UUID,
        amount: float | None = None,
        token: str | None = None,
        renewal_interval_days: int = 30,
    ) -> ServiceSubscription | None:
        """
        Create a new subscription for a session.

        Args:
            session_id: Agent session ID
            service_id: Service ID to subscribe to
            amount: Payment amount for subscription
            token: Token symbol for payment
            renewal_interval_days: Renewal interval in days (default: 30)

        Returns:
            Created subscription or None if failed
        """
        try:
            expires_at = datetime.utcnow() + timedelta(days=renewal_interval_days)

            subscription = ServiceSubscription(
                id=uuid4(),
                session_id=session_id,
                service_id=service_id,
                status="active",
                expires_at=expires_at,
                amount=amount,
                token=token,
                renewal_interval_days=renewal_interval_days,
            )

            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(subscription)

            logger.info(
                f"Created subscription {subscription.id} for session {session_id} "
                f"to service {service_id}, expires {expires_at}"
            )

            # Invalidate cache
            await self.cache_service.delete_pattern(
                f"subscription:session:{session_id}:*"
            )

            return subscription

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create subscription: {e}")
            return None

    async def get_subscription(self, subscription_id: UUID) -> ServiceSubscription | None:
        """
        Get subscription by ID.

        Args:
            subscription_id: Subscription ID

        Returns:
            Subscription object if found
        """
        try:
            stmt = select(ServiceSubscription).where(
                ServiceSubscription.id == subscription_id
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get subscription {subscription_id}: {e}")
            return None

    async def get_session_subscriptions(
        self, session_id: UUID, include_expired: bool = False
    ) -> list[ServiceSubscription]:
        """
        Get all subscriptions for a session.

        Args:
            session_id: Agent session ID
            include_expired: Whether to include expired subscriptions

        Returns:
            List of subscriptions
        """
        try:
            # Check cache first
            cache_key = f"subscription:session:{session_id}:{include_expired}"
            cached = await self.cache_service.get(cache_key)
            if cached:
                return cached

            stmt = select(ServiceSubscription).where(
                ServiceSubscription.session_id == session_id
            )

            if not include_expired:
                stmt = stmt.where(
                    (ServiceSubscription.status == "active") |
                    (ServiceSubscription.expires_at > datetime.utcnow())
                )

            result = await self.db.execute(stmt)
            subscriptions = result.scalars().all()

            # Cache for 5 minutes
            await self.cache_service.set(cache_key, subscriptions, expiration=300)

            return list(subscriptions)

        except Exception as e:
            logger.error(f"Failed to get session subscriptions: {e}")
            return []

    async def is_subscription_active(
        self, session_id: UUID, service_id: UUID
    ) -> bool:
        """
        Check if a subscription is active for a session and service.

        Args:
            session_id: Agent session ID
            service_id: Service ID

        Returns:
            True if active subscription exists
        """
        try:
            # Check cache first
            cache_key = f"subscription:active:{session_id}:{service_id}"
            cached = await self.cache_service.get(cache_key)
            if cached is not None:
                return cached

            stmt = select(ServiceSubscription).where(
                ServiceSubscription.session_id == session_id,
                ServiceSubscription.service_id == service_id,
                ServiceSubscription.status == "active",
                ServiceSubscription.expires_at > datetime.utcnow(),
            )

            result = await self.db.execute(stmt)
            subscription = result.scalar_one_or_none()

            is_active = subscription is not None

            # Cache for 1 minute (shorter TTL for active status)
            await self.cache_service.set(cache_key, is_active, expiration=60)

            return is_active

        except Exception as e:
            logger.error(f"Failed to check subscription active status: {e}")
            return False

    async def get_expiring_subscriptions(
        self, hours_until_expiration: int = 24
    ) -> list[ServiceSubscription]:
        """
        Get subscriptions that will expire soon.

        Args:
            hours_until_expiration: Hours until expiration to check

        Returns:
            List of expiring subscriptions
        """
        try:
            cutoff_time = datetime.utcnow() + timedelta(hours=hours_until_expiration)

            stmt = select(ServiceSubscription).where(
                ServiceSubscription.status == "active",
                ServiceSubscription.expires_at <= cutoff_time,
                ServiceSubscription.expires_at > datetime.utcnow(),
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get expiring subscriptions: {e}")
            return []

    async def renew_subscription(
        self, subscription_id: UUID, tx_hash: str | None = None
    ) -> bool:
        """
        Renew a subscription by extending its expiration date.

        Args:
            subscription_id: Subscription ID to renew
            tx_hash: Optional transaction hash for payment

        Returns:
            True if renewal successful
        """
        try:
            subscription = await self.get_subscription(subscription_id)
            if not subscription:
                logger.error(f"Subscription {subscription_id} not found")
                return False

            if subscription.status != "active":
                logger.warning(
                    f"Cannot renew subscription {subscription_id} with status {subscription.status}"
                )
                return False

            # Calculate new expiration date
            current_expiration = subscription.expires_at or datetime.utcnow()
            renewal_interval = subscription.renewal_interval_days or 30

            new_expiration = current_expiration + timedelta(days=renewal_interval)

            # Update subscription with new expiration, tx_hash, and renewal tracking
            stmt = (
                update(ServiceSubscription)
                .where(ServiceSubscription.id == subscription_id)
                .values(
                    expires_at=new_expiration,
                    last_renewal_date=datetime.utcnow(),
                    last_tx_hash=tx_hash,
                    renewal_count=(subscription.renewal_count or 0) + 1,
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()

            # Invalidate cache
            await self.cache_service.delete_pattern(
                f"subscription:session:{subscription.session_id}:*"
            )
            await self.cache_service.delete_pattern(
                f"subscription:active:{subscription.session_id}:*"
            )

            logger.info(
                f"Renewed subscription {subscription_id}, new expiration: {new_expiration}, "
                f"tx_hash: {tx_hash}, renewal count: {subscription.renewal_count or 0 + 1}"
            )

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to renew subscription {subscription_id}: {e}")
            return False

    async def cancel_subscription(self, subscription_id: UUID) -> bool:
        """
        Cancel a subscription.

        Args:
            subscription_id: Subscription ID to cancel

        Returns:
            True if cancellation successful
        """
        try:
            subscription = await self.get_subscription(subscription_id)
            if not subscription:
                return False

            stmt = (
                update(ServiceSubscription)
                .where(ServiceSubscription.id == subscription_id)
                .values(status="cancelled")
            )
            await self.db.execute(stmt)
            await self.db.commit()

            # Invalidate cache
            await self.cache_service.delete_pattern(
                f"subscription:session:{subscription.session_id}:*"
            )
            await self.cache_service.delete_pattern(
                f"subscription:active:{subscription.session_id}:*"
            )

            logger.info(f"Cancelled subscription {subscription_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            return False

    async def check_and_expire_subscriptions(self) -> int:
        """
        Check for expired subscriptions and mark them as expired.

        Returns:
            Number of subscriptions expired
        """
        try:
            stmt = (
                update(ServiceSubscription)
                .where(
                    ServiceSubscription.status == "active",
                    ServiceSubscription.expires_at <= datetime.utcnow(),
                )
                .values(status="expired")
                .returning(ServiceSubscription.id)
            )

            result = await self.db.execute(stmt)
            expired_ids = result.scalars().all()
            await self.db.commit()

            if expired_ids:
                # Invalidate all subscription caches
                await self.cache_service.delete_pattern("subscription:*")
                logger.info(f"Expired {len(expired_ids)} subscriptions")

            return len(expired_ids)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to check and expire subscriptions: {e}")
            return 0

    async def get_subscription_stats(self, session_id: UUID) -> dict[str, Any]:
        """
        Get subscription statistics for a session.

        Args:
            session_id: Agent session ID

        Returns:
            Dictionary with subscription statistics
        """
        try:
            subscriptions = await self.get_session_subscriptions(
                session_id, include_expired=True
            )

            active_count = sum(
                1 for s in subscriptions
                if s.status == "active" and s.expires_at > datetime.utcnow()
            )
            expired_count = sum(
                1 for s in subscriptions
                if s.status == "expired" or s.expires_at <= datetime.utcnow()
            )
            cancelled_count = sum(
                1 for s in subscriptions if s.status == "cancelled"
            )

            return {
                "total": len(subscriptions),
                "active": active_count,
                "expired": expired_count,
                "cancelled": cancelled_count,
            }

        except Exception as e:
            logger.error(f"Failed to get subscription stats: {e}")
            return {"total": 0, "active": 0, "expired": 0, "cancelled": 0}

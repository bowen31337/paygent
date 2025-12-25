"""
Payment service for managing payment history and statistics.

This service provides functionality for querying payment history,
generating payment statistics, and managing payment records.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.payments import Payment

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for payment history and statistics."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the payment service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_payment_history(
        self,
        wallet_address: str | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get payment history with filtering and pagination.

        Args:
            wallet_address: Filter by wallet address
            status: Filter by payment status (pending, confirmed, failed)
            start_date: Filter by start date
            end_date: Filter by end date
            offset: Pagination offset
            limit: Max results to return

        Returns:
            Dict containing payment history
        """
        try:
            # Build query with filters
            query = select(Payment)

            # Apply filters
            conditions = []
            if wallet_address:
                conditions.append(Payment.agent_wallet == wallet_address)
            if status:
                conditions.append(Payment.status == status)
            if start_date:
                conditions.append(Payment.created_at >= start_date)
            if end_date:
                conditions.append(Payment.created_at <= end_date)

            if conditions:
                query = query.where(*conditions)

            # Get total count
            count_result = await self.db.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = count_result.scalar() or 0

            # Get paginated results
            query = query.order_by(Payment.created_at.desc())
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            payments = result.scalars().all()

            # Format response
            payment_list = []
            for payment in payments:
                payment_list.append({
                    "id": str(payment.id),
                    "agent_wallet": payment.agent_wallet,
                    "service_id": str(payment.service_id) if payment.service_id else None,
                    "recipient": payment.recipient,
                    "amount": payment.amount,
                    "token": payment.token,
                    "tx_hash": payment.tx_hash,
                    "status": payment.status,
                    "created_at": payment.created_at.isoformat(),
                })

            return {
                "success": True,
                "payments": payment_list,
                "total": total,
                "offset": offset,
                "limit": limit,
            }

        except Exception as e:
            logger.error(f"Failed to get payment history: {e}")
            return {
                "success": False,
                "error": str(e),
                "payments": [],
                "total": 0,
                "offset": offset,
                "limit": limit,
            }

    async def get_payment(
        self,
        payment_id: UUID,
    ) -> dict[str, Any]:
        """
        Get details of a specific payment.

        Args:
            payment_id: Payment ID

        Returns:
            Dict containing payment details or error
        """
        try:
            result = await self.db.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()

            if not payment:
                return {
                    "success": False,
                    "error": "payment_not_found",
                    "message": f"Payment {payment_id} not found",
                }

            return {
                "success": True,
                "payment": {
                    "id": str(payment.id),
                    "agent_wallet": payment.agent_wallet,
                    "service_id": str(payment.service_id) if payment.service_id else None,
                    "recipient": payment.recipient,
                    "amount": payment.amount,
                    "token": payment.token,
                    "tx_hash": payment.tx_hash,
                    "status": payment.status,
                    "created_at": payment.created_at.isoformat(),
                }
            }

        except Exception as e:
            logger.error(f"Failed to get payment: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get payment: {str(e)}",
            }

    async def get_payment_by_tx_hash(
        self,
        tx_hash: str,
    ) -> dict[str, Any]:
        """
        Get payment details by transaction hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Dict containing payment details or error
        """
        try:
            result = await self.db.execute(
                select(Payment).where(Payment.tx_hash == tx_hash)
            )
            payment = result.scalar_one_or_none()

            if not payment:
                return {
                    "success": False,
                    "error": "payment_not_found",
                    "message": f"Payment with tx_hash {tx_hash} not found",
                }

            return {
                "success": True,
                "payment": {
                    "id": str(payment.id),
                    "agent_wallet": payment.agent_wallet,
                    "service_id": str(payment.service_id) if payment.service_id else None,
                    "recipient": payment.recipient,
                    "amount": payment.amount,
                    "token": payment.token,
                    "tx_hash": payment.tx_hash,
                    "status": payment.status,
                    "created_at": payment.created_at.isoformat(),
                }
            }

        except Exception as e:
            logger.error(f"Failed to get payment by tx_hash: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get payment by tx_hash: {str(e)}",
            }

    async def get_payment_stats(
        self,
        wallet_address: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get payment statistics.

        Calculates aggregate statistics including total payments,
        success rates, and amounts over a time period.

        Args:
            wallet_address: Optional wallet address to filter by
            days: Number of days to look back (default: 30)

        Returns:
            Dict containing payment statistics
        """
        try:
            # Calculate date cutoff
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Build query
            conditions = [Payment.created_at >= cutoff_date]
            if wallet_address:
                conditions.append(Payment.agent_wallet == wallet_address)

            # Get count by status
            result = await self.db.execute(
                select(
                    Payment.status,
                    func.count(Payment.id).label('count')
                )
                .where(*conditions)
                .group_by(Payment.status)
            )

            status_counts = {row.status: row.count for row in result}

            total_payments = sum(status_counts.values())
            confirmed_payments = status_counts.get('confirmed', 0)
            pending_payments = status_counts.get('pending', 0)
            failed_payments = status_counts.get('failed', 0)

            # Calculate success rate
            success_rate = (
                confirmed_payments / total_payments
                if total_payments > 0
                else 0.0
            )

            # Get total amount (only confirmed payments)
            result = await self.db.execute(
                select(func.sum(Payment.amount))
                .where(*conditions)
                .where(Payment.status == 'confirmed')
            )
            total_amount = result.scalar() or 0.0

            return {
                "success": True,
                "stats": {
                    "total_payments": total_payments,
                    "total_amount_usd": round(total_amount, 2),
                    "confirmed_payments": confirmed_payments,
                    "pending_payments": pending_payments,
                    "failed_payments": failed_payments,
                    "success_rate": round(success_rate, 2),
                    "period_days": days,
                }
            }

        except Exception as e:
            logger.error(f"Failed to get payment stats: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": {
                    "total_payments": 0,
                    "total_amount_usd": 0.0,
                    "confirmed_payments": 0,
                    "pending_payments": 0,
                    "failed_payments": 0,
                    "success_rate": 0.0,
                    "period_days": days,
                }
            }

    async def create_payment(
        self,
        agent_wallet: str,
        recipient: str,
        amount: float,
        token: str,
        service_id: UUID | None = None,
        tx_hash: str | None = None,
        status: str = "pending",
    ) -> Payment:
        """
        Create a new payment record.

        Args:
            agent_wallet: Agent wallet address
            recipient: Recipient address
            amount: Payment amount
            token: Token symbol or address
            service_id: Optional service ID
            tx_hash: Optional transaction hash
            status: Payment status (default: pending)

        Returns:
            Created Payment object
        """
        payment = Payment(
            agent_wallet=agent_wallet,
            service_id=service_id,
            recipient=recipient,
            amount=amount,
            token=token,
            tx_hash=tx_hash,
            status=status,
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)

        logger.info(f"Created payment: {payment.id}")
        return payment

    async def update_payment_status(
        self,
        payment_id: UUID,
        status: str,
        tx_hash: str | None = None,
    ) -> Payment | None:
        """
        Update payment status.

        Args:
            payment_id: Payment ID
            status: New status
            tx_hash: Optional transaction hash

        Returns:
            Updated Payment object or None if not found
        """
        try:
            result = await self.db.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()

            if not payment:
                return None

            payment.status = status
            if tx_hash:
                payment.tx_hash = tx_hash

            await self.db.commit()
            await self.db.refresh(payment)

            logger.info(f"Updated payment {payment_id} status to {status}")
            return payment

        except Exception as e:
            logger.error(f"Failed to update payment status: {e}")
            await self.db.rollback()
            return None

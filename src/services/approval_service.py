"""
Approval service for Human-in-the-Loop (HITL) workflows.

This module provides services for managing approval requests, decisions, and notifications.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, AsyncGenerator
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.database import Base, async_session_maker
from src.models.agent_sessions import ApprovalRequest, AgentSession
from src.models.payments import Payment

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for managing approval requests and decisions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_approval_request(
        self,
        session_id: UUID,
        tool_name: str,
        tool_args: Dict[str, Any],
        amount: Optional[float] = None,
        token: Optional[str] = None,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        approval_request = ApprovalRequest(
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            decision="pending",
            amount=amount,
            token=token,
        )

        self.session.add(approval_request)
        await self.session.commit()
        await self.session.refresh(approval_request)

        logger.info(
            f"Created approval request {approval_request.id} for session {session_id}, tool {tool_name}"
        )

        return approval_request

    async def get_pending_approvals(self, session_id: Optional[UUID] = None) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        query = select(ApprovalRequest).where(ApprovalRequest.decision == "pending")

        if session_id:
            query = query.where(ApprovalRequest.session_id == session_id)

        query = query.order_by(ApprovalRequest.created_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_approval_request(self, approval_id: UUID) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        query = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def approve_request(
        self, approval_id: UUID, edited_args: Optional[Dict[str, Any]] = None
    ) -> Optional[ApprovalRequest]:
        """Approve an approval request."""
        query = (
            update(ApprovalRequest)
            .where(ApprovalRequest.id == approval_id, ApprovalRequest.decision == "pending")
            .values(
                decision="approved",
                edited_args=edited_args,
                decision_made_at=datetime.utcnow(),
            )
        )

        result = await self.session.execute(query)
        await self.session.commit()

        if result.rowcount > 0:
            logger.info(f"Approved request {approval_id}")
            # Get the updated request
            return await self.get_approval_request(approval_id)

        return None

    async def reject_request(self, approval_id: UUID) -> Optional[ApprovalRequest]:
        """Reject an approval request."""
        query = (
            update(ApprovalRequest)
            .where(ApprovalRequest.id == approval_id, ApprovalRequest.decision == "pending")
            .values(decision="rejected", decision_made_at=datetime.utcnow())
        )

        result = await self.session.execute(query)
        await self.session.commit()

        if result.rowcount > 0:
            logger.info(f"Rejected request {approval_id}")
            # Get the updated request
            return await self.get_approval_request(approval_id)

        return None

    async def get_session_approvals(
        self, session_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[ApprovalRequest]:
        """Get approval requests for a session."""
        query = (
            select(ApprovalRequest)
            .where(ApprovalRequest.session_id == session_id)
            .order_by(ApprovalRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def cleanup_expired_approvals(self, max_age_hours: int = 24) -> int:
        """Clean up expired approval requests (older than max_age_hours)."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        # Get expired pending requests
        expired_query = select(ApprovalRequest).where(
            ApprovalRequest.decision == "pending",
            ApprovalRequest.created_at < cutoff,
        )

        expired_result = await self.session.execute(expired_query)
        expired_requests = expired_result.scalars().all()

        # Mark as expired
        if expired_requests:
            for request in expired_requests:
                request.decision = "expired"
                request.decision_made_at = datetime.utcnow()

            await self.session.commit()
            logger.info(f"Cleaned up {len(expired_requests)} expired approval requests")

        return len(expired_requests)

    async def stream_pending_approvals(
        self, session_id: Optional[UUID] = None
    ) -> AsyncGenerator[ApprovalRequest, None]:
        """Stream pending approval requests in real-time."""
        while True:
            pending = await self.get_pending_approvals(session_id)
            for approval in pending:
                yield approval

            # Wait before checking again
            await asyncio.sleep(1)


class BudgetLimitService:
    """Service for managing budget limits and spending controls."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_session_budget(self, session_id: UUID) -> Dict[str, Any]:
        """Get session budget configuration."""
        session = await self._get_session(session_id)
        if not session:
            return {"enabled": False, "daily_limit": 0, "spent_today": 0, "currency": "USD"}

        config = session.config or {}
        budget_config = config.get("budget", {})

        return {
            "enabled": budget_config.get("enabled", False),
            "daily_limit": budget_config.get("daily_limit", 0),
            "spent_today": await self._get_daily_spent(session_id),
            "currency": budget_config.get("currency", "USD"),
        }

    async def check_budget_limit(
        self, session_id: UUID, amount: float, currency: str = "USD"
    ) -> bool:
        """Check if a transaction would exceed budget limits."""
        budget = await self.get_session_budget(session_id)

        if not budget["enabled"]:
            return True

        if budget["daily_limit"] <= 0:
            return True

        spent_today = budget["spent_today"]
        if spent_today + amount > budget["daily_limit"]:
            logger.warning(
                f"Budget limit exceeded for session {session_id}: "
                f"spent {spent_today}, trying to spend {amount}, limit {budget['daily_limit']}"
            )
            return False

        return True

    async def update_session_budget(
        self,
        session_id: UUID,
        enabled: bool = None,
        daily_limit: float = None,
        currency: str = None,
    ) -> bool:
        """Update session budget configuration."""
        session = await self._get_session(session_id)
        if not session:
            return False

        config = session.config or {}
        budget_config = config.get("budget", {})

        if enabled is not None:
            budget_config["enabled"] = enabled
        if daily_limit is not None:
            budget_config["daily_limit"] = daily_limit
        if currency is not None:
            budget_config["currency"] = currency

        config["budget"] = budget_config
        session.config = config

        await self.session.commit()
        logger.info(f"Updated budget config for session {session_id}: {budget_config}")

        return True

    async def _get_session(self, session_id: UUID) -> Optional[AgentSession]:
        """Get agent session by ID."""
        query = select(AgentSession).where(AgentSession.id == session_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_daily_spent(self, session_id: UUID) -> float:
        """Get amount spent today for a session."""
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())

        # Query payments for this session
        query = select(Payment).where(
            Payment.created_at >= start_of_day,
            Payment.session_id == session_id,
            Payment.status == "confirmed",
        )

        result = await self.session.execute(query)
        payments = result.scalars().all()

        total_spent = sum(payment.amount for payment in payments)
        return total_spent


async def get_approval_service() -> ApprovalService:
    """Get approval service instance."""
    async with async_session_maker() as session:
        return ApprovalService(session)


async def get_budget_service() -> BudgetLimitService:
    """Get budget limit service instance."""
    async with async_session_maker() as session:
        return BudgetLimitService(session)
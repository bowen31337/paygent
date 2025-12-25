"""
Session service for managing agent sessions.

This module provides business logic for creating, updating, and retrieving
agent sessions.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_sessions import (
    AgentSession,
    ApprovalRequest,
)
from src.models.execution_logs import ExecutionLog
from src.services.metrics_service import metrics_collector

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing agent sessions."""

    def __init__(self, db: AsyncSession):
        """Initialize the session service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_session(
        self,
        user_id: UUID,
        wallet_address: str | None = None,
        config: dict | None = None,
    ) -> AgentSession:
        """Create a new agent session.

        Args:
            user_id: User ID for the session
            wallet_address: Optional wallet address
            config: Optional session configuration

        Returns:
            Created AgentSession
        """
        session = AgentSession(
            id=uuid4(),
            user_id=user_id,
            wallet_address=wallet_address,
            config=config,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        # Record metrics
        metrics_collector.record_session_created()

        logger.info(f"Created session {session.id} for user {user_id}")
        return session

    async def get_session(self, session_id: UUID) -> AgentSession | None:
        """Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            AgentSession or None if not found
        """
        result = await self.db.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def update_session_last_active(self, session_id: UUID) -> bool:
        """Update the last_active timestamp of a session.

        Args:
            session_id: Session ID

        Returns:
            True if updated, False if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        # SQLAlchemy will auto-update last_active via onupdate
        session.last_active = session.last_active  # Trigger update
        await self.db.commit()
        return True

    async def list_sessions(
        self,
        user_id: UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AgentSession], int]:
        """List sessions with optional user filter and pagination.

        Args:
            user_id: Optional user ID filter
            offset: Pagination offset
            limit: Pagination limit (max 100)

        Returns:
            Tuple of (sessions, total_count)
        """
        limit = min(limit, 100)

        # Build query
        query = select(AgentSession)
        if user_id:
            query = query.where(AgentSession.user_id == user_id)

        # Get total count
        count_query = query.with_only_columns(AgentSession.id)
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())

        # Get paginated results
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        sessions = list(result.scalars().all())

        return sessions, total

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        await self.db.delete(session)
        await self.db.commit()
        logger.info(f"Deleted session {session_id}")
        return True

    async def log_execution(
        self,
        session_id: UUID,
        command: str,
        plan: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        result: dict[str, Any] | None = None,
        total_cost: float | None = None,
        duration_ms: int | None = None,
    ) -> ExecutionLog | None:
        """Log agent execution details.

        Args:
            session_id: Session ID
            command: Original command
            plan: Execution plan
            tool_calls: List of tool calls made
            result: Final execution result
            total_cost: Total execution cost in USD
            duration_ms: Execution duration in milliseconds

        Returns:
            Created execution log
        """
        try:
            execution_log = ExecutionLog(
                session_id=session_id,
                command=command,
                plan=plan,
                tool_calls=tool_calls,
                result=result,
                total_cost=total_cost,
                duration_ms=duration_ms,
            )

            self.db.add(execution_log)
            await self.db.flush()
            await self.db.refresh(execution_log)

            logger.info(f"Logged execution for session {session_id}")
            return execution_log

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to log execution: {e}")
            return None

    async def get_execution_logs(
        self,
        session_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ExecutionLog]:
        """Get execution logs with optional filtering.

        Args:
            session_id: Optional session ID to filter by
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of execution logs
        """
        try:
            from sqlalchemy import desc
            query = select(ExecutionLog)

            if session_id:
                query = query.where(ExecutionLog.session_id == session_id)

            query = query.order_by(desc(ExecutionLog.created_at)).offset(offset).limit(limit)
            result = await self.db.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get execution logs: {e}")
            return []

    async def request_approval(
        self,
        session_id: UUID,
        tool_name: str,
        tool_args: dict[str, Any],

    ) -> ApprovalRequest | None:
        """Request human approval for a tool call.

        Args:
            session_id: Session ID
            tool_name: Name of the tool requiring approval
            tool_args: Arguments for the tool


        Returns:
            Created approval request
        """
        try:
            approval_request = ApprovalRequest(
                session_id=session_id,
                tool_name=tool_name,
                tool_args=tool_args,

            )

            self.db.add(approval_request)
            await self.db.flush()
            await self.db.refresh(approval_request)

            logger.info(f"Created approval request for session {session_id}")
            return approval_request

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create approval request: {e}")
            return None

    async def get_pending_approvals(
        self, session_id: UUID | None = None
    ) -> list[ApprovalRequest]:
        """Get pending approval requests.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            List of pending approval requests
        """
        try:
            from sqlalchemy import desc
            query = select(ApprovalRequest).where(ApprovalRequest.decision == "pending")

            if session_id:
                query = query.where(ApprovalRequest.session_id == session_id)

            query = query.order_by(desc(ApprovalRequest.created_at))
            result = await self.db.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return []

    async def approve_request(
        self, request_id: UUID, edited_args: dict[str, Any] | None = None
    ) -> bool:
        """Approve an approval request.

        Args:
            request_id: Approval request ID
            edited_args: Optional edited arguments

        Returns:
            True if successful
        """
        try:
            stmt = (
                update(ApprovalRequest)
                .where(ApprovalRequest.id == request_id)
                .values(
                    decision="approved",
                    edited_args=edited_args,
                    decision_made_at=datetime.utcnow(),
                )
            )

            await self.db.execute(stmt)
            await self.db.commit()

            logger.info(f"Approved request: {request_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to approve request {request_id}: {e}")
            return False

    async def reject_request(self, request_id: UUID) -> bool:
        """Reject an approval request.

        Args:
            request_id: Approval request ID

        Returns:
            True if successful
        """
        try:
            stmt = (
                update(ApprovalRequest)
                .where(ApprovalRequest.id == request_id)
                .values(
                    decision="rejected",
                    decision_made_at=datetime.utcnow(),
                )
            )

            await self.db.execute(stmt)
            await self.db.commit()

            logger.info(f"Rejected request: {request_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to reject request {request_id}: {e}")
            return False

    async def get_session_summary(self, session_id: UUID) -> dict[str, Any]:
        """Get summary of session execution.

        Args:
            session_id: Session ID

        Returns:
            Session summary
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                return {"error": f"Session {session_id} not found"}

            # Get execution logs
            logs = await self.get_execution_logs(session_id=session_id)

            # Calculate summary metrics
            total_executions = len(logs)
            total_cost = sum(log.total_cost or 0 for log in logs)
            total_duration = sum(log.duration_ms or 0 for log in logs)

            # Get pending approvals
            pending_approvals = await self.get_pending_approvals(session_id=session_id)

            return {
                "session_id": str(session_id),
                "user_id": str(session.user_id) if session.user_id else None,
                "wallet_address": session.wallet_address,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
                "total_executions": total_executions,
                "total_cost_usd": total_cost,
                "total_duration_ms": total_duration,
                "pending_approvals": len(pending_approvals),
                "status": "active",
            }

        except Exception as e:
            logger.error(f"Failed to get session summary: {e}")
            return {"error": str(e)}

    async def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up old sessions and logs.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of cleaned up records
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

            # Delete old execution logs
            stmt = delete(ExecutionLog).where(ExecutionLog.created_at < cutoff_time)
            result = await self.db.execute(stmt)
            deleted_logs = result.rowcount

            # Delete old approval requests
            stmt = delete(ApprovalRequest).where(ApprovalRequest.created_at < cutoff_time)
            result = await self.db.execute(stmt)
            deleted_approvals = result.rowcount

            # Delete old sessions
            stmt = delete(AgentSession).where(AgentSession.last_active < cutoff_time)
            result = await self.db.execute(stmt)
            deleted_sessions = result.rowcount

            await self.db.commit()

            total_deleted = deleted_logs + deleted_approvals + deleted_sessions
            logger.info(f"Cleaned up {total_deleted} old records")

            return total_deleted

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0

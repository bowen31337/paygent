"""
Agent execution audit service.

This service provides functionality for tracking and retrieving agent execution logs
to maintain a complete audit trail of all agent operations.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.execution_logs import ExecutionLog, ToolCall

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing agent execution audit trails."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the audit service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_execution_log(
        self,
        session_id: UUID,
        command: str,
        plan: dict[str, Any] | None = None,
    ) -> ExecutionLog:
        """
        Create a new execution log entry.

        Args:
            session_id: Agent session ID
            command: Natural language command executed
            plan: Agent's execution plan (optional)

        Returns:
            Created ExecutionLog instance
        """
        try:
            log = ExecutionLog(
                session_id=session_id,
                command=command,
                plan=plan,
                created_at=datetime.utcnow(),
            )

            self.db.add(log)
            await self.db.commit()
            await self.db.refresh(log)

            logger.info(f"Created execution log {log.id} for session {session_id}")
            return log

        except Exception as e:
            logger.error(f"Failed to create execution log: {e}")
            await self.db.rollback()
            raise

    async def update_execution_log(
        self,
        log_id: UUID,
        tool_calls: list[dict[str, Any]] | None = None,
        result: dict[str, Any] | None = None,
        total_cost_usd: float | None = None,
        duration_ms: int | None = None,
    ) -> ExecutionLog:
        """
        Update an execution log with results.

        Args:
            log_id: Execution log ID
            tool_calls: List of tool calls made during execution
            result: Final execution result
            total_cost_usd: Total cost in USD
            duration_ms: Execution duration in milliseconds

        Returns:
            Updated ExecutionLog instance
        """
        try:
            # Get the log
            log_result = await self.db.execute(
                select(ExecutionLog).where(ExecutionLog.id == log_id)
            )
            log = log_result.scalar_one_or_none()

            if not log:
                raise ValueError(f"Execution log {log_id} not found")

            # Update fields
            if tool_calls is not None:
                log.tool_calls = tool_calls
            if result is not None:
                log.result = result
            if total_cost_usd is not None:
                log.total_cost_usd = total_cost_usd
            if duration_ms is not None:
                log.duration_ms = duration_ms

            await self.db.commit()
            await self.db.refresh(log)

            logger.info(f"Updated execution log {log_id}")
            return log

        except Exception as e:
            logger.error(f"Failed to update execution log: {e}")
            await self.db.rollback()
            raise

    async def record_tool_call(
        self,
        execution_log_id: UUID,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> ToolCall:
        """
        Record a tool call in the audit trail.

        Args:
            execution_log_id: Parent execution log ID
            tool_name: Name of the tool called
            tool_args: Arguments passed to the tool
            tool_result: Result returned by the tool
            success: Whether the tool call succeeded
            error_message: Error message if tool call failed
            duration_ms: Tool execution duration in milliseconds

        Returns:
            Created ToolCall instance
        """
        try:
            tool_call = ToolCall(
                execution_log_id=execution_log_id,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=tool_result,
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
                created_at=datetime.utcnow(),
            )

            self.db.add(tool_call)
            await self.db.commit()
            await self.db.refresh(tool_call)

            logger.debug(f"Recorded tool call {tool_call.id}: {tool_name}")
            return tool_call

        except Exception as e:
            logger.error(f"Failed to record tool call: {e}")
            await self.db.rollback()
            raise

    async def get_execution_log(self, log_id: UUID) -> dict[str, Any] | None:
        """
        Get an execution log by ID.

        Args:
            log_id: Execution log ID

        Returns:
            Dict containing execution log details or None
        """
        try:
            result = await self.db.execute(
                select(ExecutionLog).where(ExecutionLog.id == log_id)
            )
            log = result.scalar_one_or_none()

            if not log:
                return None

            return {
                "id": str(log.id),
                "session_id": str(log.session_id),
                "command": log.command,
                "plan": log.plan,
                "tool_calls": log.tool_calls,
                "result": log.result,
                "total_cost_usd": log.total_cost_usd,
                "duration_ms": log.duration_ms,
                "created_at": log.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get execution log: {e}")
            return None

    async def get_session_execution_logs(
        self,
        session_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Get all execution logs for a session.

        Args:
            session_id: Agent session ID
            offset: Pagination offset
            limit: Max results to return

        Returns:
            Dict containing execution logs for the session
        """
        try:
            # Get total count
            count_result = await self.db.execute(
                select(func.count())
                .where(ExecutionLog.session_id == session_id)
            )
            from sqlalchemy import func
            count_result = await self.db.execute(
                select(func.count(ExecutionLog.id))
                .where(ExecutionLog.session_id == session_id)
            )
            total = count_result.scalar() or 0

            # Get paginated logs
            result = await self.db.execute(
                select(ExecutionLog)
                .where(ExecutionLog.session_id == session_id)
                .order_by(ExecutionLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            logs = result.scalars().all()

            execution_logs = []
            for log in logs:
                execution_logs.append({
                    "id": str(log.id),
                    "command": log.command,
                    "result": log.result,
                    "total_cost_usd": log.total_cost_usd,
                    "duration_ms": log.duration_ms,
                    "created_at": log.created_at.isoformat(),
                })

            return {
                "session_id": str(session_id),
                "execution_logs": execution_logs,
                "total": total,
                "offset": offset,
                "limit": limit,
            }

        except Exception as e:
            logger.error(f"Failed to get session execution logs: {e}")
            return {
                "session_id": str(session_id),
                "execution_logs": [],
                "total": 0,
                "offset": offset,
                "limit": limit,
            }

    async def get_tool_calls(
        self,
        execution_log_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        Get all tool calls for an execution log.

        Args:
            execution_log_id: Execution log ID

        Returns:
            List of tool call details
        """
        try:
            result = await self.db.execute(
                select(ToolCall)
                .where(ToolCall.execution_log_id == execution_log_id)
                .order_by(ToolCall.created_at.asc())
            )
            tool_calls = result.scalars().all()

            return [
                {
                    "id": str(tc.id),
                    "tool_name": tc.tool_name,
                    "tool_args": tc.tool_args,
                    "tool_result": tc.tool_result,
                    "success": tc.success,
                    "error_message": tc.error_message,
                    "duration_ms": tc.duration_ms,
                    "created_at": tc.created_at.isoformat(),
                }
                for tc in tool_calls
            ]

        except Exception as e:
            logger.error(f"Failed to get tool calls: {e}")
            return []

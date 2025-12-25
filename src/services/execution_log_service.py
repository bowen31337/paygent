"""
Execution log service for managing agent execution records.

This service provides functionality for creating, retrieving, and analyzing
execution logs from agent operations.
"""
import logging
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ExecutionLog

logger = logging.getLogger(__name__)


class ExecutionLogService:
    """Service for managing execution logs."""

    def __init__(self, db: AsyncSession = None):
        self.db = db

    async def create_execution_log(
        self,
        session_id: str,
        command: str,
        plan: list[dict[str, Any]] | None = None,
        result: dict[str, Any] | None = None,
        total_cost: float | None = None,
        duration_ms: int | None = None
    ) -> ExecutionLog:
        """
        Create a new execution log.

        Args:
            session_id: Agent session ID
            command: Executed command
            plan: Execution plan
            result: Execution result
            total_cost: Total cost in USD
            duration_ms: Execution duration in milliseconds

        Returns:
            ExecutionLog: Created log record
        """
        try:
            execution_log = ExecutionLog(
                session_id=session_id,
                command=command,
                plan=plan,
                result=result,
                total_cost=total_cost,
                duration_ms=duration_ms
            )
            if self.db:
                self.db.add(execution_log)
                await self.db.commit()
                await self.db.refresh(execution_log)
            return execution_log
        except Exception as e:
            logger.error(f"Error creating execution log: {e}")
            if self.db:
                await self.db.rollback()
            raise

    async def get_execution_logs(
        self,
        session_id: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[ExecutionLog]:
        """
        Get execution logs with optional filtering.

        Args:
            session_id: Filter by session ID
            status: Filter by status
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            limit: Maximum number of logs to return
            offset: Number of logs to skip

        Returns:
            List[ExecutionLog]: List of execution logs
        """
        if not self.db:
            return []

        try:
            query = select(ExecutionLog)

            # Apply filters
            if session_id:
                query = query.where(ExecutionLog.session_id == session_id)
            if status:
                query = query.where(ExecutionLog.status == status)
            if start_date:
                query = query.where(ExecutionLog.created_at >= start_date)
            if end_date:
                query = query.where(ExecutionLog.created_at <= end_date)

            # Apply pagination
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            logs = result.scalars().all()
            return logs
        except Exception as e:
            logger.error(f"Error getting execution logs: {e}")
            return []

    async def get_execution_log(self, log_id: str) -> ExecutionLog | None:
        """Get specific execution log by ID."""
        if not self.db:
            return None

        try:
            result = await self.db.execute(
                select(ExecutionLog).where(ExecutionLog.id == log_id)
            )
            log = result.scalar_one_or_none()
            return log
        except Exception as e:
            logger.error(f"Error getting execution log {log_id}: {e}")
            return None

    async def update_execution_log(
        self,
        log_id: str,
        updates: dict[str, Any]
    ) -> ExecutionLog | None:
        """Update execution log."""
        if not self.db:
            return None

        try:
            log = await self.get_execution_log(log_id)
            if not log:
                return None

            # Update fields
            for key, value in updates.items():
                if hasattr(log, key):
                    setattr(log, key, value)

            await self.db.commit()
            await self.db.refresh(log)
            return log
        except Exception as e:
            logger.error(f"Error updating execution log {log_id}: {e}")
            if self.db:
                await self.db.rollback()
            return None

    async def delete_execution_log(self, log_id: str) -> bool:
        """Delete execution log."""
        if not self.db:
            return False

        try:
            log = await self.get_execution_log(log_id)
            if not log:
                return False

            await self.db.delete(log)
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting execution log {log_id}: {e}")
            if self.db:
                await self.db.rollback()
            return False

    async def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """
        Get execution summary for a session.

        Args:
            session_id: Agent session ID

        Returns:
            Dict: Summary statistics
        """
        if not self.db:
            return {"session_id": session_id, "total_executions": 0}

        try:
            # Get total logs for session
            total_logs = await self.db.execute(
                select(func.count()).select_from(ExecutionLog).where(
                    ExecutionLog.session_id == session_id
                )
            )
            total_executions = total_logs.scalar()

            if total_executions == 0:
                return {
                    "session_id": session_id,
                    "total_executions": 0,
                    "success_rate": 0,
                    "total_cost": 0,
                    "total_duration_ms": 0,
                    "average_duration_ms": 0,
                    "most_used_tool": None,
                    "tool_usage_count": 0
                }

            # Get successful executions
            successful_logs = await self.db.execute(
                select(func.count()).select_from(ExecutionLog).where(
                    and_(
                        ExecutionLog.session_id == session_id,
                        ExecutionLog.result.op('->>')('success') == 'true'
                    )
                )
            )
            successful_executions = successful_logs.scalar()

            # Get total cost and duration
            cost_duration = await self.db.execute(
                select(
                    func.sum(ExecutionLog.total_cost),
                    func.sum(ExecutionLog.duration_ms)
                ).select_from(ExecutionLog).where(
                    ExecutionLog.session_id == session_id
                )
            )
            cost_result = cost_duration.fetchone()
            total_cost = cost_result[0] or 0
            total_duration = cost_result[1] or 0

            # Get tool usage
            logs = await self.get_execution_logs(session_id)
            tool_usage = {}
            for log in logs:
                if log.result and "tool_calls" in log.result:
                    for tool_call in log.result["tool_calls"]:
                        tool_name = tool_call.get("tool_name", "unknown")
                        tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

            most_used_tool = max(tool_usage.items(), key=lambda x: x[1]) if tool_usage else None

            return {
                "session_id": session_id,
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
                "total_cost": float(total_cost) if total_cost else 0,
                "total_duration_ms": int(total_duration) if total_duration else 0,
                "average_duration_ms": int(total_duration / total_executions) if total_executions > 0 else 0,
                "most_used_tool": most_used_tool[0] if most_used_tool else None,
                "tool_usage_count": most_used_tool[1] if most_used_tool else 0
            }

        except Exception as e:
            logger.error(f"Error getting session summary for {session_id}: {e}")
            return {
                "session_id": session_id,
                "total_executions": 0,
                "success_rate": 0,
                "total_cost": 0,
                "total_duration_ms": 0,
                "average_duration_ms": 0,
                "most_used_tool": None,
                "tool_usage_count": 0
            }

    async def get_tool_usage_stats(
        self,
        session_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> dict[str, dict[str, int]]:
        """
        Get tool usage statistics.

        Args:
            session_id: Filter by session ID
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Dict: Tool usage statistics
        """
        if not self.db:
            return {}

        try:
            logs = await self.get_execution_logs(
                session_id=session_id,
                start_date=start_date,
                end_date=end_date
            )

            tool_stats = {}
            for log in logs:
                if log.result and "tool_calls" in log.result:
                    for tool_call in log.result["tool_calls"]:
                        tool_name = tool_call.get("tool_name", "unknown")
                        session_id = log.session_id

                        if session_id not in tool_stats:
                            tool_stats[session_id] = {}

                        tool_stats[session_id][tool_name] = tool_stats[session_id].get(tool_name, 0) + 1

            return tool_stats
        except Exception as e:
            logger.error(f"Error getting tool usage stats: {e}")
            return {}

    async def cleanup_old_logs(
        self,
        days_to_keep: int = 30,
        session_id: str | None = None
    ) -> int:
        """
        Clean up old execution logs.

        Args:
            days_to_keep: Number of days to keep logs
            session_id: Optional session ID to clean specific session

        Returns:
            int: Number of logs deleted
        """
        if not self.db:
            return 0

        try:
            from datetime import datetime, timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            query = select(ExecutionLog).where(
                ExecutionLog.created_at < cutoff_date
            )
            if session_id:
                query = query.where(ExecutionLog.session_id == session_id)

            result = await self.db.execute(query)
            logs_to_delete = result.scalars().all()

            for log in logs_to_delete:
                await self.db.delete(log)

            await self.db.commit()
            return len(logs_to_delete)
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            if self.db:
                await self.db.rollback()
            return 0

"""
Agent service for executing commands and managing agent execution.

This service provides the core functionality for executing natural language
commands through the deepagents framework and managing agent execution state.
"""
import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_sessions import AgentSession
from src.models.execution_logs import ExecutionLog

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing agent execution and state."""

    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.active_executions: dict[str, asyncio.Task] = {}

    async def execute_command(
        self,
        session_id: str,
        command: str,
        plan: list[dict[str, Any]] | None = None  # noqa: ARG002
    ) -> dict[str, Any]:
        """
        Execute a natural language command.

        Args:
            session_id: Agent session ID
            command: Natural language command to execute
            plan: Optional execution plan

        Returns:
            Dict containing execution result
        """
        try:
            # Import here to avoid circular dependency
            from src.agents.agent_executor_enhanced import execute_agent_command_enhanced

            # Get or create session
            session = await self.get_or_create_session(session_id)

            # Execute command using enhanced executor
            result = await execute_agent_command_enhanced(
                command=command,
                session_id=session.id,
                db=self.db,
                budget_limit_usd=None
            )

            return result

        except Exception as e:
            logger.error(f"Error executing command for session {session_id}: {e}")
            raise

    async def cancel_execution(
        self,
        session_id: str,
        execution_id: str
    ) -> bool:
        """
        Cancel an ongoing execution.

        Args:
            session_id: Agent session ID
            execution_id: Execution ID to cancel

        Returns:
            bool: True if cancelled successfully
        """
        try:
            # Check if execution is active
            if execution_id in self.active_executions:
                task = self.active_executions[execution_id]
                task.cancel()
                del self.active_executions[execution_id]
                logger.info(f"Cancelled execution {execution_id} for session {session_id}")
                return True

            logger.warning(f"Execution {execution_id} not found for session {session_id}")
            return False

        except Exception as e:
            logger.error(f"Error cancelling execution {execution_id}: {e}")
            return False

    async def get_session(self, session_id: str) -> AgentSession | None:
        """Get agent session by ID."""
        if not self.db:
            return None

        try:
            result = await self.db.execute(
                select(AgentSession).where(AgentSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            return session
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def get_or_create_session(self, session_id: str) -> AgentSession:
        """Get or create agent session."""
        session = await self.get_session(session_id)
        if session:
            return session

        # Create new session
        new_session = AgentSession(id=session_id)
        if self.db:
            self.db.add(new_session)
            await self.db.commit()
            await self.db.refresh(new_session)

        return new_session

    async def get_execution_logs(
        self,
        session_id: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[ExecutionLog]:
        """Get execution logs."""
        if not self.db:
            return []

        try:
            query = select(ExecutionLog)
            if session_id:
                query = query.where(ExecutionLog.session_id == session_id)

            query = query.offset(offset).limit(limit)
            result = await self.db.execute(query)
            logs = result.scalars().all()
            return logs
        except Exception as e:
            logger.error(f"Error getting execution logs: {e}")
            return []

    async def get_execution_log(self, log_id: str) -> ExecutionLog | None:
        """Get specific execution log."""
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

    async def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """Get session execution summary."""
        logs = await self.get_execution_logs(session_id)
        if not logs:
            return {"session_id": session_id, "total_executions": 0}

        total_executions = len(logs)
        successful_executions = sum(1 for log in logs if log.result and log.result.get("success", False))
        total_cost = sum(log.total_cost or 0 for log in logs)
        total_duration = sum(log.duration_ms or 0 for log in logs)

        # Get most used tools
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
            "total_cost": total_cost,
            "total_duration_ms": total_duration,
            "average_duration_ms": total_duration / total_executions if total_executions > 0 else 0,
            "most_used_tool": most_used_tool[0] if most_used_tool else None,
            "tool_usage_count": most_used_tool[1] if most_used_tool else 0
        }

    async def cleanup(self):
        """Clean up agent service."""
        # Cancel all active executions
        for task in self.active_executions.values():
            task.cancel()

        self.active_executions.clear()

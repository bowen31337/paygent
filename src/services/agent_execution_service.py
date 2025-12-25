"""
Agent Execution Service for Paygent.

This module provides services for executing agent commands and managing
agent sessions. It works with the basic agent implementation.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.basic_agent import BasicPaygentAgent
from src.core.config import settings
from src.models.agent_sessions import AgentSession
from src.services.session_service import SessionService

logger = logging.getLogger(__name__)


class AgentExecutionService:
    """Service for executing agent commands and managing sessions."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the agent execution service.

        Args:
            db: Database session
        """
        self.db = db
        self.session_service = SessionService(db)

    async def execute_command(
        self,
        command: str,
        user_id: UUID | None = None,
        budget_limit_usd: float | None = None,
        llm_model: str = "mock",
    ) -> dict[str, Any]:
        """
        Execute a natural language command using the agent.

        Args:
            command: Natural language command to execute
            user_id: Optional user ID for the session
            budget_limit_usd: Optional budget limit in USD
            llm_model: LLM model to use (mock for now)

        Returns:
            Dict containing execution result
        """
        try:
            # Create or get session
            session = await self._get_or_create_session(user_id)

            # Create agent
            agent = BasicPaygentAgent(
                db=self.db,
                session_id=session.id,
                llm_model=llm_model,
            )

            # Execute command
            result = await agent.execute_command(command, budget_limit_usd)

            # Update session last active time
            await self.session_service.update_session_last_active(session.id)

            # Return result with session info
            return {
                **result,
                "session_info": await agent.get_session_info(),
                "execution_summary": await agent.get_execution_summary(),
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(user_id) if user_id else None,
            }

    async def get_session_status(self, session_id: UUID) -> dict[str, Any]:
        """
        Get the status of an agent session.

        Args:
            session_id: Session ID to check

        Returns:
            Dict containing session status
        """
        try:
            session = await self.session_service.get_session(session_id)
            if not session:
                return {"error": f"Session {session_id} not found"}

            return {
                "session_id": str(session.id),
                "user_id": str(session.user_id) if session.user_id else None,
                "wallet_address": session.wallet_address,
                "config": session.config,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
                "status": "active",
            }

        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(session_id),
            }

    async def terminate_session(self, session_id: UUID) -> dict[str, Any]:
        """
        Terminate an agent session.

        Args:
            session_id: Session ID to terminate

        Returns:
            Dict containing termination result
        """
        try:
            # For now, just return success - in a real implementation,
            # we would clean up agent resources and mark session as terminated
            return {
                "success": True,
                "message": f"Session {session_id} terminated successfully",
                "session_id": str(session_id),
            }

        except Exception as e:
            logger.error(f"Failed to terminate session: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(session_id),
            }

    async def _get_or_create_session(self, user_id: UUID | None) -> AgentSession:
        """
        Get or create an agent session.

        Args:
            user_id: Optional user ID

        Returns:
            AgentSession instance
        """
        # For demo purposes, create a new session each time
        # In production, you might want to reuse sessions
        session_data = {
            "user_id": user_id,
            "wallet_address": settings.default_wallet_address,
            "config": {
                "daily_limit_usd": settings.default_daily_limit_usd,
                "max_iterations": settings.agent_max_iterations,
                "timeout_seconds": settings.agent_timeout_seconds,
            },
        }

        session = await self.session_service.create_session(session_data)
        return session

    async def list_sessions(self, user_id: UUID | None = None) -> dict[str, Any]:
        """
        List agent sessions.

        Args:
            user_id: Optional user ID to filter sessions

        Returns:
            Dict containing list of sessions
        """
        try:
            sessions = await self.session_service.list_sessions(user_id)
            session_list = []

            for session in sessions:
                session_info = {
                    "session_id": str(session.id),
                    "user_id": str(session.user_id) if session.user_id else None,
                    "wallet_address": session.wallet_address,
                    "config": session.config,
                    "created_at": session.created_at.isoformat(),
                    "last_active": session.last_active.isoformat(),
                }
                session_list.append(session_info)

            return {
                "success": True,
                "sessions": session_list,
                "total": len(session_list),
            }

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return {
                "success": False,
                "error": str(e),
            }

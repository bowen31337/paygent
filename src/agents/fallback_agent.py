"""
Fallback Agent Implementation for Paygent.

This module provides a fallback agent that works when langchain dependencies
fail to load, using the simple agent implementation.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.simple_agent import SimplePaygentAgent
from src.services.session_service import SessionService

logger = logging.getLogger(__name__)


class FallbackPaygentAgent:
    """
    Fallback Paygent Agent.

    Used when the main langchain-based agent fails to initialize.
    Provides basic payment orchestration functionality.
    """

    def __init__(
        self,
        db: AsyncSession,
        session_id: UUID,
        llm_model: str = "anthropic/claude-sonnet-4",
    ):
        """
        Initialize the fallback agent.

        Args:
            db: Database session
            session_id: Session ID for this execution
            llm_model: LLM model to use (for future compatibility)
        """
        self.db = db
        self.session_id = session_id
        self.session_service = SessionService(db)
        self.llm_model = llm_model

        # Use simple agent as fallback
        self.simple_agent = SimplePaygentAgent(db, session_id, llm_model)

        logger.warning(f"Fallback agent initialized for session {session_id} - langchain unavailable")

    async def execute_command(
        self, command: str, budget_limit_usd: float | None = None
    ) -> dict[str, Any]:
        """
        Execute a natural language command using the fallback agent.

        Args:
            command: Natural language command to execute
            budget_limit_usd: Optional budget limit in USD

        Returns:
            Dict containing execution result
        """
        try:
            logger.info(f"Session {self.session_id}: Using fallback agent for command - {command}")

            # Log that we're using fallback
            result = await self.simple_agent.execute_command(command, budget_limit_usd)

            # Add fallback information to result
            if "success" in result:
                result["agent_type"] = "Fallback Paygent Agent"
                result["note"] = "Using fallback implementation due to langchain dependency issues"

            return result

        except Exception as e:
            logger.error(f"Session {self.session_id}: Fallback agent execution failed - {e}")
            return {
                "success": False,
                "error": f"Fallback agent failed: {str(e)}",
                "session_id": str(self.session_id),
                "agent_type": "Fallback Paygent Agent",
            }

    async def get_session_info(self) -> dict[str, Any]:
        """Get current session information."""
        return await self.simple_agent.get_session_info()

    async def get_execution_summary(self) -> dict[str, Any]:
        """Get execution summary for this agent."""
        summary = await self.simple_agent.get_execution_summary()
        summary["note"] = "Using fallback agent implementation"
        return summary

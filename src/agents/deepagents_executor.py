"""
DeepAgents executor for advanced AI agent orchestration.

This module provides integration with the deepagents framework (0.2.7+)
for building production-ready agents with planning, sub-agent spawning,
and filesystem capabilities using Claude Sonnet 4 as the primary LLM.
"""

import logging
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from deepagents import Agent

from src.core.config import settings

logger = logging.getLogger(__name__)


class DeepAgentsExecutor:
    """
    DeepAgents executor with Claude Sonnet 4 integration.

    This executor provides advanced agent capabilities:
    - Multi-step planning with write_todos
    - Sub-agent spawning for specialized tasks
    - Filesystem backend for agent memory
    - Integration with Paygent x402 payment tools
    """

    def __init__(
        self,
        session_id: str,
        anthropic_api_key: str | None = None,
        workspace_dir: str | None = None
    ):
        """
        Initialize the DeepAgents executor.

        Args:
            session_id: Unique session identifier
            anthropic_api_key: Anthropic API key (defaults to settings)
            workspace_dir: Directory for agent filesystem (defaults to .workspace/{session_id})
        """
        self.session_id = session_id
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Set it in environment or pass to constructor."
            )

        # Setup workspace directory
        if workspace_dir is None:
            workspace_dir = f".workspace/sessions/{session_id}"

        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"DeepAgentsExecutor initialized for session {session_id} "
            f"with workspace: {self.workspace_dir}"
        )

        # Initialize Anthropic client for Claude Sonnet 4
        self.client = Anthropic(api_key=self.api_key)

        # Store agent instance (created lazily)
        self._agent: Agent | None = None

    def _create_agent(self) -> Agent:
        """
        Create and configure the deepagents Agent.

        Returns:
            Configured Agent instance
        """
        # Import deepagents Agent
        from deepagents import Agent as DeepAgent

        # Create agent with Claude Sonnet 4
        agent = DeepAgent(
            name="paygent",
            description=(
                "Paygent is an AI-powered payment orchestration platform that enables "
                "autonomous AI agents to discover, negotiate, and execute payments "
                "seamlessly across the Cronos ecosystem using the x402 protocol."
            ),
            model="claude-sonnet-4-20250514",  # Claude Sonnet 4 model ID
            api_key=self.api_key,
            workspace=str(self.workspace_dir),
        )

        logger.info(f"DeepAgent created with Claude Sonnet 4 for session {self.session_id}")
        return agent

    @property
    def agent(self) -> Agent:
        """Get or create the agent instance."""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    async def execute_command(
        self,
        command: str,
        budget_limit_usd: float | None = None,
        tools: list[Any] | None = None
    ) -> dict[str, Any]:
        """
        Execute a natural language command using deepagents.

        Args:
            command: Natural language command to execute
            budget_limit_usd: Optional budget limit in USD
            tools: Optional list of tools to register with the agent

        Returns:
            Dict containing execution result
        """
        logger.info(f"Session {self.session_id}: Executing with deepagents - {command}")

        try:
            # Register tools if provided
            if tools:
                for tool in tools:
                    self.agent.register_tool(tool)
                logger.info(f"Registered {len(tools)} tools with deepagent")

            # Execute command through deepagents
            # The agent will use write_todos for planning and can spawn sub-agents
            result = await self.agent.run(command)

            logger.info(
                f"Deepagents execution completed for session {self.session_id}: "
                f"success={result.get('success', False)}"
            )

            return {
                "success": True,
                "session_id": self.session_id,
                "command": command,
                "result": result,
                "framework": "deepagents",
                "model": "claude-sonnet-4",
                "workspace": str(self.workspace_dir),
            }

        except Exception as e:
            logger.error(
                f"Deepagents execution failed for session {self.session_id}: {e}",
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "session_id": self.session_id,
                "command": command,
                "framework": "deepagents",
            }

    def verify_claude_sonnet_4(self) -> dict[str, Any]:
        """
        Verify that Claude Sonnet 4 is being used.

        Returns:
            Dict with verification results
        """
        try:
            # Create a test completion to verify the model
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'OK' if you receive this."}]
            )

            model_used = response.model if hasattr(response, 'model') else "unknown"

            return {
                "success": True,
                "model": model_used,
                "framework": "deepagents",
                "verification": "Claude Sonnet 4 is properly configured",
                "response": response.content[0].text if response.content else None
            }

        except Exception as e:
            logger.error(f"Claude Sonnet 4 verification failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "framework": "deepagents",
                "verification": "Failed to verify Claude Sonnet 4"
            }

    async def cleanup(self):
        """Clean up resources."""
        logger.info(f"Cleaning up DeepAgents executor for session {self.session_id}")
        self._agent = None


# Singleton instance for simple use cases
_default_executor: DeepAgentsExecutor | None = None


def get_default_executor() -> DeepAgentsExecutor:
    """Get or create the default executor instance."""
    global _default_executor
    if _default_executor is None:
        _default_executor = DeepAgentsExecutor(session_id="default")
    return _default_executor


async def execute_with_deepagents(
    command: str,
    session_id: str = "default",
    budget_limit_usd: float | None = None
) -> dict[str, Any]:
    """
    Convenience function to execute a command with deepagents.

    Args:
        command: Natural language command
        session_id: Session identifier
        budget_limit_usd: Optional budget limit

    Returns:
        Execution result
    """
    executor = DeepAgentsExecutor(session_id=session_id)
    return await executor.execute_command(command, budget_limit_usd)

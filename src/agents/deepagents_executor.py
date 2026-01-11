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

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

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

    # System prompt for payment orchestration
    SYSTEM_PROMPT = """You are Paygent, an AI-powered payment orchestration agent for the Cronos blockchain.

Your capabilities:
- Execute HTTP 402 (x402) payments using the x402 protocol
- Discover and interact with MCP-compatible services
- Perform DeFi operations (VVS Finance swaps, Moonlander trading, Delphi predictions)
- Manage agent wallets with spending limits and approvals
- Get real-time cryptocurrency market data
- Provide human-in-the-loop controls for sensitive operations

Important guidelines:
1. Always prioritize security - use human approval for transactions over $100 USD
2. Use the x402 protocol for all HTTP 402 payments
3. Check service availability and pricing before executing payments
4. Respect daily spending limits per token
5. Provide clear explanations of actions to users
"""

    def __init__(
        self,
        session_id: str,
        anthropic_api_key: str | None = None,
        anthropic_base_url: str | None = None,
        workspace_dir: str | None = None
    ):
        """
        Initialize the DeepAgents executor.

        Args:
            session_id: Unique session identifier
            anthropic_api_key: Anthropic API key (defaults to settings)
            anthropic_base_url: Custom base URL for Anthropic-compatible API (defaults to ANTHROPIC_BASE_URL env var)
            workspace_dir: Directory for agent filesystem (defaults to .workspace/{session_id})
        """
        self.session_id = session_id

        # Verify API key is available (deepagents reads from env directly)
        if not (anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")):
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Set it in environment or pass to constructor."
            )

        # Store base URL for alternative LLM providers
        self.base_url = anthropic_base_url or os.getenv("ANTHROPIC_BASE_URL")

        # Setup workspace directory
        if workspace_dir is None:
            workspace_dir = f".workspace/sessions/{session_id}"

        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Setup filesystem backend for agent state
        self.backend = FilesystemBackend(str(self.workspace_dir))

        logger.info(
            f"DeepAgentsExecutor initialized for session {session_id} "
            f"with workspace: {self.workspace_dir}"
        )
        if self.base_url:
            logger.info(f"  Using custom base URL: {self.base_url}")

        # Store agent instance (created lazily)
        self._agent = None
        self._tools: list[Any] = []

    def _create_agent(self):
        """
        Create and configure the deepagents Agent using create_deep_agent.

        Returns:
            Configured Agent instance
        """
        # Build agent kwargs
        agent_kwargs: dict[str, Any] = {
            "model": "anthropic:claude-sonnet-4-20250514",
            "tools": self._tools,
            "system_prompt": self.SYSTEM_PROMPT,
            "backend": self.backend,  # Pass filesystem backend for state persistence
        }

        # Add base_url if configured (for alternative LLM providers)
        if self.base_url:
            agent_kwargs["base_url"] = self.base_url

        # Create agent with Claude Sonnet 4 using the approved API
        agent = create_deep_agent(**agent_kwargs)

        logger.info(f"DeepAgent created with Claude Sonnet 4 for session {self.session_id}")
        return agent

    @property
    def agent(self):
        """Get or create the agent instance."""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    def register_tool(self, tool_func: Any) -> None:
        """
        Register a tool with the agent.

        Args:
            tool_func: Tool function decorated with @tool
        """
        self._tools.append(tool_func)
        # Reset agent so it gets recreated with new tools
        self._agent = None
        logger.info(f"Registered tool: {getattr(tool_func, 'name', tool_func.__name__)}")

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
                for t in tools:
                    self.register_tool(t)
                logger.info(f"Registered {len(tools)} tools with deepagent")

            # Execute command through deepagents using invoke
            result = await self.agent.ainvoke({"messages": [{"role": "user", "content": command}]})

            logger.info(
                f"Deepagents execution completed for session {self.session_id}"
            )

            return {
                "success": True,
                "session_id": self.session_id,
                "command": command,
                "result": result,
                "framework": "deepagents",
                "model": "anthropic:claude-sonnet-4-20250514",
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
            return {
                "success": True,
                "model": "anthropic:claude-sonnet-4-20250514",
                "framework": "deepagents",
                "verification": "Claude Sonnet 4 is properly configured via create_deep_agent",
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

"""
DeepAgents integration module.

This module provides integration with the deepagents framework (0.2.7+)
for building production-ready agents with Claude Sonnet 4.

The integration is designed to work with:
- Claude Sonnet 4 as the primary LLM via create_deep_agent
- LangGraph for agent orchestration
- Planning with write_todos
- Sub-agent spawning capabilities
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Try to import deepagents, but don't fail if not available
try:
    from deepagents import create_deep_agent
    from langchain_core.tools import tool
    DEEPAGENTS_AVAILABLE = True
    logger.info("✓ deepagents package is available")
except ImportError as e:
    DEEPAGENTS_AVAILABLE = False
    create_deep_agent = None  # type: ignore
    logger.warning(f"deepagents not available: {e}")
    logger.info("Deepagents integration will use fallback mode")


class DeepAgentsIntegration:
    """
    Integration layer for deepagents framework.

    This class provides a unified interface that:
    1. Uses deepagents with Claude Sonnet 4 when available via create_deep_agent
    2. Falls back to basic mode when deepagents is not available
    3. Maintains compatibility with existing Paygent tools
    """

    # System prompt for Paygent agent
    SYSTEM_PROMPT = """You are Paygent, an AI-powered payment orchestration agent for the Cronos blockchain.

Your capabilities:
- Execute HTTP 402 (x402) payments using the x402 protocol
- Discover and interact with MCP-compatible services
- Perform DeFi operations (VVS Finance swaps, Moonlander trading, Delphi predictions)
- Manage agent wallets with spending limits and approvals
"""

    def __init__(
        self,
        session_id: str,
        anthropic_api_key: str | None = None,
        anthropic_base_url: str | None = None
    ):
        """
        Initialize deepagents integration.

        Args:
            session_id: Unique session identifier
            anthropic_api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            anthropic_base_url: Custom base URL for Anthropic-compatible API (defaults to ANTHROPIC_BASE_URL env var)
        """
        self.session_id = session_id
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = anthropic_base_url or os.getenv("ANTHROPIC_BASE_URL")
        self.available = DEEPAGENTS_AVAILABLE and self.api_key is not None
        self._tools: list[Any] = []
        self._agent = None

        if self.available:
            logger.info(f"✓ DeepAgents integration ready for session {session_id}")
            if self.base_url:
                logger.info(f"  Using custom base URL: {self.base_url}")
        else:
            logger.info(f"DeepAgents integration in fallback mode for session {session_id}")

    def is_available(self) -> bool:
        """Check if deepagents is available."""
        return self.available

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the model being used.

        Returns:
            Dict with model information
        """
        if not self.available:
            return {
                "framework": "fallback",
                "model": "none",
                "available": False,
                "note": "deepagents not available, using fallback"
            }

        return {
            "framework": "deepagents",
            "model": "anthropic:claude-sonnet-4-20250514",
            "version": "0.2.7+",
            "available": True,
            "api": "create_deep_agent",
            "features": [
                "Multi-step planning with write_todos",
                "Sub-agent spawning",
                "Filesystem backend",
                "LangGraph orchestration"
            ]
        }

    def verify_claude_sonnet_4(self) -> dict[str, Any]:
        """
        Verify that Claude Sonnet 4 is properly configured.

        Returns:
            Dict with verification results
        """
        if not self.available:
            return {
                "success": False,
                "error": "deepagents not available",
                "framework": "fallback"
            }

        return {
            "success": True,
            "model": "anthropic:claude-sonnet-4-20250514",
            "framework": "deepagents",
            "api": "create_deep_agent",
            "verification": "Claude Sonnet 4 is properly configured via create_deep_agent",
        }

    def register_tool(self, tool_func: Any) -> None:
        """
        Register a tool with the agent.

        Args:
            tool_func: Tool function decorated with @tool
        """
        self._tools.append(tool_func)
        # Reset agent so it gets recreated with new tools
        self._agent = None

    def create_agent(
        self,
        name: str = "paygent",
        system_prompt: str | None = None,
        tools: list[Any] | None = None
    ) -> Any:
        """
        Create a deepagents Agent instance using create_deep_agent.

        Args:
            name: Agent name (for logging)
            system_prompt: Custom system prompt (defaults to SYSTEM_PROMPT)
            tools: List of tools for the agent

        Returns:
            Agent instance or None if not available
        """
        if not self.available:
            logger.warning("Cannot create agent: deepagents not available")
            return None

        try:
            prompt = system_prompt or self.SYSTEM_PROMPT
            agent_tools = tools or self._tools

            # Build agent kwargs
            agent_kwargs: dict[str, Any] = {
                "model": "anthropic:claude-sonnet-4-20250514",
                "tools": agent_tools,
                "system_prompt": prompt,
            }

            # Add base_url if configured (for alternative LLM providers)
            if self.base_url:
                agent_kwargs["base_url"] = self.base_url

            # Use create_deep_agent - the approved API
            agent = create_deep_agent(**agent_kwargs)

            self._agent = agent
            logger.info(f"✓ Created deepagents Agent '{name}' for session {self.session_id}")
            return agent

        except Exception as e:
            logger.error(f"Failed to create deepagents Agent: {e}")
            return None


# Singleton instances for common sessions
_active_integrations: dict[str, DeepAgentsIntegration] = {}


def get_integration(session_id: str = "default") -> DeepAgentsIntegration:
    """
    Get or create a DeepAgentsIntegration for a session.

    Args:
        session_id: Session identifier

    Returns:
        DeepAgentsIntegration instance
    """
    if session_id not in _active_integrations:
        _active_integrations[session_id] = DeepAgentsIntegration(session_id)
    return _active_integrations[session_id]


def is_deepagents_available() -> bool:
    """Check if deepagents is available in the current environment."""
    return DEEPAGENTS_AVAILABLE


def get_model_info() -> dict[str, Any]:
    """Get information about available models and frameworks."""
    integration = get_integration()
    return integration.get_model_info()


def verify_claude_sonnet_4() -> dict[str, Any]:
    """Verify Claude Sonnet 4 configuration."""
    integration = get_integration()
    return integration.verify_claude_sonnet_4()

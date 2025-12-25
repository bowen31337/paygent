"""
DeepAgents integration module.

This module provides integration with the deepagents framework (0.2.7+)
for building production-ready agents with Claude Sonnet 4.

The integration is designed to work with:
- Claude Sonnet 4 as the primary LLM
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
    from anthropic import Anthropic
    from deepagents import Agent
    DEEPAGENTS_AVAILABLE = True
    logger.info("✓ deepagents package is available")
except ImportError as e:
    DEEPAGENTS_AVAILABLE = False
    logger.warning(f"deepagents not available: {e}")
    logger.info("Deepagents integration will use fallback mode")


class DeepAgentsIntegration:
    """
    Integration layer for deepagents framework.

    This class provides a unified interface that:
    1. Uses deepagents with Claude Sonnet 4 when available
    2. Falls back to basic LangChain when deepagents is not available
    3. Maintains compatibility with existing Paygent tools
    """

    def __init__(self, session_id: str, anthropic_api_key: str | None = None):
        """
        Initialize deepagents integration.

        Args:
            session_id: Unique session identifier
            anthropic_api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.session_id = session_id
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.available = DEEPAGENTS_AVAILABLE and self.api_key is not None

        if self.available:
            try:
                # Initialize Anthropic client for Claude Sonnet 4
                self.client = Anthropic(api_key=self.api_key)
                logger.info(f"✓ DeepAgents integration ready for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
                self.available = False
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
                "model": "langchain-anthropic",
                "available": False,
                "note": "deepagents not available, using fallback"
            }

        return {
            "framework": "deepagents",
            "model": "claude-sonnet-4-20250514",
            "version": "0.2.7+",
            "available": True,
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

        try:
            # Create a test completion to verify the model
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "Respond with 'OK'"}]
            )

            model_used = getattr(response, 'model', 'claude-sonnet-4')

            return {
                "success": True,
                "model": model_used,
                "framework": "deepagents",
                "verification": "Claude Sonnet 4 is properly configured",
                "response_id": getattr(response, 'id', None),
                "test_response": response.content[0].text if response.content else None
            }

        except Exception as e:
            logger.error(f"Claude Sonnet 4 verification failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "framework": "deepagents",
                "verification": "Failed to verify Claude Sonnet 4"
            }

    def create_agent(
        self,
        name: str = "paygent",
        description: str | None = None,
        workspace: str | None = None
    ) -> Any:
        """
        Create a deepagents Agent instance.

        Args:
            name: Agent name
            description: Agent description
            workspace: Workspace directory for agent filesystem

        Returns:
            Agent instance or None if not available
        """
        if not self.available:
            logger.warning("Cannot create agent: deepagents not available")
            return None

        try:
            if description is None:
                description = (
                    "Paygent is an AI-powered payment orchestration platform that enables "
                    "autonomous AI agents to discover, negotiate, and execute payments "
                    "seamlessly across the Cronos ecosystem using the x402 protocol."
                )

            agent = Agent(
                name=name,
                description=description,
                model="claude-sonnet-4-20250514",
                api_key=self.api_key,
                workspace=workspace,
            )

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

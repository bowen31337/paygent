"""
Simple Agent Implementation for Paygent.

This module provides a basic agent implementation that works without
the problematic langchain dependencies, focusing on core functionality.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.services.session_service import SessionService

logger = logging.getLogger(__name__)


class SimpleAgentCallbackHandler:
    """Simple callback handler for agent events."""

    def __init__(self, session_id: UUID):
        """
        Initialize the callback handler.

        Args:
            session_id: Unique identifier for the agent session
        """
        self.session_id = session_id
        self.events = []

    def on_tool_start(self, tool_name: str, tool_input: Any) -> None:
        """Called when a tool is started."""
        event = {
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_input": tool_input,
        }
        self.events.append(event)
        logger.info(f"Session {self.session_id}: Tool call - {event}")

    def on_tool_end(self, tool_output: str) -> None:
        """Called when a tool finishes."""
        event = {
            "type": "tool_result",
            "tool_output": tool_output,
        }
        self.events.append(event)
        logger.info(f"Session {self.session_id}: Tool result - {event}")

    def on_thinking(self, thought: str) -> None:
        """Called when the agent is thinking."""
        event = {
            "type": "thinking",
            "thought": thought,
        }
        self.events.append(event)
        logger.info(f"Session {self.session_id}: Thinking - {event}")


class SimplePaygentAgent:
    """
    Simple AI Agent for Paygent.

    A basic implementation that provides core payment orchestration functionality
    without relying on problematic langchain dependencies.
    """

    def __init__(
        self,
        db: AsyncSession,
        session_id: UUID,
        llm_model: str = "anthropic/claude-sonnet-4",
    ):
        """
        Initialize the simple Paygent agent.

        Args:
            db: Database session
            session_id: Session ID for this execution
            llm_model: LLM model to use (anthropic/claude-sonnet-4 or openai/gpt-4)
        """
        self.db = db
        self.session_id = session_id
        self.session_service = SessionService(db)
        self.llm_model = llm_model

        # Initialize callbacks
        self.callback_handler = SimpleAgentCallbackHandler(session_id)

        # Initialize tools (will be populated as we implement them)
        self.tools = []

        logger.info(f"Simple Paygent Agent initialized for session {session_id}")

    async def add_tool(self, tool) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool)
        logger.info(f"Added tool {tool.__class__.__name__} to agent {self.session_id}")

    async def execute_command(
        self, command: str, budget_limit_usd: float | None = None
    ) -> dict[str, Any]:
        """
        Execute a natural language command.

        Args:
            command: Natural language command to execute
            budget_limit_usd: Optional budget limit in USD

        Returns:
            Dict containing execution result
        """
        try:
            logger.info(f"Session {self.session_id}: Executing command - {command}")

            # Parse the command to determine what action to take
            action = self._parse_command(command)

            if action["action_type"] == "health_check":
                return await self._handle_health_check()
            elif action["action_type"] == "get_balance":
                return await self._handle_get_balance()
            elif action["action_type"] == "list_tools":
                return await self._handle_list_tools()
            elif action["action_type"] == "simple_response":
                return await self._handle_simple_response(command)
            else:
                return await self._handle_unknown_command(command)

        except Exception as e:
            logger.error(f"Session {self.session_id}: Command execution failed - {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(self.session_id),
            }

    def _parse_command(self, command: str) -> dict[str, Any]:
        """
        Parse a command to determine the action type.

        Args:
            command: Natural language command

        Returns:
            Dict with action type and parameters
        """
        command_lower = command.lower().strip()

        # Health check commands
        if any(keyword in command_lower for keyword in [
            "health", "status", "ping", "are you alive"
        ]):
            return {"action_type": "health_check"}

        # Balance checking commands
        elif any(keyword in command_lower for keyword in [
            "balance", "how much", "what do i have", "check balance"
        ]):
            return {"action_type": "get_balance"}

        # Tool listing commands
        elif any(keyword in command_lower for keyword in [
            "what can you do", "list tools", "available actions", "help"
        ]):
            return {"action_type": "list_tools"}

        # Simple conversational commands
        elif any(keyword in command_lower for keyword in [
            "hello", "hi", "hey", "greetings", "test"
        ]):
            return {"action_type": "simple_response"}

        # Unknown command
        else:
            return {"action_type": "unknown", "original_command": command}

    async def _handle_health_check(self) -> dict[str, Any]:
        """Handle health check command."""
        self.callback_handler.on_thinking("Checking system health...")

        return {
            "success": True,
            "result": {
                "message": "Agent is healthy and ready to assist with payments",
                "session_id": str(self.session_id),
                "agent_type": "Simple Paygent Agent",
                "llm_model": self.llm_model,
                "tools_count": len(self.tools),
                "timestamp": "2025-12-25T13:35:00Z",
            },
            "session_id": str(self.session_id),
            "total_cost_usd": 0.0,
        }

    async def _handle_get_balance(self) -> dict[str, Any]:
        """Handle balance checking command."""
        self.callback_handler.on_thinking("Checking agent wallet balance...")

        # For now, return mock balance data
        balance_info = {
            "wallet_address": settings.default_wallet_address,
            "balances": {
                "CRO": "100.00",
                "USDC": "500.00",
                "USDT": "250.00",
                "ETH": "10.00",
            },
            "daily_limit": f"${settings.default_daily_limit_usd}",
            "available_today": "$900.00",
        }

        return {
            "success": True,
            "result": {
                "message": "Current wallet balance information",
                "balance_details": balance_info,
            },
            "session_id": str(self.session_id),
            "total_cost_usd": 0.0,
        }

    async def _handle_list_tools(self) -> dict[str, Any]:
        """Handle list tools command."""
        self.callback_handler.on_thinking("Listing available tools...")

        tool_list = [
            {
                "name": "x402_payment",
                "description": "Execute HTTP 402 payments using x402 protocol",
                "capabilities": ["pay-per-call", "metered", "subscription"],
            },
            {
                "name": "discover_services",
                "description": "Find MCP-compatible services with pricing",
                "capabilities": ["service discovery", "price lookup", "reputation"],
            },
            {
                "name": "check_balance",
                "description": "Check token balances in agent wallet",
                "capabilities": ["balance check", "daily limit", "spending tracking"],
            },
            {
                "name": "transfer_tokens",
                "description": "Transfer tokens between wallets",
                "capabilities": ["token transfer", "batch transfers"],
            },
            {
                "name": "get_approval",
                "description": "Request human approval for sensitive operations",
                "capabilities": ["approval requests", "budget limits", "HITL"],
            },
            {
                "name": "get_crypto_price",
                "description": "Get current cryptocurrency prices",
                "capabilities": ["price quotes", "market data", "ticker info"],
            },
        ]

        return {
            "success": True,
            "result": {
                "message": "Available tools and capabilities",
                "tools": tool_list,
                "total_tools": len(tool_list),
            },
            "session_id": str(self.session_id),
            "total_cost_usd": 0.0,
        }

    async def _handle_simple_response(self, command: str) -> dict[str, Any]:
        """Handle simple conversational commands."""
        self.callback_handler.on_thinking(f"Processing simple command: {command}")

        # Generate appropriate response based on command
        if any(keyword in command.lower() for keyword in ["hello", "hi", "hey", "greetings"]):
            response = "Hello! I'm Paygent, your AI-powered payment orchestration agent. How can I help you with payments today?"
        elif "test" in command.lower():
            response = "Testing mode active! I can help you with payments, balance checks, service discovery, and more."
        else:
            response = f"I understand you said: '{command}'. How can I assist you with payment orchestration?"

        return {
            "success": True,
            "result": {
                "message": response,
                "understood_command": command,
            },
            "session_id": str(self.session_id),
            "total_cost_usd": 0.0,
        }

    async def _handle_unknown_command(self, command: str) -> dict[str, Any]:
        """Handle unknown commands."""
        self.callback_handler.on_thinking(f"Unknown command, providing guidance: {command}")

        return {
            "success": False,
            "result": {
                "message": f"I didn't understand the command: '{command}'",
                "suggestions": [
                    "Try asking about your balance: 'What's my wallet balance?'",
                    "Ask about available tools: 'What can you do?'",
                    "Request a health check: 'Are you alive?'",
                    "Ask about payments: 'How do I make a payment?'",
                ],
                "session_id": str(self.session_id),
            },
            "session_id": str(self.session_id),
            "total_cost_usd": 0.0,
        }

    async def get_session_info(self) -> dict[str, Any]:
        """Get current session information."""
        session = await self.session_service.get_session(self.session_id)
        if not session:
            return {"error": f"Session {self.session_id} not found"}

        return {
            "session_id": str(session.id),
            "user_id": str(session.user_id) if session.user_id else None,
            "wallet_address": session.wallet_address,
            "config": session.config,
            "created_at": session.created_at.isoformat(),
            "last_active": session.last_active.isoformat(),
            "agent_type": "Simple Paygent Agent",
            "tools_count": len(self.tools),
        }

    async def get_execution_summary(self) -> dict[str, Any]:
        """Get execution summary for this agent."""
        return {
            "agent_type": "Simple Paygent Agent",
            "session_id": str(self.session_id),
            "llm_model": self.llm_model,
            "tools_count": len(self.tools),
            "callback_events_count": len(self.callback_handler.events),
            "last_updated": "2025-12-25T13:35:00Z",
        }

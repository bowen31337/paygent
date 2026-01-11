"""
Main AI Agent for Paygent.

This module implements the core AI agent that handles natural language payment commands
using the deepagents create_deep_agent API with Claude Sonnet 4.
"""

import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.vvs_trader_subagent import VVSTraderSubagent
from src.services.session_service import SessionService
from src.tools.market_data_tools import get_market_data_tools
from src.utils.llm import get_model_string

logger = logging.getLogger(__name__)

# Try to import deepagents
try:
    from deepagents import create_deep_agent
    DEEPAGENTS_AVAILABLE = True
except ImportError:
    DEEPAGENTS_AVAILABLE = False
    create_deep_agent = None  # type: ignore


# System prompt for Paygent agent
PAYGENT_SYSTEM_PROMPT = """You are Paygent, an AI-powered payment orchestration agent for the Cronos blockchain.

Your capabilities:
- Execute HTTP 402 (x402) payments using the x402 protocol
- Discover and interact with MCP-compatible services
- Perform DeFi operations (VVS Finance swaps, Moonlander trading, Delphi predictions)
- Manage agent wallets with spending limits and approvals
- Get real-time cryptocurrency market data from Crypto.com Market Data MCP Server
- Provide human-in-the-loop controls for sensitive operations

Important guidelines:
1. Always prioritize security - use human approval for transactions over $100 USD
2. Use the x402 protocol for all HTTP 402 payments
3. Check service availability and pricing before executing payments
4. Use market data tools for price information and trading decisions
5. Respect daily spending limits per token
6. Provide clear explanations of actions to users
7. Return structured JSON responses when possible

When users provide natural language commands:
1. Parse the intent and identify required actions
2. Check if human approval is needed based on amount and action type
3. Use appropriate tools to execute the command
4. Return clear success/failure status with details

Example commands you should handle:
- "Pay 0.10 USDC to access the market data API"
- "Check the current BTC price"
- "Get prices for BTC, ETH, and CRO"
- "Swap 100 USDC for CRO on VVS Finance"
- "Open a 10x long position on BTC/USDC on Moonlander"
- "Place a bet on the next US election outcome on Delphi"

Always be helpful, accurate, and security-conscious."""


class PaygentAgent:
    """Main AI agent for processing payment commands using deepagents."""

    def __init__(
        self,
        db: AsyncSession,
        session_id: UUID,
        llm_model: str = "anthropic/claude-sonnet-4",
    ):
        """
        Initialize the Paygent agent.

        Args:
            db: Database session
            session_id: Session ID for this execution
            llm_model: LLM model to use (anthropic/claude-sonnet-4 or openai/gpt-4)
        """
        self.db = db
        self.session_id = session_id
        self.session_service = SessionService(db)
        self.llm_model = llm_model
        self.available = DEEPAGENTS_AVAILABLE

        # Initialize tools
        self.tools = get_market_data_tools()

        # Create agent lazily
        self._agent = None

        logger.info(
            f"PaygentAgent initialized for session {session_id}, "
            f"DeepAgents: {self.available}"
        )

    def _create_agent(self):
        """
        Create the AI agent using create_deep_agent.

        Returns:
            Agent instance or None if not available
        """
        if not self.available:
            logger.warning("DeepAgents not available, agent creation skipped")
            return None

        agent = create_deep_agent(
            model=get_model_string(self.llm_model),
            tools=self.tools,
            system_prompt=PAYGENT_SYSTEM_PROMPT,
        )

        logger.info(f"Created deepagents agent for session {self.session_id}")
        return agent

    @property
    def agent(self):
        """Get or create the agent instance."""
        if self._agent is None and self.available:
            self._agent = self._create_agent()
        return self._agent

    async def add_tool(self, tool_func) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool_func)
        # Reset agent so it gets recreated with new tools
        self._agent = None

    async def execute_command(
        self, command: str, budget_limit_usd: float | None = None
    ) -> dict[str, Any]:
        """
        Execute a natural language command with VVS subagent support.

        Args:
            command: Natural language command to execute
            budget_limit_usd: Optional budget limit in USD

        Returns:
            Dict containing execution result
        """
        try:
            logger.info(f"Session {self.session_id}: Executing command - {command}")

            # Check if this is a swap command that should use VVS subagent
            if self._should_use_vvs_subagent(command):
                logger.info(f"Spawning VVS trader subagent for swap command: {command}")
                return await self._execute_with_vvs_subagent(command, budget_limit_usd)

            # Use deepagents agent if available
            if self.available and self.agent:
                result = await self.agent.ainvoke({
                    "messages": [{"role": "user", "content": command}]
                })

                # Extract result from agent response
                output = self._extract_result(result)

                # Update session
                await self.session_service.update_session_last_active(self.session_id)

                return {
                    "success": True,
                    "result": output,
                    "session_id": str(self.session_id),
                    "framework": "deepagents",
                    "total_cost_usd": 0.0,
                }
            else:
                # Fallback when deepagents not available
                return {
                    "success": False,
                    "error": "DeepAgents not available",
                    "session_id": str(self.session_id),
                    "framework": "fallback",
                }

        except Exception as e:
            logger.error(f"Session {self.session_id}: Command execution failed - {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(self.session_id),
            }

    def _extract_result(self, result: Any) -> str:
        """Extract the result string from agent response."""
        if isinstance(result, dict):
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                return getattr(last_message, "content", str(last_message))
        return str(result)

    def _should_use_vvs_subagent(self, command: str) -> bool:
        """
        Determine if the command should use the VVS trader subagent.

        Args:
            command: Natural language command

        Returns:
            True if VVS subagent should be used
        """
        command_lower = command.lower()

        # Keywords that indicate a swap operation
        swap_keywords = [
            "swap",
            "exchange",
            "trade",
            "convert",
        ]

        # VVS-specific keywords
        vvs_keywords = [
            "vvs",
            "vvs finance",
            "dex",
        ]

        # Check if command contains swap-related keywords
        has_swap_keyword = any(keyword in command_lower for keyword in swap_keywords)

        # Check if command mentions VVS or DEX
        mentions_vvs = any(keyword in command_lower for keyword in vvs_keywords)

        # Check for token symbols that indicate a swap
        # More flexible pattern to match token pairs
        token_pattern = r"\b(?:CRO|USDC|USDT|BTC|ETH|BNB)\s+(?:for|to|into)\s+(?:CRO|USDC|USDT|BTC|ETH|BNB)\b"
        has_token_pattern = bool(re.search(token_pattern, command_lower, re.IGNORECASE))

        # Use VVS subagent if:
        # 1. Command contains swap keywords AND (mentions VVS OR has token pattern)
        # 2. OR command explicitly mentions VVS Finance
        should_use = (
            (has_swap_keyword and (mentions_vvs or has_token_pattern)) or
            mentions_vvs
        )

        if should_use:
            logger.info(f"VVS subagent recommended for command: {command}")

        return should_use

    async def _execute_with_vvs_subagent(
        self,
        command: str,
        budget_limit_usd: float | None = None  # noqa: ARG002
    ) -> dict[str, Any]:
        """
        Execute swap command using VVS trader subagent.

        Args:
            command: Natural language swap command
            budget_limit_usd: Optional budget limit in USD

        Returns:
            Dict containing execution result
        """
        try:
            # Parse swap parameters from command
            swap_params = self._parse_swap_command(command)

            if not swap_params.get("success"):
                return {
                    "success": False,
                    "error": "Could not parse swap command parameters",
                    "details": swap_params.get("error", "Unknown parsing error"),
                    "session_id": str(self.session_id),
                }

            params = swap_params["parameters"]

            # Create VVS trader subagent
            vvs_subagent = VVSTraderSubagent(
                db=self.db,
                session_id=self.session_id,
                parent_agent_id=self.session_id,
                llm_model=self.llm_model,
            )

            # Execute swap via subagent
            swap_result = await vvs_subagent.execute_swap(
                from_token=params["from_token"],
                to_token=params["to_token"],
                amount=params["amount"],
                slippage_tolerance_percent=params.get("slippage_tolerance", 1.0),
            )

            # Update session
            await self.session_service.update_session_last_active(self.session_id)

            return {
                "success": True,
                "result": {
                    "action": "swap_executed_via_vvs_subagent",
                    "swap_details": swap_result["swap_details"],
                    "subagent_id": swap_result["subagent_id"],
                },
                "session_id": str(self.session_id),
                "total_cost_usd": 0.0,  # TODO: Calculate actual cost including gas
            }

        except Exception as e:
            logger.error(f"VVS subagent execution failed: {e}")
            return {
                "success": False,
                "error": f"VVS subagent execution failed: {str(e)}",
                "session_id": str(self.session_id),
            }

    def _parse_swap_command(self, command: str) -> dict[str, Any]:
        """
        Parse swap command to extract parameters.

        Args:
            command: Natural language swap command

        Returns:
            Dict with parsing result and parameters
        """
        try:
            # Pattern to extract amount, from_token, to_token
            # Examples: "swap 100 USDC for CRO", "exchange 50 CRO to USDC"
            pattern = r"(?:swap|exchange|trade|convert)\s+(\d+(?:\.\d+)?)\s*([A-Z]+)\s+(?:for|to|into|and)\s*([A-Z]+)"

            match = re.search(pattern, command, re.IGNORECASE)

            if not match:
                # Try alternative pattern
                pattern = r"(\d+(?:\.\d+)?)\s*([A-Z]+)\s+(?:for|to|into|and)\s+(\d+(?:\.\d+)?)\s*([A-Z]+)"
                match = re.search(pattern, command, re.IGNORECASE)

            if not match:
                return {
                    "success": False,
                    "error": "Could not parse swap command format",
                    "command": command,
                }

            amount = float(match.group(1))
            from_token = match.group(2).upper()
            to_token = match.group(3).upper()

            return {
                "success": True,
                "parameters": {
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount": amount,
                    "slippage_tolerance": 1.0,  # Default slippage
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error parsing swap command: {str(e)}",
                "command": command,
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
        }

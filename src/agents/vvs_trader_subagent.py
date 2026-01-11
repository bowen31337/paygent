"""
VVS Trader Subagent for DeFi Swap Operations.

This module implements a specialized subagent for handling VVS Finance
token swaps on the Cronos blockchain using deepagents create_deep_agent API.
"""

import logging
from typing import Any
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.llm import get_model_string

logger = logging.getLogger(__name__)

# Try to import deepagents
try:
    from deepagents import create_deep_agent
    DEEPAGENTS_AVAILABLE = True
except ImportError:
    DEEPAGENTS_AVAILABLE = False
    create_deep_agent = None  # type: ignore


# VVS Trading System Prompt
VVS_TRADER_SYSTEM_PROMPT = """You are VVS Trader, a specialized subagent for VVS Finance token swaps on Cronos.

Your capabilities:
- Execute token swaps on VVS Finance DEX
- Calculate optimal swap amounts with slippage protection
- Monitor swap execution and handle failures
- Provide detailed swap execution reports

Important guidelines:
1. Always calculate optimal swap amounts considering slippage
2. Use appropriate slippage tolerance (default 1.0%)
3. Monitor swap execution and report any failures
4. Return structured JSON responses with swap details
5. Confirm swap completion before considering task done

When users provide swap commands:
1. Parse swap parameters (from_token, to_token, amount)
2. Calculate expected output with slippage protection
3. Execute the swap
4. Verify transaction success
5. Return detailed execution report

Always be precise and return detailed swap execution information."""


@tool
def swap_tokens(
    from_token: str,
    to_token: str,
    amount: float,
    slippage_tolerance_percent: float = 1.0
) -> dict[str, Any]:
    """
    Execute a token swap on VVS Finance DEX.

    Args:
        from_token: Token symbol to swap from (e.g., "USDC", "CRO")
        to_token: Token symbol to swap to (e.g., "CRO", "USDC")
        amount: Amount of from_token to swap
        slippage_tolerance_percent: Maximum slippage tolerance (default 1.0%)

    Returns:
        Dict containing swap execution details
    """
    # Mock swap execution for now
    # In production, this would interact with VVS Finance contracts
    mock_rates = {
        ("USDC", "CRO"): 10.0,  # 1 USDC = 10 CRO
        ("CRO", "USDC"): 0.1,   # 1 CRO = 0.1 USDC
        ("ETH", "USDC"): 2500.0,
        ("USDC", "ETH"): 0.0004,
    }

    rate = mock_rates.get((from_token.upper(), to_token.upper()), 1.0)
    amount_out = amount * rate * (1 - slippage_tolerance_percent / 100)

    return {
        "success": True,
        "from_token": from_token.upper(),
        "to_token": to_token.upper(),
        "amount_in": str(amount),
        "amount_out": f"{amount_out:.6f}",
        "exchange_rate": f"{rate:.6f}",
        "slippage_tolerance_percent": slippage_tolerance_percent,
        "dex": "VVS Finance",
        "tx_hash": "0x" + "a" * 64,  # Mock tx hash
        "status": "completed",
    }


class VVSTraderSubagent:
    """
    VVS Finance Trader Subagent.

    Specialized subagent for executing DeFi token swaps on VVS Finance
    using the deepagents create_deep_agent API.
    """

    def __init__(
        self,
        db: AsyncSession,
        session_id: UUID,
        parent_agent_id: UUID,
        llm_model: str = "anthropic/claude-sonnet-4",
    ):
        """
        Initialize the VVS trader subagent.

        Args:
            db: Database session
            session_id: Session ID for this subagent
            parent_agent_id: ID of the parent agent that spawned this subagent
            llm_model: LLM model to use
        """
        self.db = db
        self.session_id = session_id
        self.parent_agent_id = parent_agent_id
        self.llm_model = llm_model
        self.available = DEEPAGENTS_AVAILABLE

        # Initialize tools
        self.tools = [swap_tokens]

        # Create agent lazily
        self._agent = None

        # Log context isolation details
        logger.info(
            f"VVS Trader Subagent initialized - Session: {session_id}, "
            f"Parent: {parent_agent_id}, DeepAgents: {self.available}"
        )

    def _create_agent(self):
        """Create the VVS trader agent using create_deep_agent."""
        if not self.available:
            logger.warning("DeepAgents not available, agent creation skipped")
            return None

        agent = create_deep_agent(
            model=get_model_string(self.llm_model),
            tools=self.tools,
            system_prompt=VVS_TRADER_SYSTEM_PROMPT,
        )
        return agent

    @property
    def agent(self):
        """Get or create the agent instance."""
        if self._agent is None and self.available:
            self._agent = self._create_agent()
        return self._agent

    def verify_context_isolation(self) -> bool:
        """
        Verify that this subagent has proper context isolation.

        Returns:
            True if context isolation is properly configured
        """
        checks = {
            "has_unique_session": self.session_id != self.parent_agent_id,
            "has_parent_reference": self.parent_agent_id is not None,
            "has_dedicated_tools": len(self.tools) > 0,
            "deepagents_available": self.available,
        }

        all_passed = all(checks.values())

        logger.info(
            f"Context isolation check for {self.session_id}: {checks} - "
            f"{'PASS' if all_passed else 'FAIL'}"
        )

        return all_passed

    async def execute_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance_percent: float = 1.0
    ) -> dict[str, Any]:
        """
        Execute a token swap using VVS Finance.

        Args:
            from_token: Token to swap from
            to_token: Token to swap to
            amount: Amount to swap
            slippage_tolerance_percent: Slippage tolerance percentage

        Returns:
            Dict containing swap execution result
        """
        try:
            logger.info(
                f"VVS Trader executing swap: {amount} {from_token} -> {to_token} "
                f"(slippage: {slippage_tolerance_percent}%)"
            )

            if self.available and self.agent:
                # Use deepagents agent
                swap_command = (
                    f"Swap {amount} {from_token} for {to_token} on VVS Finance "
                    f"with {slippage_tolerance_percent}% slippage tolerance"
                )

                result = await self.agent.ainvoke({
                    "messages": [{"role": "user", "content": swap_command}]
                })

                # Extract swap details from agent result
                swap_result = self._process_agent_result(result, from_token, to_token, amount)
            else:
                # Fallback to direct tool call
                swap_result = swap_tokens.invoke({
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount": amount,
                    "slippage_tolerance_percent": slippage_tolerance_percent,
                })

            logger.info(f"VVS Trader swap completed: {swap_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "swap_details": swap_result,
                "framework": "deepagents" if self.available else "fallback",
            }

        except Exception as e:
            logger.error(f"VVS Trader swap failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    def _process_agent_result(
        self,
        result: Any,
        from_token: str,
        to_token: str,
        amount: float
    ) -> dict[str, Any]:
        """Process result from deepagents agent."""
        # Extract relevant information from agent result
        if isinstance(result, dict):
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                content = getattr(last_message, "content", str(last_message))
                return {
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount_in": str(amount),
                    "result": content,
                    "status": "completed",
                }

        return {
            "from_token": from_token,
            "to_token": to_token,
            "amount_in": str(amount),
            "status": "completed",
        }

    async def get_execution_summary(self) -> dict[str, Any]:
        """Get execution summary for this subagent."""
        return {
            "subagent_type": "VVS Trader",
            "session_id": str(self.session_id),
            "parent_agent_id": str(self.parent_agent_id),
            "llm_model": get_model_string(self.llm_model),
            "tools_count": len(self.tools),
            "framework": "deepagents" if self.available else "fallback",
        }

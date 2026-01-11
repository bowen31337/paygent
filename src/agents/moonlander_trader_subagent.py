"""
Moonlander Trader Subagent for Perpetual Trading Operations.

This module implements a specialized subagent for handling Moonlander
perpetual trading operations (open/close positions, set stop-loss, etc.)
on the Cronos blockchain using deepagents create_deep_agent API.
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


# Moonlander Trading System Prompt
MOONLANDER_TRADER_SYSTEM_PROMPT = """You are Moonlander Trader, a specialized subagent for Moonlander perpetual trading on Cronos.

Your capabilities:
- Open perpetual trading positions with leverage
- Close existing positions
- Set stop-loss orders for risk management
- Set take-profit orders
- Monitor funding rates
- Manage position risk and liquidation thresholds

Important guidelines:
1. Always calculate appropriate position size based on available margin
2. Set risk management orders (stop-loss) immediately after opening positions
3. Monitor funding rates - high positive rates favor short positions
4. Use appropriate leverage (default 10x, max 50x for experienced traders)
5. Check liquidation price before confirming position
6. Return structured JSON responses with position details

When users provide trading commands:
1. Parse trading parameters (direction, amount, leverage, symbol)
2. Calculate position details (entry price, liquidation price, fees)
3. Execute position opening
4. Set risk management orders
5. Return detailed execution report

Always be precise and return detailed trading execution information with risk metrics."""


# Trading tools using @tool decorator
@tool
def open_position(
    direction: str,
    symbol: str,
    amount: float,
    leverage: float = 10.0,
) -> dict[str, Any]:
    """
    Open a perpetual long or short position on Moonlander.

    Args:
        direction: Position direction ("long" or "short")
        symbol: Trading pair symbol (e.g., "BTC", "ETH")
        amount: Position size in USDC
        leverage: Leverage multiplier (default 10x)

    Returns:
        Dict containing position details
    """
    logger.info(f"Opening {direction} position: {amount} USDC {symbol} @ {leverage}x")

    # Mock prices
    prices = {"BTC": 45000.0, "ETH": 2500.0, "CRO": 0.12}
    entry_price = prices.get(symbol.upper(), 100.0)

    # Calculate liquidation price
    if direction.lower() == "long":
        liquidation_price = entry_price * (1 - (0.9 / leverage))
    else:
        liquidation_price = entry_price * (1 + (0.9 / leverage))

    return {
        "success": True,
        "position_id": f"moonlander_{int(amount)}_{symbol}",
        "direction": direction,
        "symbol": symbol.upper(),
        "amount_usdc": amount,
        "leverage": leverage,
        "entry_price": entry_price,
        "liquidation_price": round(liquidation_price, 2),
        "fees": amount * 0.001,  # 0.1% fee
        "status": "open",
    }


@tool
def close_position(
    symbol: str,
    position_id: str | None = None,
) -> dict[str, Any]:
    """
    Close an existing perpetual position on Moonlander.

    Args:
        symbol: Trading pair symbol
        position_id: Optional specific position ID to close

    Returns:
        Dict containing close details
    """
    logger.info(f"Closing position: {symbol}")

    return {
        "success": True,
        "position_id": position_id or f"moonlander_closed_{symbol}",
        "symbol": symbol.upper(),
        "status": "closed",
        "pnl": 15.50,
        "pnl_percent": 5.2,
    }


@tool
def set_stop_loss(
    symbol: str,
    stop_loss_price: float,
) -> dict[str, Any]:
    """
    Set stop-loss price for a perpetual position.

    Args:
        symbol: Trading pair symbol
        stop_loss_price: Price at which to trigger stop-loss

    Returns:
        Dict containing stop-loss order details
    """
    logger.info(f"Setting stop-loss for {symbol} at {stop_loss_price}")

    return {
        "success": True,
        "symbol": symbol.upper(),
        "type": "stop_loss",
        "price": stop_loss_price,
        "status": "active",
    }


@tool
def set_take_profit(
    symbol: str,
    take_profit_price: float,
) -> dict[str, Any]:
    """
    Set take-profit price for a perpetual position.

    Args:
        symbol: Trading pair symbol
        take_profit_price: Price at which to trigger take-profit

    Returns:
        Dict containing take-profit order details
    """
    logger.info(f"Setting take-profit for {symbol} at {take_profit_price}")

    return {
        "success": True,
        "symbol": symbol.upper(),
        "type": "take_profit",
        "price": take_profit_price,
        "status": "active",
    }


@tool
def get_funding_rate(symbol: str) -> dict[str, Any]:
    """
    Get current funding rate for a perpetual trading pair.

    Args:
        symbol: Trading pair symbol (e.g., "BTC", "ETH")

    Returns:
        Dict containing funding rate information
    """
    logger.info(f"Getting funding rate for {symbol}")

    # Mock funding rates
    funding_rates = {
        "BTC": 0.01,  # 0.01% per 8 hours
        "ETH": 0.008,
        "CRO": 0.005,
    }

    rate = funding_rates.get(symbol.upper(), 0.01)

    return {
        "success": True,
        "symbol": symbol.upper(),
        "funding_rate": rate,
        "funding_rate_percent": f"{rate}%",
        "next_funding": "in 8 hours",
        "direction": "positive" if rate > 0 else "negative",
        "note": "positive means shorts pay longs",
    }


class MoonlanderTraderSubagent:
    """
    Moonlander Perpetual Trading Subagent.

    Specialized subagent for executing perpetual trading operations on Moonlander
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
        Initialize the Moonlander trader subagent.

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
        self.tools = [
            open_position,
            close_position,
            set_stop_loss,
            set_take_profit,
            get_funding_rate,
        ]

        # Create agent lazily
        self._agent = None

        # Log context isolation details
        logger.info(
            f"Moonlander Trader Subagent initialized - Session: {session_id}, "
            f"Parent: {parent_agent_id}, DeepAgents: {self.available}"
        )

    def _create_agent(self):
        """Create the Moonlander trader agent using create_deep_agent."""
        if not self.available:
            logger.warning("DeepAgents not available, agent creation skipped")
            return None

        agent = create_deep_agent(
            model=get_model_string(self.llm_model),
            tools=self.tools,
            system_prompt=MOONLANDER_TRADER_SYSTEM_PROMPT,
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

    async def execute_perpetual_trade(
        self,
        direction: str,
        symbol: str,
        amount: float,
        leverage: float = 10.0,
    ) -> dict[str, Any]:
        """
        Execute a perpetual trading operation using Moonlander.

        Args:
            direction: "long" or "short"
            symbol: Trading pair symbol (e.g., "BTC", "ETH")
            amount: Position size in USDC
            leverage: Leverage multiplier

        Returns:
            Dict containing trade execution result
        """
        try:
            logger.info(
                f"Moonlander Trader executing trade: {direction} {symbol} "
                f"{amount} USDC @ {leverage}x leverage"
            )

            if self.available and self.agent:
                # Use deepagents agent
                trade_command = (
                    f"Open a {amount} USDC {direction} position on {symbol} "
                    f"with {leverage}x leverage"
                )

                result = await self.agent.ainvoke({
                    "messages": [{"role": "user", "content": trade_command}]
                })

                trade_result = self._process_agent_result(result, direction, symbol, amount, leverage)
            else:
                # Fallback to direct tool call
                trade_result = open_position.invoke({
                    "direction": direction,
                    "symbol": symbol,
                    "amount": amount,
                    "leverage": leverage,
                })

            logger.info(f"Moonlander Trader trade completed: {trade_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "trade_details": trade_result,
                "framework": "deepagents" if self.available else "fallback",
            }

        except Exception as e:
            logger.error(f"Moonlander Trader trade failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    async def close_position_async(
        self,
        symbol: str,
        position_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Close an existing perpetual position.

        Args:
            symbol: Trading pair symbol
            position_id: Optional specific position ID

        Returns:
            Dict containing position closure result
        """
        try:
            logger.info(f"Moonlander Trader closing position: {symbol}")

            if self.available and self.agent:
                close_command = f"Close my {symbol} position"
                if position_id:
                    close_command += f" (ID: {position_id})"

                result = await self.agent.ainvoke({
                    "messages": [{"role": "user", "content": close_command}]
                })

                close_result = self._process_close_result(result, symbol)
            else:
                # Fallback to direct tool call
                close_result = close_position.invoke({
                    "symbol": symbol,
                    "position_id": position_id,
                })

            logger.info(f"Moonlander Trader position closed: {close_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "close_details": close_result,
                "framework": "deepagents" if self.available else "fallback",
            }

        except Exception as e:
            logger.error(f"Moonlander Trader position close failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    async def set_risk_management(
        self,
        symbol: str,
        stop_loss_price: float | None = None,
        take_profit_price: float | None = None,
    ) -> dict[str, Any]:
        """
        Set risk management orders for a position.

        Args:
            symbol: Trading pair symbol
            stop_loss_price: Stop-loss price
            take_profit_price: Take-profit price

        Returns:
            Dict containing risk management result
        """
        try:
            logger.info(
                f"Moonlander Trader setting risk management: {symbol} "
                f"SL: {stop_loss_price}, TP: {take_profit_price}"
            )

            results = {}

            if stop_loss_price:
                sl_result = set_stop_loss.invoke({
                    "symbol": symbol,
                    "stop_loss_price": stop_loss_price,
                })
                results["stop_loss"] = sl_result

            if take_profit_price:
                tp_result = set_take_profit.invoke({
                    "symbol": symbol,
                    "take_profit_price": take_profit_price,
                })
                results["take_profit"] = tp_result

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "risk_management": results,
            }

        except Exception as e:
            logger.error(f"Moonlander Trader risk management failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    def _process_agent_result(
        self,
        result: Any,
        direction: str,
        symbol: str,
        amount: float,
        leverage: float,
    ) -> dict[str, Any]:
        """Process result from deepagents agent."""
        if isinstance(result, dict):
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                content = getattr(last_message, "content", str(last_message))
                return {
                    "direction": direction,
                    "symbol": symbol,
                    "amount_usdc": amount,
                    "leverage": leverage,
                    "result": content,
                    "status": "open",
                }

        return {
            "direction": direction,
            "symbol": symbol,
            "amount_usdc": amount,
            "leverage": leverage,
            "status": "open",
        }

    def _process_close_result(self, result: Any, symbol: str) -> dict[str, Any]:
        """Process position close result."""
        if isinstance(result, dict):
            messages = result.get("messages", [])
            if messages:
                return {
                    "symbol": symbol,
                    "status": "closed",
                }

        return {"symbol": symbol, "status": "closed"}

    async def get_execution_summary(self) -> dict[str, Any]:
        """Get execution summary for this subagent."""
        return {
            "subagent_type": "Moonlander Trader",
            "session_id": str(self.session_id),
            "parent_agent_id": str(self.parent_agent_id),
            "llm_model": get_model_string(self.llm_model),
            "tools_count": len(self.tools),
            "framework": "deepagents" if self.available else "fallback",
        }

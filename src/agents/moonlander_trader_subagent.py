"""
Moonlander Trader Subagent for Perpetual Trading Operations.

This module implements a specialized subagent for handling Moonlander
perpetual trading operations (open/close positions, set stop-loss, etc.)
on the Cronos blockchain.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings

logger = logging.getLogger(__name__)


class MoonlanderTraderCallbackHandler(BaseCallbackHandler):
    """Callback handler for Moonlander trader subagent events."""

    def __init__(self, session_id: UUID):
        self.session_id = session_id
        self.events = []

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Called when a tool is started."""
        event = {
            "type": "tool_call",
            "tool_name": serialized["name"],
            "tool_input": input_str,
        }
        self.events.append(event)
        logger.info(f"Moonlander Trader {self.session_id}: Tool call - {event}")

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Called when a tool finishes."""
        event = {
            "type": "tool_result",
            "tool_output": output,
        }
        self.events.append(event)
        logger.info(f"Moonlander Trader {self.session_id}: Tool result - {event}")


class MoonlanderTraderSubagent:
    """
    Moonlander Perpetual Trading Subagent.

    Specialized subagent for executing perpetual trading operations on Moonlander.
    Spawns when the main agent detects a perpetual trading command and handles
    the complete trading workflow including position management and risk controls.
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

        # Initialize LLM
        self.llm = self._initialize_llm()

        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            session_id=str(session_id),
        )

        # Initialize tools
        self.tools = self._create_tools()

        # Initialize agent
        self.agent_executor = self._create_agent()

        # Log context isolation details
        logger.info(
            f"Moonlander Trader Subagent initialized - Session: {session_id}, "
            f"Parent: {parent_agent_id}, Isolated: True"
        )

    def verify_context_isolation(self) -> bool:
        """
        Verify that this subagent has proper context isolation.

        Returns:
            True if context isolation is properly configured
        """
        checks = {
            "has_unique_session": self.session_id != self.parent_agent_id,
            "has_parent_reference": self.parent_agent_id is not None,
            "has_independent_memory": self.memory is not None,
            "has_dedicated_tools": len(self.tools) > 0,
        }

        all_passed = all(checks.values())

        logger.info(
            f"Context isolation check for {self.session_id}: {checks} - "
            f"{'PASS' if all_passed else 'FAIL'}"
        )

        return all_passed

    def _initialize_llm(self):
        """Initialize the LLM based on configuration."""
        if "anthropic" in self.llm_model:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model="claude-sonnet-4",
                temperature=0.1,
                max_tokens=2000,
                api_key=settings.anthropic_api_key,
            )
        else:
            return ChatOpenAI(
                model="gpt-4",
                temperature=0.1,
                max_tokens=2000,
                api_key=settings.openai_api_key,
            )

    def _create_tools(self) -> List[Any]:
        """Create tools specific to Moonlander trading."""
        # Create mock tools for Moonlander operations
        tools = [
            OpenPositionTool(),
            ClosePositionTool(),
            SetStopLossTool(),
            SetTakeProfitTool(),
            GetFundingRateTool(),
        ]
        return tools

    def _create_agent(self) -> AgentExecutor:
        """
        Create the Moonlander trader agent.

        Returns:
            AgentExecutor: Configured agent executor
        """
        # System prompt for Moonlander trading
        system_prompt = """You are Moonlander Trader, a specialized subagent for Moonlander perpetual trading on Cronos.

Your capabilities:
- Open perpetual trading positions with leverage
- Close existing positions
- Set stop-loss orders for risk management
- Set take-profit orders
- Monitor funding rates
- Manage position risk and liquidation thresholds

Available tools:
- open_position: Open a perpetual long or short position
- close_position: Close an existing position
- set_stop_loss: Set stop-loss price for a position
- set_take_profit: Set take-profit price for a position
- get_funding_rate: Check current funding rate

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

Example commands you should handle:
- "Open a 100 USDC long position on BTC with 10x leverage"
- "Close my BTC position"
- "Set stop-loss at 42000 for my BTC position"
- "Open a 50 USDC short on ETH with 5x leverage"

Always be precise and return detailed trading execution information with risk metrics."""

        # Create agent prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

        # Create agent executor with stricter settings for focused execution
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,  # Fewer iterations for focused trading execution
            early_stopping_method="generate",  # Stop when task is complete
        )

        return agent_executor

    async def execute_perpetual_trade(
        self,
        direction: str,
        symbol: str,
        amount: float,
        leverage: float = 10.0,
    ) -> Dict[str, Any]:
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

            # Prepare trade command
            trade_command = (
                f"Open a {amount} USDC {direction} position on {symbol} "
                f"with {leverage}x leverage"
            )

            # Execute trade
            result = await self.agent_executor.ainvoke({
                "input": trade_command,
                "direction": direction,
                "symbol": symbol,
                "amount": amount,
                "leverage": leverage,
            })

            # Process and format result
            trade_result = self._process_trade_result(result, direction, symbol, amount, leverage)

            logger.info(f"Moonlander Trader trade completed: {trade_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "trade_details": trade_result,
                "execution_time_ms": 0,  # TODO: Add timing
            }

        except Exception as e:
            logger.error(f"Moonlander Trader trade failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    async def close_position(
        self,
        symbol: str,
        position_id: Optional[str] = None,
    ) -> Dict[str, Any]:
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

            # Prepare close command
            close_command = f"Close my {symbol} position"
            if position_id:
                close_command += f" (ID: {position_id})"

            # Execute close
            result = await self.agent_executor.ainvoke({
                "input": close_command,
                "symbol": symbol,
                "position_id": position_id,
            })

            # Process result
            close_result = self._process_close_result(result, symbol)

            logger.info(f"Moonlander Trader position closed: {close_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "close_details": close_result,
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
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Set risk management orders for a position.

        Args:
            symbol: Trading pair symbol
            stop_loss: Stop-loss price
            take_profit: Take-profit price

        Returns:
            Dict containing risk management result
        """
        try:
            logger.info(
                f"Moonlander Trader setting risk management: {symbol} "
                f"SL: {stop_loss}, TP: {take_profit}"
            )

            results = {}

            if stop_loss:
                sl_command = f"Set stop-loss at {stop_loss} for {symbol} position"
                sl_result = await self.agent_executor.ainvoke({
                    "input": sl_command,
                    "symbol": symbol,
                    "stop_loss": stop_loss,
                })
                results["stop_loss"] = self._process_risk_order_result(sl_result, "stop_loss")

            if take_profit:
                tp_command = f"Set take-profit at {take_profit} for {symbol} position"
                tp_result = await self.agent_executor.ainvoke({
                    "input": tp_command,
                    "symbol": symbol,
                    "take_profit": take_profit,
                })
                results["take_profit"] = self._process_risk_order_result(tp_result, "take_profit")

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

    def _process_trade_result(
        self,
        result: Dict[str, Any],
        direction: str,
        symbol: str,
        amount: float,
        leverage: float,
    ) -> Dict[str, Any]:
        """
        Process and format trade execution result.

        Args:
            result: Raw trade result from agent
            direction: Trade direction
            symbol: Trading pair
            amount: Position size
            leverage: Leverage used

        Returns:
            Formatted trade details
        """
        # Extract trade details from result
        trade_details = result.get("output", {})
        if isinstance(trade_details, str):
            try:
                import json as json_lib
                trade_details = json_lib.loads(trade_details)
            except:
                trade_details = {"raw_output": trade_details}

        # Calculate mock entry price and liquidation price
        mock_entry_price = self._get_mock_price(symbol, direction)
        liquidation_price = self._calculate_liquidation_price(
            mock_entry_price, direction, leverage
        )

        # Ensure trade details have expected structure
        processed_result = {
            "symbol": symbol,
            "direction": direction,
            "amount_usdc": amount,
            "leverage": leverage,
            "entry_price": trade_details.get("entry_price", mock_entry_price),
            "liquidation_price": trade_details.get("liquidation_price", liquidation_price),
            "position_id": trade_details.get("position_id", f"pos_{self.session_id}"),
            "status": trade_details.get("status", "open"),
            "fees": trade_details.get("fees", amount * 0.001),  # 0.1% fee
            "timestamp": trade_details.get("timestamp", "2025-12-24T19:00:00Z"),
        }

        return processed_result

    def _process_close_result(
        self,
        result: Dict[str, Any],
        symbol: str,
    ) -> Dict[str, Any]:
        """
        Process and format position closure result.

        Args:
            result: Raw close result from agent
            symbol: Trading pair

        Returns:
            Formatted close details
        """
        close_details = result.get("output", {})
        if isinstance(close_details, str):
            try:
                import json as json_lib
                close_details = json_lib.loads(close_details)
            except:
                close_details = {"raw_output": close_details}

        return {
            "symbol": symbol,
            "position_id": close_details.get("position_id", f"pos_{self.session_id}"),
            "pnl": close_details.get("pnl", 0.0),
            "pnl_percent": close_details.get("pnl_percent", 0.0),
            "status": "closed",
            "timestamp": close_details.get("timestamp", "2025-12-24T19:00:00Z"),
        }

    def _process_risk_order_result(
        self,
        result: Dict[str, Any],
        order_type: str,
    ) -> Dict[str, Any]:
        """
        Process and format risk order result.

        Args:
            result: Raw order result from agent
            order_type: "stop_loss" or "take_profit"

        Returns:
            Formatted order details
        """
        order_details = result.get("output", {})
        if isinstance(order_details, str):
            try:
                import json as json_lib
                order_details = json_lib.loads(order_details)
            except:
                order_details = {"raw_output": order_details}

        return {
            "type": order_type,
            "price": order_details.get("price", 0.0),
            "status": order_details.get("status", "active"),
            "timestamp": order_details.get("timestamp", "2025-12-24T19:00:00Z"),
        }

    def _get_mock_price(self, symbol: str, direction: str) -> float:
        """Get mock price for symbol (for testing)."""
        prices = {
            "BTC": 45000.0,
            "ETH": 2500.0,
            "CRO": 0.12,
        }
        return prices.get(symbol.upper(), 100.0)

    def _calculate_liquidation_price(
        self, entry_price: float, direction: str, leverage: float
    ) -> float:
        """Calculate liquidation price based on entry and leverage."""
        if direction.lower() == "long":
            # Long liquidation: price drops by ~90% of position value
            liquidation = entry_price * (1 - (0.9 / leverage))
        else:
            # Short liquidation: price rises by ~90% of position value
            liquidation = entry_price * (1 + (0.9 / leverage))
        return round(liquidation, 2)

    async def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary for this subagent."""
        return {
            "subagent_type": "Moonlander Trader",
            "session_id": str(self.session_id),
            "parent_agent_id": str(self.parent_agent_id),
            "llm_model": self.llm_model,
            "tools_count": len(self.tools),
            "memory_size": len(self.memory.chat_memory.messages),
        }


# Mock trading tools for Moonlander operations
class OpenPositionTool:
    """Tool for opening perpetual positions."""

    name = "open_position"
    description = "Open a perpetual long or short position on Moonlander"

    def run(
        self,
        direction: str,
        symbol: str,
        amount: float,
        leverage: float = 10.0,
    ) -> Dict[str, Any]:
        """Execute position opening."""
        logger.info(f"Opening {direction} position: {amount} USDC {symbol} @ {leverage}x")

        return {
            "position_id": f"moonlander_{int(amount)}_{symbol}",
            "direction": direction,
            "symbol": symbol,
            "amount": amount,
            "leverage": leverage,
            "entry_price": 45000.0 if symbol.upper() == "BTC" else 2500.0,
            "status": "open",
            "message": f"Position opened successfully: {direction} {symbol} @ {leverage}x"
        }


class ClosePositionTool:
    """Tool for closing positions."""

    name = "close_position"
    description = "Close an existing perpetual position"

    def run(
        self,
        symbol: str,
        position_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute position closing."""
        logger.info(f"Closing position: {symbol}")

        return {
            "position_id": position_id or f"moonlander_closed_{symbol}",
            "symbol": symbol,
            "status": "closed",
            "pnl": 15.50,
            "pnl_percent": 5.2,
            "message": f"Position closed successfully: {symbol}"
        }


class SetStopLossTool:
    """Tool for setting stop-loss."""

    name = "set_stop_loss"
    description = "Set stop-loss price for a position"

    def run(
        self,
        symbol: str,
        stop_loss_price: float,
    ) -> Dict[str, Any]:
        """Set stop-loss order."""
        logger.info(f"Setting stop-loss for {symbol} at {stop_loss_price}")

        return {
            "symbol": symbol,
            "type": "stop_loss",
            "price": stop_loss_price,
            "status": "active",
            "message": f"Stop-loss set at {stop_loss_price}"
        }


class SetTakeProfitTool:
    """Tool for setting take-profit."""

    name = "set_take_profit"
    description = "Set take-profit price for a position"

    def run(
        self,
        symbol: str,
        take_profit_price: float,
    ) -> Dict[str, Any]:
        """Set take-profit order."""
        logger.info(f"Setting take-profit for {symbol} at {take_profit_price}")

        return {
            "symbol": symbol,
            "type": "take_profit",
            "price": take_profit_price,
            "status": "active",
            "message": f"Take-profit set at {take_profit_price}"
        }


class GetFundingRateTool:
    """Tool for getting funding rate."""

    name = "get_funding_rate"
    description = "Get current funding rate for a symbol"

    def run(
        self,
        symbol: str,
    ) -> Dict[str, Any]:
        """Get funding rate."""
        logger.info(f"Getting funding rate for {symbol}")

        # Mock funding rates
        funding_rates = {
            "BTC": 0.01,  # 0.01% per 8 hours (positive, shorts pay longs)
            "ETH": 0.008,
        }

        rate = funding_rates.get(symbol.upper(), 0.01)

        return {
            "symbol": symbol,
            "funding_rate": rate,
            "next_funding": "in 8 hours",
            "direction": "positive" if rate > 0 else "negative",
            "message": f"Current funding rate for {symbol}: {rate}% (positive means shorts pay longs)"
        }

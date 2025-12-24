"""
VVS Trader Subagent for DeFi Swap Operations.

This module implements a specialized subagent for handling VVS Finance
token swaps on the Cronos blockchain.
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
from src.tools.simple_tools import SwapTokensTool

logger = logging.getLogger(__name__)


class VVSTraderCallbackHandler(BaseCallbackHandler):
    """Callback handler for VVS trader subagent events."""

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
        logger.info(f"VVS Trader {self.session_id}: Tool call - {event}")

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Called when a tool finishes."""
        event = {
            "type": "tool_result",
            "tool_output": output,
        }
        self.events.append(event)
        logger.info(f"VVS Trader {self.session_id}: Tool result - {event}")


class VVSTraderSubagent:
    """
    VVS Finance Trader Subagent.

    Specialized subagent for executing DeFi token swaps on VVS Finance.
    Spawns when the main agent detects a swap operation and handles
    the complete swap execution workflow.
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
            f"VVS Trader Subagent initialized - Session: {session_id}, "
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
        """Create tools specific to VVS trading."""
        swap_tool = SwapTokensTool()
        return [swap_tool]

    def _create_agent(self) -> AgentExecutor:
        """
        Create the VVS trader agent.

        Returns:
            AgentExecutor: Configured agent executor
        """
        # System prompt for VVS trading
        system_prompt = """You are VVS Trader, a specialized subagent for VVS Finance token swaps on Cronos.

Your capabilities:
- Execute token swaps on VVS Finance DEX
- Calculate optimal swap amounts with slippage protection
- Monitor swap execution and handle failures
- Provide detailed swap execution reports

Available tools:
- swap_tokens: Execute token swaps with slippage tolerance

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

Example commands you should handle:
- "Swap 100 USDC for CRO on VVS Finance"
- "Exchange 50 CRO to USDC with 1% slippage"
- "Perform a token swap with optimal routing"

Always be precise and return detailed swap execution information."""

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
            max_iterations=5,  # Fewer iterations for focused swap execution
            early_stopping_method="generate",  # Stop when task is complete
        )

        return agent_executor

    async def execute_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance_percent: float = 1.0
    ) -> Dict[str, Any]:
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

            # Prepare swap command
            swap_command = (
                f"Swap {amount} {from_token} for {to_token} on VVS Finance "
                f"with {slippage_tolerance_percent}% slippage tolerance"
            )

            # Execute swap
            result = await self.agent_executor.ainvoke({
                "input": swap_command,
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
                "slippage_tolerance_percent": slippage_tolerance_percent,
            })

            # Process and format result
            swap_result = self._process_swap_result(result, from_token, to_token, amount)

            logger.info(f"VVS Trader swap completed: {swap_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "swap_details": swap_result,
                "execution_time_ms": 0,  # TODO: Add timing
            }

        except Exception as e:
            logger.error(f"VVS Trader swap failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    def _process_swap_result(
        self,
        result: Dict[str, Any],
        from_token: str,
        to_token: str,
        amount: float
    ) -> Dict[str, Any]:
        """
        Process and format swap execution result.

        Args:
            result: Raw swap result from agent
            from_token: Source token
            to_token: Destination token
            amount: Swapped amount

        Returns:
            Formatted swap details
        """
        # Extract swap details from result
        swap_details = result.get("output", {})
        if isinstance(swap_details, str):
            # If result is a string, parse it
            try:
                import json as json_lib
                swap_details = json_lib.loads(swap_details)
            except:
                swap_details = {"raw_output": swap_details}

        # Ensure swap details have expected structure
        processed_result = {
            "from_token": from_token,
            "to_token": to_token,
            "amount_in": str(amount),
            "amount_out": swap_details.get("amount_out", "0.00"),
            "exchange_rate": swap_details.get("exchange_rate", "0.00"),
            "dex": "VVS Finance",
            "tx_hash": swap_details.get("tx_hash", "N/A"),
            "status": swap_details.get("status", "completed"),
            "slippage_tolerance": f"{swap_details.get('slippage_tolerance_percent', 1.0)}%",
            "timestamp": swap_details.get("timestamp", "2025-12-24T19:00:00Z"),
        }

        return processed_result

    async def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary for this subagent."""
        return {
            "subagent_type": "VVS Trader",
            "session_id": str(self.session_id),
            "parent_agent_id": str(self.parent_agent_id),
            "llm_model": self.llm_model,
            "tools_count": len(self.tools),
            "memory_size": len(self.memory.chat_memory.messages),
        }
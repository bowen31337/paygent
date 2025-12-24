"""
Main AI Agent for Paygent.

This module implements the core AI agent that handles natural language payment commands
using LangChain framework with Claude and OpenAI models.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.memory import ConversationBufferMemory
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.agent_sessions import AgentSession
from src.services.session_service import SessionService

logger = logging.getLogger(__name__)


class AgentCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for agent execution events."""

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
        logger.info(f"Session {self.session_id}: Tool call - {event}")

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Called when a tool finishes."""
        event = {
            "type": "tool_result",
            "tool_output": output,
        }
        self.events.append(event)
        logger.info(f"Session {self.session_id}: Tool result - {event}")

    def on_agent_action(self, action: Any, **kwargs: Any) -> Any:
        """Called when the agent takes an action."""
        event = {
            "type": "thinking",
            "action": str(action),
        }
        self.events.append(event)
        logger.info(f"Session {self.session_id}: Agent thinking - {event}")


class PaygentAgent:
    """Main AI agent for processing payment commands."""

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

        # Initialize LLM
        self.llm = self._initialize_llm()

        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            session_id=str(session_id),
        )

        # Initialize tools
        self.tools = []

        # Initialize agent
        self.agent_executor = self._create_agent()

    def _initialize_llm(self):
        """Initialize the LLM based on configuration."""
        if "anthropic" in self.llm_model:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model="claude-sonnet-4",
                temperature=0.1,
                max_tokens=4000,
                api_key=settings.anthropic_api_key,
            )
        else:
            return ChatOpenAI(
                model="gpt-4",
                temperature=0.1,
                max_tokens=4000,
                api_key=settings.openai_api_key,
            )

    def _create_agent(self) -> AgentExecutor:
        """
        Create the AI agent with tools and memory.

        Returns:
            AgentExecutor: Configured agent executor
        """
        # System prompt for payment orchestration
        system_prompt = """You are Paygent, an AI-powered payment orchestration agent for the Cronos blockchain.

Your capabilities:
- Execute HTTP 402 (x402) payments using the x402 protocol
- Discover and interact with MCP-compatible services
- Perform DeFi operations (VVS Finance swaps, Moonlander trading, Delphi predictions)
- Manage agent wallets with spending limits and approvals
- Provide human-in-the-loop controls for sensitive operations

Available tools:
- x402_payment: Execute HTTP 402 payments with EIP-712 signatures
- discover_services: Find MCP-compatible services with pricing
- check_balance: Check token balances in agent wallet
- transfer_tokens: Transfer tokens between wallets
- get_approval: Request human approval for sensitive operations

Important guidelines:
1. Always prioritize security - use human approval for transactions over $100 USD
2. Use the x402 protocol for all HTTP 402 payments
3. Check service availability and pricing before executing payments
4. Respect daily spending limits per token
5. Provide clear explanations of actions to users
6. Return structured JSON responses when possible

When users provide natural language commands:
1. Parse the intent and identify required actions
2. Check if human approval is needed based on amount and action type
3. Use appropriate tools to execute the command
4. Return clear success/failure status with details

Example commands you should handle:
- "Pay 0.10 USDC to access the market data API"
- "Swap 100 USDC for CRO on VVS Finance"
- "Open a 10x long position on BTC/USDC on Moonlander"
- "Place a bet on the next US election outcome on Delphi"

Always be helpful, accurate, and security-conscious."""

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

        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
        )

        return agent_executor

    async def add_tool(self, tool) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool)
        self.agent_executor.tools = self.tools

    async def execute_command(
        self, command: str, budget_limit_usd: Optional[float] = None
    ) -> Dict[str, Any]:
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

            # Prepare input
            input_data = {
                "input": command,
                "budget_limit_usd": budget_limit_usd,
            }

            # Execute command
            result = await self.agent_executor.ainvoke(input_data)

            # Update session
            await self.session_service.update_session_last_active(self.session_id)

            return {
                "success": True,
                "result": result["output"],
                "session_id": str(self.session_id),
                "total_cost_usd": 0.0,  # TODO: Calculate actual cost
            }

        except Exception as e:
            logger.error(f"Session {self.session_id}: Command execution failed - {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(self.session_id),
            }

    async def get_session_info(self) -> Dict[str, Any]:
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
"""
Enhanced agent executor with logging, planning, and budget enforcement.

This module provides comprehensive agent execution with:
- Execution logging to database
- write_todos plan generation for complex operations
- Budget limit enforcement
- Tool call tracking
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.agents.command_parser import CommandParser, ParsedCommand
from src.tools.simple_tools import get_all_tools
from src.models.agent_sessions import ExecutionLog, AgentSession, AgentMemory
from src.core.database import get_db

# Try to import the subagents, but fall back gracefully if langchain isn't available
try:
    from src.agents.vvs_trader_subagent import VVSTraderSubagent
    HAS_VVS_SUBAGENT = True
except ImportError:
    VVSTraderSubagent = None
    HAS_VVS_SUBAGENT = False

try:
    from src.agents.moonlander_trader_subagent import MoonlanderTraderSubagent
    HAS_MOONLANDER_SUBAGENT = True
except ImportError:
    MoonlanderTraderSubagent = None
    HAS_MOONLANDER_SUBAGENT = False

logger = logging.getLogger(__name__)


class AgentExecutorEnhanced:
    """
    Enhanced agent executor with logging, planning, and budget enforcement.

    Features:
    1. Parses natural language commands
    2. Creates execution plans (write_todos) for complex operations
    3. Enforces budget limits
    4. Logs all tool calls to execution_logs table
    5. Tracks execution time and cost
    """

    def __init__(self, session_id: UUID, db: AsyncSession):
        """
        Initialize the enhanced agent executor.

        Args:
            session_id: Session ID for this execution
            db: Database session for logging
        """
        self.session_id = session_id
        self.db = db
        self.parser = CommandParser()
        self.tools = get_all_tools()
        self.tool_calls: List[Dict[str, Any]] = []
        self.current_execution_log_id: Optional[UUID] = None
        self.memory: List[Dict[str, Any]] = []

        logger.info(f"AgentExecutorEnhanced initialized for session {session_id}")
        logger.info(f"Available tools: {list(self.tools.keys())}")

    async def load_memory(self) -> None:
        """
        Load conversation memory from database for this session.
        """
        try:
            result = await self.db.execute(
                select(AgentMemory)
                .where(AgentMemory.session_id == self.session_id)
                .order_by(AgentMemory.timestamp)
            )
            memory_records = result.scalars().all()

            self.memory = [
                {
                    "type": record.message_type,
                    "content": record.content,
                    "timestamp": record.timestamp.isoformat(),
                    "metadata": getattr(record, 'extra_data', {}) or {},
                }
                for record in memory_records
            ]

            logger.info(f"Loaded {len(self.memory)} memory entries for session {self.session_id}")
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
            self.memory = []

    async def save_memory(
        self,
        message_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save a message to the conversation memory.

        Args:
            message_type: Type of message ('human', 'ai', 'system')
            content: The message content
            metadata: Optional additional metadata
        """
        try:
            # Use extra_data attribute which maps to metadata column
            memory_entry = AgentMemory(
                id=uuid4(),
                session_id=self.session_id,
                message_type=message_type,
                content=content,
                extra_data=metadata or {},
            )
            self.db.add(memory_entry)
            await self.db.commit()

            # Also update in-memory cache
            self.memory.append({
                "type": message_type,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            })

            logger.debug(f"Saved memory entry: {message_type}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            await self.db.rollback()

    def get_memory_context(self, max_messages: int = 10) -> str:
        """
        Get formatted memory context for LLM prompts.

        Args:
            max_messages: Maximum number of recent messages to include

        Returns:
            Formatted string of conversation history
        """
        if not self.memory:
            return ""

        recent = self.memory[-max_messages:]
        context_parts = []

        for msg in recent:
            role = "User" if msg["type"] == "human" else "Assistant" if msg["type"] == "ai" else "System"
            context_parts.append(f"{role}: {msg['content']}")

        return "\n".join(context_parts)

    async def execute_command(
        self,
        command: str,
        budget_limit_usd: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a natural language command with full logging and planning.

        Args:
            command: Natural language command to execute
            budget_limit_usd: Optional budget limit in USD

        Returns:
            Dict containing execution result
        """
        start_time = time.time()
        logger.info(f"Session {self.session_id}: Executing command - {command}")

        # Load existing memory for this session
        await self.load_memory()

        # Create execution log
        execution_log = ExecutionLog(
            id=uuid4(),
            session_id=self.session_id,
            command=command,
            tool_calls=[],
            result=None,
            total_cost=0.0,
            duration_ms=0,
            status="running",
        )
        self.db.add(execution_log)
        await self.db.commit()
        self.current_execution_log_id = execution_log.id

        try:
            # Step 1: Parse the command
            parsed = self.parser.parse(command)
            logger.info(
                f"Parsed intent: {parsed.intent} "
                f"(confidence: {parsed.confidence:.2f})"
            )

            # Step 2: Generate plan for complex operations
            plan = self._generate_execution_plan(parsed, command)
            execution_log.plan = plan

            # Step 3: Execute based on intent
            if parsed.intent == "payment":
                result = await self._execute_payment_with_logging(
                    parsed, budget_limit_usd
                )

            elif parsed.intent == "swap":
                result = await self._execute_swap_with_logging(
                    parsed, budget_limit_usd
                )

            elif parsed.intent == "perpetual_trade":
                result = await self._execute_perpetual_trade_with_logging(
                    parsed, budget_limit_usd
                )

            elif parsed.intent == "balance_check":
                result = await self._execute_balance_check_with_logging(parsed)

            elif parsed.intent == "service_discovery":
                result = await self._execute_service_discovery_with_logging(parsed)

            else:
                # Unknown intent - return helpful error
                result = {
                    "success": False,
                    "error": "Could not understand command intent. Please rephrase.",
                    "suggestions": [
                        "Pay 0.10 USDC to API service",
                        "Check my wallet balance",
                        "Swap 10 CRO for USDC",
                        "Open a 100 USDC long position on BTC with 10x leverage",
                        "Find available services"
                    ],
                    "parsed_intent": parsed.intent,
                    "confidence": parsed.confidence
                }

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Update execution log
            execution_log.result = result
            execution_log.tool_calls = self.tool_calls
            execution_log.duration_ms = duration_ms
            execution_log.total_cost = result.get("total_cost_usd", 0.0)
            execution_log.status = "completed" if result.get("success") else "failed"
            await self.db.commit()

            # Store conversation in memory for persistence across commands
            # Save user message
            await self.save_memory(
                message_type="human",
                content=command,
                metadata={
                    "intent": parsed.intent,
                    "confidence": parsed.confidence,
                }
            )

            # Save agent response
            await self.save_memory(
                message_type="ai",
                content=json.dumps(result),
                metadata={
                    "duration_ms": duration_ms,
                    "success": result.get("success", False),
                    "total_cost_usd": result.get("total_cost_usd", 0.0),
                }
            )

            # Add metadata to result
            result["session_id"] = str(self.session_id)
            result["command"] = command
            result["parsed_intent"] = parsed.intent
            result["confidence"] = parsed.confidence
            result["execution_log_id"] = str(execution_log.id)
            result["duration_ms"] = duration_ms
            result["plan"] = plan
            result["memory_context"] = self.get_memory_context()

            return result

        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)

            # Update execution log with error
            duration_ms = int((time.time() - start_time) * 1000)
            execution_log.result = {
                "success": False,
                "error": str(e),
            }
            execution_log.tool_calls = self.tool_calls
            execution_log.duration_ms = duration_ms
            execution_log.status = "failed"
            await self.db.commit()

            return {
                "success": False,
                "error": str(e),
                "session_id": str(self.session_id),
                "command": command,
                "execution_log_id": str(execution_log.id),
            }

    def _generate_execution_plan(
        self,
        parsed: ParsedCommand,
        command: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a write_todos style execution plan.

        For complex operations, creates a structured plan with steps.

        Args:
            parsed: Parsed command
            command: Original command text

        Returns:
            Plan dictionary with steps, or None for simple operations
        """
        # Simple commands don't need complex plans
        if parsed.intent in ["balance_check", "service_discovery"]:
            return None

        # Create plan for payment/swap/perpetual trade operations
        if parsed.intent == "payment":
            return {
                "approach": "Execute x402 payment flow",
                "steps": [
                    {
                        "id": 1,
                        "description": "Parse payment parameters",
                        "outcome": "Extract amount, token, and recipient",
                        "status": "completed"
                    },
                    {
                        "id": 2,
                        "description": "Discover service endpoint",
                        "outcome": "Identify service URL from recipient description",
                        "status": "pending"
                    },
                    {
                        "id": 3,
                        "description": "Execute x402 payment",
                        "outcome": "Complete payment via facilitator",
                        "status": "pending"
                    },
                    {
                        "id": 4,
                        "description": "Verify payment settlement",
                        "outcome": "Confirm on-chain transaction",
                        "status": "pending"
                    }
                ],
                "total_steps": 4,
                "created_at": datetime.utcnow().isoformat()
            }

        elif parsed.intent == "swap":
            return {
                "approach": "Execute token swap on DEX",
                "steps": [
                    {
                        "id": 1,
                        "description": "Parse swap parameters",
                        "outcome": "Extract tokens and amount",
                        "status": "completed"
                    },
                    {
                        "id": 2,
                        "description": "Get price quote from DEX",
                        "outcome": "Obtain expected output amount",
                        "status": "pending"
                    },
                    {
                        "id": 3,
                        "description": "Execute swap transaction",
                        "outcome": "Complete token exchange",
                        "status": "pending"
                    },
                    {
                        "id": 4,
                        "description": "Verify token balances",
                        "outcome": "Confirm new balances",
                        "status": "pending"
                    }
                ],
                "total_steps": 4,
                "created_at": datetime.utcnow().isoformat()
            }

        elif parsed.intent == "perpetual_trade":
            return {
                "approach": "Execute perpetual trade via Moonlander",
                "steps": [
                    {
                        "id": 1,
                        "description": "Parse trade parameters",
                        "outcome": "Extract direction, symbol, amount, leverage",
                        "status": "completed"
                    },
                    {
                        "id": 2,
                        "description": "Spawn Moonlander subagent",
                        "outcome": "Create specialized trading agent",
                        "status": "pending"
                    },
                    {
                        "id": 3,
                        "description": "Open position",
                        "outcome": "Execute perpetual trade with risk management",
                        "status": "pending"
                    },
                    {
                        "id": 4,
                        "description": "Set stop-loss/take-profit",
                        "outcome": "Configure risk management orders",
                        "status": "pending"
                    }
                ],
                "total_steps": 4,
                "created_at": datetime.utcnow().isoformat()
            }

        return None

    async def _log_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any
    ) -> None:
        """
        Log a tool call to the execution log.

        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to the tool
            tool_result: Result returned by the tool
        """
        tool_call = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "result": tool_result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.tool_calls.append(tool_call)
        logger.info(f"Tool call logged: {tool_name}")

    async def _execute_payment_with_logging(
        self,
        parsed: ParsedCommand,
        budget_limit_usd: Optional[float]
    ) -> Dict[str, Any]:
        """Execute a payment command with logging."""
        params = parsed.parameters

        # Step 1: Check budget limit
        if budget_limit_usd and params.get("amount", 0) > budget_limit_usd:
            return {
                "success": False,
                "error": f"Payment amount ${params['amount']} exceeds budget limit ${budget_limit_usd}",
                "suggestion": "Increase budget limit or reduce payment amount",
                "total_cost_usd": 0.0
            }

        # Step 2: Discover service endpoint
        await self._log_tool_call(
            "resolve_service_endpoint",
            {"recipient": params.get("recipient", "api")},
            {"status": "executing"}
        )

        service_url = self._resolve_service_endpoint(params.get("recipient", "api"))

        await self._log_tool_call(
            "resolve_service_endpoint",
            {"recipient": params.get("recipient", "api")},
            {"service_url": service_url, "status": "completed"}
        )

        # Step 3: Execute x402 payment
        tool = self.tools["x402_payment"]
        payment_result = tool.run(
            service_url=service_url,
            amount=params["amount"],
            token=params.get("token", "USDC")
        )

        await self._log_tool_call(
            "x402_payment",
            {
                "service_url": service_url,
                "amount": params["amount"],
                "token": params.get("token", "USDC")
            },
            payment_result
        )

        return {
            "success": True,
            "action": "payment",
            "result": payment_result,
            "total_cost_usd": params.get("amount", 0.0)
        }

    async def _execute_swap_with_logging(
        self,
        parsed: ParsedCommand,
        budget_limit_usd: Optional[float]
    ) -> Dict[str, Any]:
        """Execute a swap command with VVS subagent (or fallback to simple tool) and logging."""
        params = parsed.parameters

        if HAS_VVS_SUBAGENT and VVSTraderSubagent:
            # Create VVS trader subagent
            vvs_subagent = VVSTraderSubagent(
                db=self.db,
                session_id=self.session_id,
                parent_agent_id=self.session_id,
            )

            # Execute swap via subagent
            swap_result = await vvs_subagent.execute_swap(
                from_token=params["from_token"],
                to_token=params["to_token"],
                amount=params["amount"]
            )

            await self._log_tool_call(
                "vvs_trader_subagent",
                {
                    "from_token": params["from_token"],
                    "to_token": params["to_token"],
                    "amount": params["amount"]
                },
                swap_result
            )
        else:
            # Fallback to simple swap tool
            tool = self.tools["swap_tokens"]
            swap_result = tool.run(
                from_token=params["from_token"],
                to_token=params["to_token"],
                amount=params["amount"]
            )

            await self._log_tool_call(
                "swap_tokens",
                {
                    "from_token": params["from_token"],
                    "to_token": params["to_token"],
                    "amount": params["amount"]
                },
                swap_result
            )

        return {
            "success": True,
            "action": "swap_via_vvs_subagent" if HAS_VVS_SUBAGENT else "swap",
            "result": swap_result,
            "total_cost_usd": 0.0  # Swaps don't have a direct cost (gas is separate)
        }

    async def _execute_perpetual_trade_with_logging(
        self,
        parsed: ParsedCommand,
        budget_limit_usd: Optional[float]
    ) -> Dict[str, Any]:
        """Execute a perpetual trade command with Moonlander subagent and logging."""
        params = parsed.parameters

        # Step 1: Check budget limit
        if budget_limit_usd and params.get("amount", 0) > budget_limit_usd:
            return {
                "success": False,
                "error": f"Position size ${params['amount']} exceeds budget limit ${budget_limit_usd}",
                "suggestion": "Increase budget limit or reduce position size",
                "total_cost_usd": 0.0
            }

        # Step 2: Log trade parameters
        await self._log_tool_call(
            "parse_perpetual_trade",
            {
                "direction": params.get("direction", "long"),
                "symbol": params.get("symbol", "BTC"),
                "amount": params["amount"],
                "token": params.get("token", "USDC"),
                "leverage": params.get("leverage", 10.0),
            },
            {"status": "parsed"}
        )

        # Step 3: Spawn Moonlander subagent and execute trade
        if HAS_MOONLANDER_SUBAGENT and MoonlanderTraderSubagent:
            # Create Moonlander trader subagent
            moonlander_subagent = MoonlanderTraderSubagent(
                db=self.db,
                session_id=uuid4(),  # New session for subagent
                parent_agent_id=self.session_id,
            )

            # Execute perpetual trade via subagent
            trade_result = await moonlander_subagent.execute_perpetual_trade(
                direction=params.get("direction", "long"),
                symbol=params.get("symbol", "BTC"),
                amount=params["amount"],
                leverage=params.get("leverage", 10.0),
            )

            await self._log_tool_call(
                "moonlander_trader_subagent",
                {
                    "direction": params.get("direction", "long"),
                    "symbol": params.get("symbol", "BTC"),
                    "amount": params["amount"],
                    "leverage": params.get("leverage", 10.0),
                },
                trade_result
            )

            # Step 4: Set risk management orders if trade was successful
            if trade_result.get("success"):
                risk_result = await moonlander_subagent.set_risk_management(
                    symbol=params.get("symbol", "BTC"),
                    stop_loss=trade_result["trade_details"]["liquidation_price"] * 0.95,  # 5% from liquidation
                    take_profit=trade_result["trade_details"]["entry_price"] * 1.1,  # 10% profit
                )

                await self._log_tool_call(
                    "set_risk_management",
                    {
                        "symbol": params.get("symbol", "BTC"),
                        "stop_loss": trade_result["trade_details"]["liquidation_price"] * 0.95,
                        "take_profit": trade_result["trade_details"]["entry_price"] * 1.1,
                    },
                    risk_result
                )

                # Combine results
                return {
                    "success": True,
                    "action": "perpetual_trade",
                    "result": {
                        "trade": trade_result,
                        "risk_management": risk_result,
                    },
                    "total_cost_usd": 0.0,  # Trading doesn't have direct cost (fees are separate)
                }
            else:
                return trade_result
        else:
            # Fallback to simple tool if subagent not available
            tool = self.tools.get("swap_tokens")  # Reuse swap tool as fallback
            if tool:
                trade_result = tool.run(
                    from_token=params.get("token", "USDC"),
                    to_token=params.get("symbol", "BTC"),
                    amount=params["amount"]
                )

                await self._log_tool_call(
                    "perpetual_trade_fallback",
                    {
                        "direction": params.get("direction", "long"),
                        "symbol": params.get("symbol", "BTC"),
                        "amount": params["amount"],
                    },
                    trade_result
                )

                return {
                    "success": True,
                    "action": "perpetual_trade_fallback",
                    "result": trade_result,
                    "total_cost_usd": 0.0,
                }
            else:
                return {
                    "success": False,
                    "error": "Moonlander subagent not available and no fallback tool",
                }

    async def _execute_balance_check_with_logging(
        self,
        parsed: ParsedCommand
    ) -> Dict[str, Any]:
        """Execute a balance check command with logging."""
        params = parsed.parameters

        # Check balance
        tool = self.tools["check_balance"]
        balance_result = tool.run(
            tokens=params.get("tokens", ["CRO", "USDC"])
        )

        await self._log_tool_call(
            "check_balance",
            {"tokens": params.get("tokens", ["CRO", "USDC"])},
            balance_result
        )

        return {
            "success": True,
            "action": "balance_check",
            "result": balance_result,
            "total_cost_usd": 0.0
        }

    async def _execute_service_discovery_with_logging(
        self,
        parsed: ParsedCommand
    ) -> Dict[str, Any]:
        """Execute a service discovery command with logging."""
        params = parsed.parameters

        # Discover services
        tool = self.tools["discover_services"]
        discovery_result = tool.run(
            category=params.get("category"),
            mcp_compatible=True
        )

        await self._log_tool_call(
            "discover_services",
            {"category": params.get("category"), "mcp_compatible": True},
            discovery_result
        )

        return {
            "success": True,
            "action": "service_discovery",
            "result": discovery_result,
            "total_cost_usd": 0.0
        }

    def _resolve_service_endpoint(self, service_name: str) -> str:
        """
        Intelligently resolve a service name to its endpoint.

        Args:
            service_name: Name or description of the service

        Returns:
            Service URL for the discovered service, or fallback URL
        """
        try:
            logger.info(f"Resolving service: {service_name}")

            # Try to discover service using the services tool
            discover_tool = self.tools.get("discover_services")
            if discover_tool:
                result = discover_tool.run(category=None, mcp_compatible=True)

                if result.get("success") and result.get("services"):
                    services = result["services"]

                    # Look for exact matches first
                    for service in services:
                        if service_name.lower() in service["name"].lower():
                            logger.info(f"Found match: {service['name']} -> {service['endpoint']}")
                            return service["endpoint"]

                        if service_name.lower() in service["description"].lower():
                            logger.info(f"Found description match: {service['name']}")
                            return service["endpoint"]

                    # If no exact match, return the first MCP-compatible service
                    if services:
                        logger.info(f"No exact match, using first service: {services[0]['name']}")
                        return services[0]["endpoint"]

            # Fallback to hardcoded URL
            logger.warning(f"Service discovery failed for '{service_name}', using fallback")
            return "https://api.example.com"

        except Exception as e:
            logger.error(f"Service resolution failed: {e}")
            return "https://api.example.com"


async def execute_agent_command_enhanced(
    command: str,
    session_id: UUID,
    db: AsyncSession,
    budget_limit_usd: Optional[float] = None
) -> Dict[str, Any]:
    """
    Convenience function to execute an agent command with enhanced logging.

    Args:
        command: Natural language command
        session_id: Session ID
        db: Database session
        budget_limit_usd: Optional budget limit

    Returns:
        Execution result
    """
    executor = AgentExecutorEnhanced(session_id, db)
    return await executor.execute_command(command, budget_limit_usd)

"""
Enhanced agent executor with logging, planning, and budget enforcement.

This module provides comprehensive agent execution with:
- Execution logging to database
- write_todos plan generation for complex operations
- Budget limit enforcement
- Tool call tracking
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.command_parser import CommandParser, ParsedCommand
from src.core.config import settings
from src.core.security import ToolAllowlistError, get_tool_allowlist
from src.models.agent_sessions import AgentMemory, ExecutionLog
from src.services.alerting_service import AlertType, send_error_alert
from src.services.approval_service import ApprovalService
from src.services.metrics_service import metrics_collector
from src.services.x402_service import X402PaymentService
from src.tools.simple_tools import get_all_tools

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

    def __init__(self, session_id: UUID, db: AsyncSession, use_allowlist: bool = True):
        """
        Initialize the enhanced agent executor.

        Args:
            session_id: Session ID for this execution
            db: Database session for logging
            use_allowlist: Whether to enforce tool allowlist security
        """
        self.session_id = session_id
        self.db = db
        self.parser = CommandParser()
        self.tools = get_all_tools()
        self.tool_calls: list[dict[str, Any]] = []
        self.current_execution_log_id: UUID | None = None
        self.memory: list[dict[str, Any]] = []
        self.use_allowlist = use_allowlist
        self.allowlist = get_tool_allowlist() if use_allowlist else None

        logger.info(f"AgentExecutorEnhanced initialized for session {session_id}")
        logger.info(f"Available tools: {list(self.tools.keys())}")
        if use_allowlist:
            logger.info(f"Tool allowlist enabled: {len(self.allowlist.allowed_tools)} allowed tools")

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
        metadata: dict[str, Any] | None = None
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

    def _validate_intent_allowed(self, intent: str) -> bool:
        """
        Validate that an intent is allowed by the tool allowlist.

        Args:
            intent: The parsed intent to validate

        Returns:
            True if the intent is allowed, False otherwise

        Raises:
            ToolAllowlistError: If the intent is not allowed
        """
        if not self.use_allowlist or self.allowlist is None:
            return True

        # Map intents to their corresponding tool names
        intent_to_tool = {
            "payment": "x402_payment",
            "swap": "swap_tokens",
            "perpetual_trade": "moonlander_trader",  # Will use subagent
            "balance_check": "check_balance",
            "service_discovery": "discover_services",
        }

        tool_name = intent_to_tool.get(intent)
        if tool_name:
            # Validate the tool
            self.allowlist.validate_tool_call(tool_name, {})
            return True

        # Unknown intent - allow by default but log warning
        logger.warning(f"Unknown intent '{intent}' - allowing but may need allowlist update")
        return True

    async def execute_command(
        self,
        command: str,  # noqa: ARG002
        budget_limit_usd: float | None = None,  # noqa: ARG002
        timeout_seconds: float = 30.0
    ) -> dict[str, Any]:
        """
        Execute a natural language command with full logging and planning.

        Args:
            command: Natural language command to execute
            budget_limit_usd: Optional budget limit in USD
            timeout_seconds: Maximum execution time in seconds (default: 30s for simple operations)

        Returns:
            Dict containing execution result

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        start_time = time.time()
        logger.info(f"Session {self.session_id}: Executing command - {command}")
        logger.info(f"Timeout set to {timeout_seconds}s for this execution")

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

            # Step 2: Validate intent against allowlist
            try:
                self._validate_intent_allowed(parsed.intent)
            except ToolAllowlistError as e:
                # Send security alert for allowlist violation
                if settings.alert_enabled:
                    send_error_alert(
                        alert_type=AlertType.ALLOWLIST_VIOLATION,
                        message=f"Tool allowlist violation: {str(e)}",
                        details={
                            "session_id": str(self.session_id),
                            "command": command,
                            "intent": parsed.intent,
                        },
                    )

                # Update execution log with error
                duration_ms = int((time.time() - start_time) * 1000)
                execution_log.result = {
                    "success": False,
                    "error": str(e),
                    "allowlist_violation": True,
                }
                execution_log.tool_calls = self.tool_calls
                execution_log.duration_ms = duration_ms
                execution_log.status = "blocked"
                await self.db.commit()

                return {
                    "success": False,
                    "error": str(e),
                    "allowlist_violation": True,
                    "session_id": str(self.session_id),
                    "command": command,
                    "execution_log_id": str(execution_log.id),
                }

            # Step 3: Generate plan for complex operations
            plan = self._generate_execution_plan(parsed, command)
            execution_log.plan = plan

            # Step 4: Execute based on intent with timeout enforcement
            # For simple operations (balance_check, service_discovery), use shorter timeout
            execution_timeout = timeout_seconds
            if parsed.intent in ["balance_check", "service_discovery"]:
                execution_timeout = min(timeout_seconds, 10.0)  # 10s max for simple queries
                logger.info(f"Using {execution_timeout}s timeout for simple {parsed.intent} operation")

            try:
                # Execute with timeout
                async def execute_with_timeout():
                    if parsed.intent == "payment":
                        return await self._execute_payment_with_logging(
                            parsed, budget_limit_usd
                        )
                    elif parsed.intent == "swap":
                        return await self._execute_swap_with_logging(
                            parsed, budget_limit_usd
                        )
                    elif parsed.intent == "perpetual_trade":
                        return await self._execute_perpetual_trade_with_logging(
                            parsed, budget_limit_usd
                        )
                    elif parsed.intent == "balance_check":
                        return await self._execute_balance_check_with_logging(parsed)
                    elif parsed.intent == "service_discovery":
                        return await self._execute_service_discovery_with_logging(parsed)
                    else:
                        # Unknown intent - return helpful error
                        return {
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

                result = await asyncio.wait_for(
                    execute_with_timeout(),
                    timeout=execution_timeout
                )

            except TimeoutError:
                # Handle timeout
                logger.error(f"Command execution exceeded {execution_timeout}s timeout")
                result = {
                    "success": False,
                    "error": f"Operation timed out after {execution_timeout:.1f} seconds. Please try a simpler command or contact support.",
                    "timeout_seconds": execution_timeout,
                    "timeout_exceeded": True,
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
        command: str  # noqa: ARG002
    ) -> dict[str, Any] | None:
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
        tool_args: dict[str, Any],
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
        budget_limit_usd: float | None  # noqa: ARG002
    ) -> dict[str, Any]:
        """Execute a payment command with HITL approval checks and logging using X402PaymentService."""
        params = parsed.parameters
        amount = params["amount"]
        token = params.get("token", "USDC")

        # Step 1: Check budget limit
        if budget_limit_usd and amount > budget_limit_usd:
            return {
                "success": False,
                "error": f"Payment amount ${amount} exceeds budget limit ${budget_limit_usd}",
                "suggestion": "Increase budget limit or reduce payment amount",
                "total_cost_usd": 0.0
            }

        # Step 2: Check if high-value transaction requires HITL approval
        high_value_threshold = 10.0  # $10 threshold for approval
        requires_approval = amount > high_value_threshold

        if requires_approval:
            # Create approval request
            approval_service = ApprovalService(self.db)
            approval_request = await approval_service.create_approval_request(
                session_id=self.session_id,
                tool_name="x402_payment",
                tool_args={
                    "service_url": None,  # Will be resolved after approval
                    "amount": amount,
                    "token": token,
                    "description": f"Payment for {params.get('recipient', 'service')}",
                },
                amount=amount,
                token=token,
            )

            return {
                "success": False,
                "requires_approval": True,
                "approval_id": str(approval_request.id),
                "amount": amount,
                "token": token,
                "message": f"Payment of ${amount} {token} requires human approval (amount exceeds ${high_value_threshold})",
                "next_steps": "Use /api/v1/approvals/{approval_id}/approve to approve, or /reject to reject",
                "total_cost_usd": 0.0
            }

        # Step 3: Discover service endpoint
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

        # Step 4: Execute x402 payment using X402PaymentService
        x402_service = X402PaymentService()
        payment_result = await x402_service.execute_payment(
            service_url=service_url,
            amount=params["amount"],
            token=params.get("token", "USDC"),
            description=f"Payment for {service_url}",
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

        # Return result with signature info if available
        return {
            "success": payment_result.get("success", False),
            "action": "payment",
            "result": payment_result,
            "total_cost_usd": params.get("amount", 0.0) if payment_result.get("success") else 0.0
        }

    async def _execute_swap_with_logging(
        self,
        parsed: ParsedCommand,
        budget_limit_usd: float | None  # noqa: ARG002
    ) -> dict[str, Any]:
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
        budget_limit_usd: float | None  # noqa: ARG002
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
    budget_limit_usd: float | None = None,
    timeout_seconds: float = 30.0
) -> dict[str, Any]:
    """
    Convenience function to execute an agent command with enhanced logging.

    Args:
        command: Natural language command
        session_id: Session ID
        db: Database session
        budget_limit_usd: Optional budget limit
        timeout_seconds: Maximum execution time in seconds (default: 30s)

    Returns:
        Execution result
    """
    start_time = time.time()
    executor = AgentExecutorEnhanced(session_id, db)
    result = await executor.execute_command(command, budget_limit_usd, timeout_seconds)

    # Record metrics
    duration_seconds = time.time() - start_time
    success = result.get("success", False)
    metrics_collector.record_agent_execution(duration_seconds, success=success)

    return result

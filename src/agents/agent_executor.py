"""
Enhanced agent executor that combines command parsing with tool execution.

This module provides the actual agent execution logic that parses natural language
commands and executes them using available tools.
"""

import logging
from typing import Any
from uuid import UUID

from src.agents.command_parser import CommandParser, ParsedCommand
from src.tools.simple_tools import get_all_tools

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Execute natural language commands using parsed intents and tools.

    This executor:
    1. Parses the natural language command to extract intent
    2. Routes to appropriate tool based on intent
    3. Executes the tool with extracted parameters
    4. Returns structured result
    """

    def __init__(self, session_id: UUID):
        """
        Initialize the agent executor.

        Args:
            session_id: Session ID for this execution
        """
        self.session_id = session_id
        self.parser = CommandParser()
        self.tools = get_all_tools()  # Already returns a dict
        logger.info(f"AgentExecutor initialized for session {session_id}")
        logger.info(f"Available tools: {list(self.tools.keys())}")

    async def execute_command(
        self,
        command: str,
        budget_limit_usd: float | None  # noqa: ARG002 = None
    ) -> dict[str, Any]:
        """
        Execute a natural language command.

        Args:
            command: Natural language command to execute
            budget_limit_usd: Optional budget limit in USD

        Returns:
            Dict containing execution result
        """
        logger.info(f"Session {self.session_id}: Executing command - {command}")

        try:
            # Step 1: Parse the command
            parsed = self.parser.parse(command)
            logger.info(
                f"Parsed intent: {parsed.intent} "
                f"(confidence: {parsed.confidence:.2f})"
            )

            # Step 2: Execute based on intent
            if parsed.intent == "payment":
                result = await self._execute_payment(parsed, budget_limit_usd)

            elif parsed.intent == "swap":
                result = await self._execute_swap(parsed, budget_limit_usd)

            elif parsed.intent == "balance_check":
                result = await self._execute_balance_check(parsed)

            elif parsed.intent == "service_discovery":
                result = await self._execute_service_discovery(parsed)

            else:
                # Unknown intent - return helpful error
                result = {
                    "success": False,
                    "error": "Could not understand command intent. Please rephrase your command.",
                    "suggestions": [
                        "Pay 0.10 USDC to API service",
                        "Check my wallet balance",
                        "Swap 10 CRO for USDC",
                        "Find available services"
                    ],
                    "parsed_intent": parsed.intent,
                    "confidence": parsed.confidence
                }

            # Add metadata
            result["session_id"] = str(self.session_id)
            result["command"] = command
            result["parsed_intent"] = parsed.intent
            result["confidence"] = parsed.confidence

            return result

        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "session_id": str(self.session_id),
                "command": command
            }

    async def _execute_payment(
        self,
        parsed: ParsedCommand,
        budget_limit_usd: float | None  # noqa: ARG002
    ) -> dict[str, Any]:
        """Execute a payment command."""
        params = parsed.parameters

        # Check budget limit
        if budget_limit_usd and params.get("amount", 0) > budget_limit_usd:
            return {
                "success": False,
                "error": f"Payment amount ${params['amount']} exceeds budget limit ${budget_limit_usd}",
                "suggestion": "Increase budget limit or reduce payment amount"
            }

        # Intelligently discover service endpoint
        print(f"DEBUG: Calling _resolve_service_endpoint with: {params.get('recipient', 'api')}")
        service_url = self._resolve_service_endpoint(params.get("recipient", "api"))
        print(f"DEBUG: Resolved service URL: {service_url}")

        # Execute x402 payment
        tool = self.tools["x402_payment"]
        result = tool.run(
            service_url=service_url,
            amount=params["amount"],
            token=params.get("token", "USDC")
        )

        return {
            "success": True,
            "action": "payment",
            "result": result
        }

    def _resolve_service_endpoint(self, service_name: str) -> str:
        """
        Intelligently resolve a service name to its endpoint.

        Args:
            service_name: Name or description of the service (e.g., "market data", "API")

        Returns:
            Service URL for the discovered service, or fallback URL
        """
        print(f"DEBUG: _resolve_service_endpoint called with: {service_name}")
        try:
            print(f"DEBUG: Resolving service: {service_name}")
            # Try to discover service using the services tool
            discover_tool = self.tools.get("discover_services")
            if discover_tool:
                print("DEBUG: Found discover_services tool")
                # Search for services containing the service name
                result = discover_tool.run(category=None, mcp_compatible=True)
                print(f"DEBUG: Discovery result: {result}")

                if result.get("services"):
                    services = result["services"]
                    print(f"DEBUG: Found {len(services)} services")

                    # Normalize query for better matching
                    query_lower = service_name.lower().strip()

                    # Look for exact matches first
                    for service in services:
                        service_name_lower = service["name"].lower()
                        service_desc_lower = service.get("description", "").lower()

                        print(f"DEBUG: Checking service: '{service_name_lower}' vs query: '{query_lower}'")

                        # Check if query is in service name
                        if query_lower in service_name_lower:
                            print(f"DEBUG: Found name match: {service['name']} -> {service['endpoint']}")
                            return str(service["endpoint"])

                        # Check if query is in service description
                        if query_lower in service_desc_lower:
                            print(f"DEBUG: Found description match: {service['name']} -> {service['endpoint']}")
                            return str(service["endpoint"])

                    # Try partial matching - look for key terms
                    key_terms = ['market', 'data', 'api', 'cronos', 'crypto', 'trading']
                    for service in services:
                        service_name_lower = service["name"].lower()
                        service_desc_lower = service.get("description", "").lower()

                        # Count how many key terms match
                        matches = sum(1 for term in key_terms if term in query_lower and term in service_name_lower)

                        if matches >= 2:  # At least 2 key terms match
                            print(f"DEBUG: Found partial match with {matches} key terms: {service['name']} -> {service['endpoint']}")
                            return str(service["endpoint"])

                    # If no exact match, return the first MCP-compatible service
                    if services:
                        print(f"DEBUG: No exact match for '{service_name}', using first available service: {services[0]['name']}")
                        return str(services[0]["endpoint"])

            # Fallback to hardcoded URL
            print(f"DEBUG: Service discovery failed for '{service_name}', using fallback URL")
            return "https://api.example.com"

        except Exception as e:
            print(f"DEBUG: Service resolution failed: {e}")
            return "https://api.example.com"

    async def _execute_swap(
        self,
        parsed: ParsedCommand,
        budget_limit_usd: float | None  # noqa: ARG002
    ) -> dict[str, Any]:
        """Execute a token swap command."""
        params = parsed.parameters

        # Execute swap
        tool = self.tools["swap_tokens"]
        result = tool.run(
            from_token=params["from_token"],
            to_token=params["to_token"],
            amount=params["amount"]
        )

        return {
            "success": True,
            "action": "swap",
            "result": result
        }

    async def _execute_balance_check(
        self,
        parsed: ParsedCommand
    ) -> dict[str, Any]:
        """Execute a balance check command."""
        params = parsed.parameters

        # Check balance
        tool = self.tools["check_balance"]
        result = tool.run(
            tokens=params.get("tokens", ["CRO", "USDC"])
        )

        return {
            "success": True,
            "action": "balance_check",
            "result": result
        }

    async def _execute_service_discovery(
        self,
        parsed: ParsedCommand
    ) -> dict[str, Any]:
        """Execute a service discovery command."""
        params = parsed.parameters

        # Discover services
        tool = self.tools["discover_services"]
        result = tool.run(
            category=params.get("category"),
            mcp_compatible=True
        )

        return {
            "success": True,
            "action": "service_discovery",
            "result": result
        }


async def execute_agent_command(
    command: str,
    session_id: UUID,
    budget_limit_usd: float | None = None
) -> dict[str, Any]:
    """
    Convenience function to execute an agent command.

    Args:
        command: Natural language command
        session_id: Session ID
        budget_limit_usd: Optional budget limit

    Returns:
        Execution result
    """
    executor = AgentExecutor(session_id)
    return await executor.execute_command(command, budget_limit_usd)

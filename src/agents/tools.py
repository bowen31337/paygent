"""
Agent tools for the Paygent AI agent.

This module contains LangChain tools that the agent can use to execute
payment commands and interact with the blockchain.
"""

import logging
from typing import Any

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.service_registry import ServiceRegistryService
from src.services.x402_service import X402PaymentService

logger = logging.getLogger(__name__)


class X402PaymentInput(BaseModel):
    """Input schema for x402 payment tool."""

    service_url: str = Field(..., description="URL of the service to pay")
    amount: float = Field(..., description="Amount to pay")
    token: str = Field(..., description="Token symbol (e.g., USDC, CRO)")
    description: str | None = Field(None, description="Description of the payment")


class X402PaymentTool(BaseTool):
    """Tool for executing x402 payments."""

    name: str = "x402_payment"
    description: str = (
        "Execute an HTTP 402 payment using the x402 protocol. "
        "Use this when you need to pay for a service that returns HTTP 402 Payment Required."
    )
    args_schema = X402PaymentInput

    def __init__(self, payment_service: X402PaymentService):
        super().__init__()
        self.payment_service = payment_service

    async def _arun(
        self, service_url: str, amount: float, token: str, description: str | None = None
    ) -> dict[str, Any]:
        """
        Execute an x402 payment.

        Args:
            service_url: URL of the service to pay
            amount: Amount to pay
            token: Token symbol
            description: Optional description

        Returns:
            Dict containing payment result
        """
        try:
            logger.info(f"Executing x402 payment: {amount} {token} to {service_url}")

            # Execute payment
            result = await self.payment_service.execute_payment(
                service_url=service_url,
                amount=amount,
                token=token,
                description=description,
            )

            return {
                "success": True,
                "payment_id": result.get("payment_id"),
                "tx_hash": result.get("tx_hash"),
                "status": result.get("status"),
                "message": f"Payment of {amount} {token} executed successfully",
            }

        except Exception as e:
            logger.error(f"x402 payment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Payment of {amount} {token} failed: {str(e)}",
            }


class DiscoverServicesInput(BaseModel):
    """Input schema for service discovery tool."""

    query: str = Field(..., description="Search query for services")
    category: str | None = Field(None, description="Service category to filter")
    max_results: int = Field(10, description="Maximum number of results to return")


class DiscoverServicesTool(BaseTool):
    """Tool for discovering MCP-compatible services."""

    name: str = "discover_services"
    description: str = (
        "Discover MCP-compatible services based on search criteria. "
        "Use this when you need to find services that support the x402 payment protocol."
    )
    args_schema = DiscoverServicesInput

    def __init__(self, service_registry: ServiceRegistryService):
        super().__init__()
        self.service_registry = service_registry

    async def _arun(
        self, query: str, category: str | None = None, max_results: int = 10
    ) -> dict[str, Any]:
        """
        Discover services based on search criteria.

        Args:
            query: Search query
            category: Optional service category
            max_results: Maximum number of results

        Returns:
            Dict containing discovered services
        """
        try:
            logger.info(f"Discovering services for query: {query}")

            # Discover services
            services = await self.service_registry.discover_services(
                query=query, category=category, limit=max_results
            )

            return {
                "success": True,
                "services": [
                    {
                        "id": str(service.id),
                        "name": service.name,
                        "description": service.description,
                        "endpoint": service.endpoint,
                        "pricing_model": service.pricing_model,
                        "price_amount": float(service.price_amount),
                        "price_token": service.price_token,
                        "mcp_compatible": service.mcp_compatible,
                        "reputation_score": float(service.reputation_score),
                    }
                    for service in services
                ],
                "total": len(services),
                "message": f"Found {len(services)} services matching '{query}'",
            }

        except Exception as e:
            logger.error(f"Service discovery failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Service discovery failed: {str(e)}",
            }


class CheckBalanceInput(BaseModel):
    """Input schema for balance check tool."""

    wallet_address: str | None = Field(None, description="Wallet address to check (optional)")


class CheckBalanceTool(BaseTool):
    """Tool for checking token balances."""

    name: str = "check_balance"
    description: str = (
        "Check the balance of tokens in the agent's wallet. "
        "Use this when you need to verify available funds before making payments."
    )
    args_schema = CheckBalanceInput

    def __init__(self, db: AsyncSession):
        super().__init__()
        self.db = db

    async def _arun(self, wallet_address: str | None = None) -> dict[str, Any]:
        """
        Check token balances.

        Args:
            wallet_address: Optional wallet address (uses agent wallet if not provided)

        Returns:
            Dict containing balance information
        """
        try:
            # TODO: Implement actual balance checking using wallet integration
            # For now, return mock data

            mock_balances = {
                "CRO": 1000.0,
                "USDC": 500.0,
                "USDT": 250.0,
                "BTC": 0.1,
                "ETH": 0.5,
            }

            return {
                "success": True,
                "balances": mock_balances,
                "wallet_address": wallet_address or "agent_wallet_address",
                "message": "Balance check completed successfully",
            }

        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Balance check failed: {str(e)}",
            }


class TransferTokensInput(BaseModel):
    """Input schema for token transfer tool."""

    recipient: str = Field(..., description="Recipient wallet address")
    amount: float = Field(..., description="Amount to transfer")
    token: str = Field(..., description="Token symbol")
    description: str | None = Field(None, description="Transfer description")


class TransferTokensTool(BaseTool):
    """Tool for transferring tokens between wallets."""

    name: str = "transfer_tokens"
    description: str = (
        "Transfer tokens from the agent's wallet to another wallet. "
        "Use this when you need to send payments or move funds."
    )
    args_schema = TransferTokensInput

    def __init__(self, db: AsyncSession):
        super().__init__()
        self.db = db

    async def _arun(
        self, recipient: str, amount: float, token: str, description: str | None = None
    ) -> dict[str, Any]:
        """
        Transfer tokens to another wallet.

        Args:
            recipient: Recipient wallet address
            amount: Amount to transfer
            token: Token symbol
            description: Optional transfer description

        Returns:
            Dict containing transfer result
        """
        try:
            # TODO: Implement actual token transfer using wallet integration
            # For now, return mock success

            return {
                "success": True,
                "tx_hash": f"mock_tx_hash_{hash(recipient + str(amount) + token)}",
                "recipient": recipient,
                "amount": amount,
                "token": token,
                "description": description or "Token transfer",
                "message": f"Successfully transferred {amount} {token} to {recipient}",
            }

        except Exception as e:
            logger.error(f"Token transfer failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Token transfer failed: {str(e)}",
            }


class GetApprovalInput(BaseModel):
    """Input schema for approval request tool."""

    action: str = Field(..., description="Action that requires approval")
    amount_usd: float | None = Field(None, description="Amount in USD")
    details: str | None = Field(None, description="Additional details")


class GetApprovalTool(BaseTool):
    """Tool for requesting human approval."""

    name: str = "get_approval"
    description: str = (
        "Request human approval for sensitive operations. "
        "Use this when transactions exceed budget limits or require human oversight."
    )
    args_schema = GetApprovalInput

    def __init__(self, db: AsyncSession):
        super().__init__()
        self.db = db

    async def _arun(
        self, action: str, amount_usd: float | None = None, details: str | None = None
    ) -> dict[str, Any]:
        """
        Request human approval for an action.

        Args:
            action: Action that requires approval
            amount_usd: Optional amount in USD
            details: Additional details

        Returns:
            Dict containing approval status
        """
        try:
            # TODO: Implement actual approval workflow
            # For now, return mock approval

            return {
                "success": True,
                "approved": True,
                "action": action,
                "amount_usd": amount_usd,
                "details": details,
                "message": f"Approval granted for: {action}",
            }

        except Exception as e:
            logger.error(f"Approval request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Approval request failed: {str(e)}",
            }


def create_agent_tools(
    payment_service: X402PaymentService,
    service_registry: ServiceRegistryService,
    db: AsyncSession,
) -> list[BaseTool]:
    """
    Create a list of tools for the agent.

    Args:
        payment_service: X402 payment service
        service_registry: Service registry service
        db: Database session

    Returns:
        List of LangChain tools
    """
    return [
        X402PaymentTool(payment_service),
        DiscoverServicesTool(service_registry),
        CheckBalanceTool(db),
        TransferTokensTool(db),
        GetApprovalTool(db),
    ]

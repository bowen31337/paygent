"""
Base agent tools for Paygent.

This module provides LangChain-compatible tools for the AI agent to use
when executing payment and DeFi operations.
"""

import logging
from typing import Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CheckBalanceInput(BaseModel):
    """Input schema for check_balance tool."""

    wallet_address: Optional[str] = Field(
        default=None,
        description="Wallet address to check balance for. If not provided, uses default agent wallet."
    )
    tokens: list[str] = Field(
        default_factory=lambda: ["CRO", "USDC"],
        description="List of token symbols to query balances for"
    )


class CheckBalanceTool(BaseTool):
    """Tool for checking wallet token balances."""

    name: str = "check_balance"
    description: str = """
    Check the balance of tokens in a wallet.

    Use this tool when users ask about:
    - Their wallet balance
    - How much of a token they have
    - Current token holdings

    Returns balances for major tokens (CRO, USDC, etc.).
    """
    args_schema: Type[BaseModel] = CheckBalanceInput

    def _run(
        self,
        wallet_address: Optional[str] = None,
        tokens: list[str] = ["CRO", "USDC"]
    ) -> dict:
        """
        Execute the balance check.

        Args:
            wallet_address: Wallet address to check
            tokens: List of token symbols to query

        Returns:
            Dict containing token balances
        """
        logger.info(f"Checking balance for wallet: {wallet_address or 'default agent wallet'}")

        # Mock balance data - in production, this would query the blockchain
        mock_balances = {
            "CRO": "1000.00",
            "USDC": "250.00",
            "USDT": "100.00",
            "ETH": "0.5",
            "WBTC": "0.02"
        }

        result = {
            "wallet_address": wallet_address or "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            "balances": {token: mock_balances.get(token, "0.00") for token in tokens},
            "timestamp": "2025-12-24T19:00:00Z"
        }

        logger.info(f"Balance check result: {result}")
        return result


class DiscoverServicesInput(BaseModel):
    """Input schema for discover_services tool."""

    category: Optional[str] = Field(
        default=None,
        description="Category of services to search for (e.g., 'market_data', 'defi', 'prediction')"
    )
    max_price_usd: Optional[float] = Field(
        default=None,
        description="Maximum price per call in USD"
    )
    mcp_compatible: bool = Field(
        default=True,
        description="Only return MCP-compatible services"
    )


class DiscoverServicesTool(BaseTool):
    """Tool for discovering available services."""

    name: str = "discover_services"
    description: str = """
    Discover available services that accept x402 payments.

    Use this tool when users want to:
    - Find services they can pay for
    - Explore available APIs and data sources
    - Check service pricing

    Returns a list of services with pricing information.
    """
    args_schema: Type[DiscoverServicesInput] = DiscoverServicesInput

    def _run(
        self,
        category: Optional[str] = None,
        max_price_usd: Optional[float] = None,
        mcp_compatible: bool = True
    ) -> dict:
        """
        Discover available services.

        Args:
            category: Service category filter
            max_price_usd: Maximum price filter
            mcp_compatible: Only MCP-compatible services

        Returns:
            Dict containing list of discovered services
        """
        logger.info(f"Discovering services: category={category}, max_price={max_price_usd}")

        # Mock service catalog - in production, this would query the service registry database
        mock_services = [
            {
                "id": "market-data-btc",
                "name": "BTC Market Data Feed",
                "description": "Real-time Bitcoin price and trading data",
                "category": "market_data",
                "pricing_model": "pay-per-call",
                "price_amount": "0.01",
                "price_token": "USDC",
                "mcp_compatible": True,
                "endpoint": "https://api.example.com/btc/price"
            },
            {
                "id": "defi-yield-optimizer",
                "name": "DeFi Yield Optimizer",
                "description": "AI-powered yield optimization across DeFi protocols",
                "category": "defi",
                "pricing_model": "subscription",
                "price_amount": "10.00",
                "price_token": "USDC",
                "mcp_compatible": True,
                "endpoint": "https://api.example.com/defi/optimize"
            },
            {
                "id": "prediction-market-analyzer",
                "name": "Prediction Market Analyzer",
                "description": "Advanced analytics for prediction markets",
                "category": "prediction",
                "pricing_model": "pay-per-call",
                "price_amount": "0.05",
                "price_token": "USDC",
                "mcp_compatible": True,
                "endpoint": "https://api.example.com/predictions/analyze"
            }
        ]

        # Apply filters
        filtered_services = mock_services
        if category:
            filtered_services = [s for s in filtered_services if s["category"] == category]
        if max_price_usd:
            filtered_services = [
                s for s in filtered_services
                if float(s["price_amount"]) <= max_price_usd
            ]
        if mcp_compatible:
            filtered_services = [s for s in filtered_services if s["mcp_compatible"]]

        result = {
            "services": filtered_services,
            "total": len(filtered_services),
            "timestamp": "2025-12-24T19:00:00Z"
        }

        logger.info(f"Discovered {len(filtered_services)} services")
        return result


class X402PaymentInput(BaseModel):
    """Input schema for x402_payment tool."""

    service_url: str = Field(
        ...,
        description="URL of the service to pay"
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Amount to pay"
    )
    token: str = Field(
        default="USDC",
        description="Token to pay with (default: USDC)"
    )


class X402PaymentTool(BaseTool):
    """Tool for executing x402 payments."""

    name: str = "x402_payment"
    description: str = """
    Execute an x402 payment to access a paid service.

    Use this tool when:
    - A service returns HTTP 402 Payment Required
    - Users explicitly want to pay for a service
    - Service access requires payment

    The tool handles:
    - HTTP 402 response detection
    - EIP-712 signature generation
    - Payment execution via x402 Facilitator
    - Retry logic with backoff

    Returns payment confirmation with transaction hash.
    """
    args_schema: Type[BaseModel] = X402PaymentInput

    def _run(
        self,
        service_url: str,
        amount: float,
        token: str = "USDC"
    ) -> dict:
        """
        Execute x402 payment.

        Args:
            service_url: URL of service to pay
            amount: Amount to pay
            token: Token to pay with

        Returns:
            Dict containing payment confirmation
        """
        logger.info(f"Executing x402 payment: {amount} {token} to {service_url}")

        # Mock payment execution - in production, this would:
        # 1. Detect HTTP 402 response
        # 2. Parse X-Payment header
        # 3. Generate EIP-712 signature
        # 4. Submit payment to x402 Facilitator
        # 5. Retry the original request with payment proof

        mock_tx_hash = "0x" + "a" * 64  # Mock transaction hash

        result = {
            "status": "confirmed",
            "service_url": service_url,
            "amount": str(amount),
            "token": token,
            "tx_hash": mock_tx_hash,
            "settlement_time_ms": 180,
            "timestamp": "2025-12-24T19:00:00Z"
        }

        logger.info(f"Payment executed successfully: {result}")
        return result


class SwapTokensInput(BaseModel):
    """Input schema for swap_tokens tool."""

    from_token: str = Field(
        ...,
        description="Token to swap from (e.g., 'CRO', 'USDC')"
    )
    to_token: str = Field(
        ...,
        description="Token to swap to (e.g., 'USDC', 'CRO')"
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Amount to swap"
    )
    slippage_tolerance_percent: float = Field(
        default=1.0,
        ge=0,
        le=10,
        description="Maximum acceptable slippage percentage"
    )


class SwapTokensTool(BaseTool):
    """Tool for swapping tokens on VVS Finance."""

    name: str = "swap_tokens"
    description: str = """
    Swap tokens on VVS Finance DEX.

    Use this tool when users want to:
    - Exchange one token for another
    - Trade on VVS Finance
    - Get best swap price

    The tool handles:
    - Price quotes from VVS
    - Slippage protection
    - Transaction execution
    - Balance updates

    Returns swap confirmation with received amount.
    """
    args_schema: Type[BaseModel] = SwapTokensInput

    def _run(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance_percent: float = 1.0
    ) -> dict:
        """
        Execute token swap.

        Args:
            from_token: Source token
            to_token: Destination token
            amount: Amount to swap
            slippage_tolerance_percent: Max slippage tolerance

        Returns:
            Dict containing swap confirmation
        """
        logger.info(f"Swapping {amount} {from_token} to {to_token}")

        # Mock swap execution - in production, this would:
        # 1. Get price quote from VVS Finance
        # 2. Calculate minimum output with slippage
        # 3. Execute swap transaction
        # 4. Wait for confirmation

        # Simple mock price calculation
        if from_token == "CRO" and to_token == "USDC":
            exchange_rate = 0.075
        elif from_token == "USDC" and to_token == "CRO":
            exchange_rate = 13.33
        else:
            exchange_rate = 1.0

        received_amount = amount * exchange_rate * (1 - slippage_tolerance_percent / 100)

        mock_tx_hash = "0x" + "b" * 64  # Mock transaction hash

        result = {
            "status": "completed",
            "from_token": from_token,
            "to_token": to_token,
            "amount_in": str(amount),
            "amount_out": f"{received_amount:.4f}",
            "exchange_rate": str(exchange_rate),
            "slippage_percent": str(slippage_tolerance_percent),
            "tx_hash": mock_tx_hash,
            "dex": "VVS Finance",
            "timestamp": "2025-12-24T19:00:00Z"
        }

        logger.info(f"Swap completed: {result}")
        return result


def get_all_tools() -> list[BaseTool]:
    """Get all available agent tools."""
    return [
        CheckBalanceTool(),
        DiscoverServicesTool(),
        X402PaymentTool(),
        SwapTokensTool(),
    ]

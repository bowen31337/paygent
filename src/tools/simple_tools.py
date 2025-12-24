"""
Simple agent tools that don't require LangChain.

These are basic tool implementations for the agent to use.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SimpleTool:
    """Base class for simple tools."""

    name: str = "base_tool"
    description: str = "Base tool description"

    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool."""
        raise NotImplementedError


class CheckBalanceTool(SimpleTool):
    """Tool for checking wallet token balances."""

    name = "check_balance"
    description = "Check the balance of tokens in a wallet"

    def run(
        self,
        wallet_address: Optional[str] = None,
        tokens: list = None
    ) -> Dict[str, Any]:
        """Execute balance check."""
        logger.info(f"Checking balance for: {wallet_address or 'default wallet'}")

        mock_balances = {
            "CRO": "1000.00",
            "USDC": "250.00",
            "USDT": "100.00",
        }

        tokens = tokens or ["CRO", "USDC"]

        return {
            "wallet_address": wallet_address or "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            "balances": {token: mock_balances.get(token, "0.00") for token in tokens},
            "timestamp": "2025-12-24T19:00:00Z"
        }


class X402PaymentTool(SimpleTool):
    """Tool for executing x402 payments."""

    name = "x402_payment"
    description = "Execute an x402 payment to access a paid service"

    def run(
        self,
        service_url: str,
        amount: float,
        token: str = "USDC"
    ) -> Dict[str, Any]:
        """Execute x402 payment."""
        logger.info(f"Executing x402 payment: {amount} {token} to {service_url}")

        mock_tx_hash = "0x" + "a" * 64

        return {
            "status": "confirmed",
            "service_url": service_url,
            "amount": str(amount),
            "token": token,
            "tx_hash": mock_tx_hash,
            "settlement_time_ms": 180,
            "timestamp": "2025-12-24T19:00:00Z"
        }


class SwapTokensTool(SimpleTool):
    """Tool for swapping tokens."""

    name = "swap_tokens"
    description = "Swap tokens on VVS Finance DEX"

    def run(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance_percent: float = 1.0
    ) -> Dict[str, Any]:
        """Execute token swap."""
        logger.info(f"Swapping {amount} {from_token} to {to_token}")

        if from_token == "CRO" and to_token == "USDC":
            exchange_rate = 0.075
        elif from_token == "USDC" and to_token == "CRO":
            exchange_rate = 13.33
        else:
            exchange_rate = 1.0

        received_amount = amount * exchange_rate * (1 - slippage_tolerance_percent / 100)
        mock_tx_hash = "0x" + "b" * 64

        return {
            "status": "completed",
            "from_token": from_token,
            "to_token": to_token,
            "amount_in": str(amount),
            "amount_out": f"{received_amount:.4f}",
            "exchange_rate": str(exchange_rate),
            "tx_hash": mock_tx_hash,
            "dex": "VVS Finance",
            "timestamp": "2025-12-24T19:00:00Z"
        }


class DiscoverServicesTool(SimpleTool):
    """Tool for discovering services."""

    name = "discover_services"
    description = "Discover available services that accept x402 payments"

    def run(
        self,
        category: Optional[str] = None,
        max_price_usd: Optional[float] = None,
        mcp_compatible: bool = True
    ) -> Dict[str, Any]:
        """Discover services."""
        logger.info(f"Discovering services: category={category}")

        mock_services = [
            {
                "id": "market-data-btc",
                "name": "Market Data API (Updated)",
                "description": "Real-time cryptocurrency market data from Crypto.com MCP Server",
                "endpoint": "https://api.marketdata.example.com",
                "category": "market_data",
                "price_amount": "0.15",
                "price_token": "USDC",
                "mcp_compatible": True,
            },
            {
                "id": "defi-yield-optimizer",
                "name": "DeFi Yield Optimizer",
                "category": "defi",
                "price_amount": "10.00",
                "price_token": "USDC",
            }
        ]

        if category:
            mock_services = [s for s in mock_services if s["category"] == category]

        return {
            "services": mock_services,
            "total": len(mock_services),
            "timestamp": "2025-12-24T19:00:00Z"
        }


def get_all_tools() -> Dict[str, SimpleTool]:
    """Get all available tools as a dict."""
    return {
        "check_balance": CheckBalanceTool(),
        "x402_payment": X402PaymentTool(),
        "swap_tokens": SwapTokensTool(),
        "discover_services": DiscoverServicesTool(),
    }

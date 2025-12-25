"""
Simple agent tools that don't require LangChain.

These are basic tool implementations for the agent to use.
"""

import logging
from typing import Any

from src.connectors.vvs import VVSFinanceConnector
from src.core.security import get_tool_allowlist

logger = logging.getLogger(__name__)


class SimpleTool:
    """Base class for simple tools."""

    name: str = "base_tool"
    description: str = "Base tool description"

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the tool."""
        raise NotImplementedError

    def validate_allowlist(self, **kwargs: Any) -> None:
        """
        Validate that this tool is allowed by the tool allowlist.

        Raises:
            ToolAllowlistError: If the tool is not in the allowlist
        """
        allowlist = get_tool_allowlist()
        allowlist.validate_tool_call(self.name, kwargs)


class CheckBalanceTool(SimpleTool):
    """Tool for checking wallet token balances."""

    name = "check_balance"
    description = "Check the balance of tokens in a wallet"

    def run(  # type: ignore[override]
        self,
        wallet_address: str | None = None,
        tokens: list[str] | None = None
    ) -> dict[str, Any]:
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

    def run(  # type: ignore[override]
        self,
        service_url: str,
        amount: float,
        token: str = "USDC"
    ) -> dict[str, Any]:
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
    """Tool for swapping tokens on VVS Finance."""

    name = "swap_tokens"
    description = "Swap tokens on VVS Finance DEX with slippage protection"

    def run(  # type: ignore[override]
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance_percent: float = 1.0,
        deadline: int | None = None
    ) -> dict[str, Any]:
        """Execute token swap using VVS Finance connector."""
        logger.info(f"Swapping {amount} {from_token} to {to_token}")

        vvs = VVSFinanceConnector()
        result = vvs.swap(
            from_token=from_token,
            to_token=to_token,
            amount=amount,
            slippage_tolerance=slippage_tolerance_percent,
            deadline=deadline
        )

        return result


class VVSQuoteTool(SimpleTool):
    """Tool for getting price quotes from VVS Finance."""

    name = "vvs_quote"
    description = "Get price quote for token swap on VVS Finance"

    def run(  # type: ignore[override]
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance_percent: float = 1.0
    ) -> dict[str, Any]:
        """Get swap quote."""
        logger.info(f"Getting quote for {amount} {from_token} -> {to_token}")

        vvs = VVSFinanceConnector()
        quote = vvs.get_quote(
            from_token=from_token,
            to_token=to_token,
            amount=amount,
            slippage_tolerance=slippage_tolerance_percent
        )

        return quote


class VVSLiquidityTool(SimpleTool):
    """Tool for managing VVS Finance liquidity positions."""

    name = "vvs_liquidity"
    description = "Add or remove liquidity from VVS Finance pools"

    def run(  # type: ignore[override]
        self,
        action: str,  # "add" or "remove"
        token_a: str,
        token_b: str,
        amount_a: float | None = None,
        amount_b: float | None = None,
        lp_amount: float | None = None,
        slippage_tolerance_percent: float = 1.0
    ) -> dict[str, Any]:
        """Manage liquidity position."""
        vvs = VVSFinanceConnector()

        if action == "add":
            if amount_a is None or amount_b is None:
                raise ValueError("amount_a and amount_b required for add action")
            logger.info(f"Adding liquidity: {amount_a} {token_a} + {amount_b} {token_b}")
            return vvs.add_liquidity(
                token_a=token_a,
                token_b=token_b,
                amount_a=amount_a,
                amount_b=amount_b,
                slippage_tolerance=slippage_tolerance_percent
            )
        elif action == "remove":
            if lp_amount is None:
                raise ValueError("lp_amount required for remove action")
            logger.info(f"Removing liquidity: {lp_amount} LP tokens")
            return vvs.remove_liquidity(
                token_a=token_a,
                token_b=token_b,
                lp_amount=lp_amount
            )
        else:
            raise ValueError(f"Unknown action: {action}. Use 'add' or 'remove'")


class VVSFarmingTool(SimpleTool):
    """Tool for VVS Finance yield farming."""

    name = "vvs_farm"
    description = "Stake LP tokens in VVS Finance yield farms"

    def run(  # type: ignore[override]
        self,
        token_a: str,
        token_b: str,
        amount: float,
        farm_id: str | None = None
    ) -> dict[str, Any]:
        """Stake LP tokens in farm."""
        logger.info(f"Farming: staking {amount} {token_a}-{token_b} LP tokens")

        vvs = VVSFinanceConnector()
        return vvs.stake_lp_tokens(
            token_a=token_a,
            token_b=token_b,
            amount=amount,
            farm_id=farm_id
        )


class DiscoverServicesTool(SimpleTool):
    """Tool for discovering services."""

    name = "discover_services"
    description = "Discover available services that accept x402 payments"

    def run(  # type: ignore[override]
        self,
        category: str | None = None,
        max_price_usd: float | None = None,
        mcp_compatible: bool = True  # noqa: ARG002
    ) -> dict[str, Any]:
        """Discover services."""
        logger.info(f"Discovering services: category={category}")

        mock_services: list[dict[str, Any]] = [
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


def get_all_tools() -> dict[str, SimpleTool]:
    """Get all available tools as a dict."""
    return {
        "check_balance": CheckBalanceTool(),
        "x402_payment": X402PaymentTool(),
        "swap_tokens": SwapTokensTool(),
        "vvs_quote": VVSQuoteTool(),
        "vvs_liquidity": VVSLiquidityTool(),
        "vvs_farm": VVSFarmingTool(),
        "discover_services": DiscoverServicesTool(),
    }

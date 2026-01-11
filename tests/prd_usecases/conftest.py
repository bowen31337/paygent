"""
Shared fixtures for PRD Use Case tests.

These fixtures support testing the 4 use cases defined in Paygent PRD Section 5:
- 5.1 Automated Trading Agent
- 5.2 AI-Powered API Marketplace
- 5.3 Portfolio Management Agent
- 5.4 Research & Intelligence Agent
"""

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# =============================================================================
# Mock Data Classes
# =============================================================================


@dataclass
class MockPool:
    """Mock liquidity pool with configurable reserves."""

    reserve0: float  # Token A reserve
    reserve1: float  # Token B reserve
    token0: str = "CRO"
    token1: str = "USDC"

    def get_price(self) -> float:
        """Get price of token0 in terms of token1."""
        return self.reserve1 / self.reserve0

    def get_amount_out(self, amount_in: float, token_in: str) -> float:
        """Calculate output amount for a swap (with 0.3% fee)."""
        fee = 0.003
        if token_in == self.token0:
            amount_in_with_fee = amount_in * (1 - fee)
            return (amount_in_with_fee * self.reserve1) / (
                self.reserve0 + amount_in_with_fee
            )
        else:
            amount_in_with_fee = amount_in * (1 - fee)
            return (amount_in_with_fee * self.reserve0) / (
                self.reserve1 + amount_in_with_fee
            )


@dataclass
class MockPriceFeed:
    """Mock price feed with controllable spreads for arbitrage testing."""

    cro_usdc_bid: float = 0.074
    cro_usdc_ask: float = 0.076

    @property
    def spread_percent(self) -> float:
        """Calculate spread percentage."""
        return (self.cro_usdc_ask - self.cro_usdc_bid) / self.cro_usdc_bid * 100


@dataclass
class MockPosition:
    """Mock trading position for portfolio tests."""

    token: str
    amount: float
    value_usd: float
    entry_price: float = 0.0


# =============================================================================
# Trading Agent Fixtures (Use Case 5.1)
# =============================================================================


@pytest.fixture
def mock_price_feed():
    """Mock Crypto.com MCP price feed with controllable spreads."""
    return MockPriceFeed(
        cro_usdc_bid=0.074,
        cro_usdc_ask=0.076,  # 2.7% spread for testing
    )


@pytest.fixture
def mock_price_feed_arbitrage():
    """Mock price feed with detectable arbitrage (>0.5% spread)."""
    return MockPriceFeed(
        cro_usdc_bid=0.073,
        cro_usdc_ask=0.078,  # 6.8% spread - clear arbitrage opportunity
    )


@pytest.fixture
def mock_price_feed_no_arbitrage():
    """Mock price feed with no arbitrage (<0.5% spread)."""
    return MockPriceFeed(
        cro_usdc_bid=0.0745,
        cro_usdc_ask=0.0748,  # 0.4% spread - below threshold
    )


@pytest.fixture
def mock_vvs_pools():
    """Mock VVS liquidity pools with configurable prices."""
    return {
        "CRO-USDC": MockPool(reserve0=1000000, reserve1=75000, token0="CRO", token1="USDC"),
        "CRO-USDT": MockPool(reserve0=1000000, reserve1=74000, token0="CRO", token1="USDT"),
        "USDC-USDT": MockPool(reserve0=100000, reserve1=100000, token0="USDC", token1="USDT"),
    }


@pytest.fixture
def trading_budget_config():
    """Budget configuration for trading agent."""
    return {
        "daily_limit_usd": 1000.0,
        "max_single_trade_usd": 100.0,
        "min_profit_threshold": 0.005,  # 0.5%
        "slippage_tolerance": 0.01,  # 1%
    }


# =============================================================================
# API Marketplace Fixtures (Use Case 5.2)
# =============================================================================


@pytest.fixture
def sample_ml_service():
    """Sample ML inference service for marketplace tests."""
    return {
        "id": "ml-image-classify-001",
        "name": "Image Classification API",
        "description": "Classify images using advanced ML models",
        "endpoint": "https://ml-api.example.com/v1/classify",
        "pricing_model": "pay-per-call",
        "price_amount": 0.001,
        "price_token": "USDC",
        "mcp_compatible": True,
        "reputation_score": 4.8,
        "total_calls": 125000,
    }


@pytest.fixture
def sample_subscription_service():
    """Sample subscription-based service."""
    return {
        "id": "analytics-premium-001",
        "name": "Premium Analytics API",
        "description": "Advanced analytics and insights",
        "endpoint": "https://analytics.example.com/v1",
        "pricing_model": "subscription",
        "price_amount": 9.99,
        "price_token": "USDC",
        "billing_period": "monthly",
        "mcp_compatible": True,
    }


@pytest.fixture
def mock_x402_facilitator():
    """Mock x402 facilitator for payment settlement."""
    mock = AsyncMock()
    mock.settle_payment.return_value = {
        "success": True,
        "tx_hash": "0x" + "a" * 64,
        "settlement_time_ms": 180,
        "block_number": 12345678,
    }
    mock.verify_payment.return_value = {"valid": True, "reason": None}
    return mock


@pytest.fixture
def mock_http_402_response():
    """Mock HTTP 402 Payment Required response."""
    return {
        "status_code": 402,
        "headers": {
            "Payment-Required": "x402; amount=0.001; token=USDC; wallet=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "Content-Type": "application/json",
        },
        "body": {"error": "Payment required", "message": "Please pay 0.001 USDC to access this resource"},
    }


# =============================================================================
# Portfolio Management Fixtures (Use Case 5.3)
# =============================================================================


@pytest.fixture
def portfolio_config():
    """Portfolio configuration for management tests."""
    return {
        "target_allocation": {
            "CRO": 0.30,
            "USDC": 0.40,
            "BTC": 0.30,
        },
        "rebalance_threshold": 0.05,  # 5% deviation triggers rebalance
        "max_daily_drawdown": 0.05,  # 5% max drawdown
        "hitl_threshold_usd": 10000.0,
    }


@pytest.fixture
def mock_portfolio_balanced():
    """Mock portfolio in balanced state."""
    return {
        "positions": [
            MockPosition(token="CRO", amount=4000, value_usd=300, entry_price=0.075),
            MockPosition(token="USDC", amount=400, value_usd=400, entry_price=1.0),
            MockPosition(token="BTC", amount=0.007, value_usd=300, entry_price=42857),
        ],
        "total_value_usd": 1000.0,
        "daily_pnl_percent": 0.0,
    }


@pytest.fixture
def mock_portfolio_unbalanced():
    """Mock portfolio needing rebalance (CRO overweight)."""
    return {
        "positions": [
            MockPosition(token="CRO", amount=6000, value_usd=450, entry_price=0.075),
            MockPosition(token="USDC", amount=300, value_usd=300, entry_price=1.0),
            MockPosition(token="BTC", amount=0.006, value_usd=250, entry_price=41667),
        ],
        "total_value_usd": 1000.0,
        "daily_pnl_percent": -1.5,
        "allocation": {"CRO": 0.45, "USDC": 0.30, "BTC": 0.25},
    }


@pytest.fixture
def mock_approval_service():
    """Mock approval service for HITL tests."""
    mock = AsyncMock()
    mock.request_approval.return_value = {
        "approval_id": "apr-123456",
        "status": "pending",
        "tool_name": "vvs_swap",
        "args": {"amount": 15000, "from_token": "CRO", "to_token": "USDC"},
        "created_at": "2024-01-01T00:00:00Z",
    }
    mock.get_approval_status.return_value = {"status": "pending", "decision": None}
    mock.approve.return_value = {"status": "approved", "decision": "approve"}
    mock.reject.return_value = {"status": "rejected", "decision": "reject"}
    return mock


# =============================================================================
# Research Agent Fixtures (Use Case 5.4)
# =============================================================================


@pytest.fixture
def mock_crypto_com_mcp_data():
    """Mock Crypto.com MCP ecosystem data."""
    return {
        "total_tvl": 1500000000,
        "daily_volume": 250000000,
        "top_protocols": [
            {"name": "VVS Finance", "tvl": 500000000, "daily_volume": 80000000},
            {"name": "Moonlander", "tvl": 100000000, "daily_volume": 30000000},
            {"name": "Delphi", "tvl": 50000000, "daily_volume": 5000000},
        ],
        "market_summary": {
            "cro_price": 0.075,
            "cro_24h_change": 2.5,
            "total_market_cap": 3000000000,
        },
    }


@pytest.fixture
def mock_premium_analytics():
    """Mock premium analytics data (requires x402 payment)."""
    return {
        "defi_health_score": 85,
        "risk_metrics": {
            "systemic_risk": "low",
            "liquidity_risk": "medium",
            "smart_contract_risk": "low",
        },
        "growth_projections": {
            "30d": 0.12,
            "90d": 0.35,
            "365d": 1.2,
        },
        "opportunities": [
            {"protocol": "VVS Finance", "pool": "CRO-USDC", "apy": 45.2},
            {"protocol": "Moonlander", "market": "BTC-USDC", "funding_rate": 0.01},
        ],
    }


@pytest.fixture
def expected_research_report_structure():
    """Expected structure for research report."""
    return {
        "title": str,
        "summary": str,
        "sections": list,
        "data_sources": list,
        "generated_at": str,
        "cost_usd": float,
    }


@pytest.fixture
def mock_research_plan():
    """Mock research plan (write_todos output)."""
    return [
        {"step": 1, "action": "Query Crypto.com MCP for ecosystem data", "status": "pending"},
        {"step": 2, "action": "Access premium analytics API via x402", "status": "pending"},
        {"step": 3, "action": "Analyze VVS Finance on-chain data", "status": "pending"},
        {"step": 4, "action": "Analyze Moonlander trading data", "status": "pending"},
        {"step": 5, "action": "Analyze Delphi prediction markets", "status": "pending"},
        {"step": 6, "action": "Compile findings into report", "status": "pending"},
        {"step": 7, "action": "Save report to filesystem", "status": "pending"},
    ]


# =============================================================================
# Testnet Configuration Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def testnet_config():
    """Load testnet configuration for integration tests."""
    deployment_path = Path(__file__).parent.parent.parent / "contracts" / "deployments" / "vvs-testnet.json"
    if deployment_path.exists():
        with open(deployment_path) as f:
            return json.load(f)
    return None


@pytest.fixture
def skip_if_no_testnet(testnet_config):
    """Skip test if testnet deployment not available."""
    if testnet_config is None:
        pytest.skip("Testnet deployment not available")


@pytest.fixture
def testnet_contracts(testnet_config):
    """Get testnet contract addresses."""
    if testnet_config is None:
        return None
    return testnet_config.get("contracts", {})


# =============================================================================
# Mock Connector Fixtures
# =============================================================================


@pytest.fixture
def mock_vvs_connector():
    """Mock VVS Finance connector."""
    mock = MagicMock()
    mock.get_quote.return_value = {
        "from_token": "CRO",
        "to_token": "USDC",
        "amount_in": "100",
        "expected_amount_out": "7.5",
        "min_amount_out": "7.425",
        "exchange_rate": "0.075",
        "price_impact": "0.1",
        "slippage_tolerance": 1.0,
        "fee": "0.003",
        "source": "mock",
    }
    mock.swap.return_value = {
        "success": True,
        "tx_hash": "0x" + "b" * 64,
        "amount_in": "100",
        "amount_out": "7.48",
        "from_token": "CRO",
        "to_token": "USDC",
    }
    return mock


@pytest.fixture
def mock_moonlander_connector():
    """Mock Moonlander connector."""
    mock = MagicMock()
    mock.get_funding_rate.return_value = {"market": "BTC-USDC", "rate": 0.0001, "next_funding": 3600}
    mock.open_position.return_value = {
        "success": True,
        "position_id": "pos-123",
        "side": "long",
        "size": 100,
        "entry_price": 42000,
        "leverage": 5,
    }
    mock.close_position.return_value = {
        "success": True,
        "position_id": "pos-123",
        "pnl": 25.50,
        "exit_price": 42500,
    }
    return mock


@pytest.fixture
def mock_delphi_connector():
    """Mock Delphi connector."""
    mock = MagicMock()
    mock.get_markets.return_value = [
        {
            "id": "mkt-001",
            "question": "Will Bitcoin exceed $50,000?",
            "category": "crypto",
            "outcomes": [{"name": "Yes", "odds": 0.65}, {"name": "No", "odds": 0.35}],
        },
        {
            "id": "mkt-002",
            "question": "Cronos TVL > $1B?",
            "category": "defi",
            "outcomes": [{"name": "Yes", "odds": 0.45}, {"name": "No", "odds": 0.55}],
        },
    ]
    mock.place_bet.return_value = {
        "success": True,
        "bet_id": "bet-456",
        "market_id": "mkt-001",
        "outcome": "Yes",
        "amount": 10,
        "potential_payout": 15.38,
    }
    return mock


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: Integration tests with external services")
    config.addinivalue_line("markers", "testnet: Tests requiring Cronos testnet")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "hitl: Tests involving HITL approval")

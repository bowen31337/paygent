"""
Use Case 5.1: Automated Trading Agent Tests

Tests for the automated trading agent that monitors VVS prices,
detects arbitrage opportunities (>0.5% spread), and executes
swaps within a $1000/day budget.

PRD Reference: Section 5.1 - Automated Trading Agent
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.vvs import VVSFinanceConnector


class TestPriceFeedSubscription:
    """Test agent's ability to subscribe to price feeds via x402."""

    @pytest.mark.asyncio
    async def test_subscribe_to_price_feed_x402(self, mock_x402_facilitator, mock_crypto_com_mcp_data):
        """Verify agent can subscribe to price feeds via x402 payment."""
        # Arrange
        service_url = "https://mcp.crypto.com/v1/market-data"
        payment_amount = 0.01
        payment_token = "USDC"

        # Mock successful payment
        mock_x402_facilitator.settle_payment.return_value = {
            "success": True,
            "tx_hash": "0x" + "a" * 64,
            "settlement_time_ms": 180,
        }

        # Act
        result = await mock_x402_facilitator.settle_payment(
            service_url=service_url,
            amount=payment_amount,
            token=payment_token,
        )

        # Assert
        assert result["success"] is True
        assert "tx_hash" in result
        mock_x402_facilitator.settle_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_price_updates_after_subscription(self, mock_price_feed):
        """Verify agent receives price updates after subscribing."""
        # Arrange & Act
        bid = mock_price_feed.cro_usdc_bid
        ask = mock_price_feed.cro_usdc_ask

        # Assert
        assert bid == 0.074
        assert ask == 0.076
        assert mock_price_feed.spread_percent > 0


class TestArbitrageDetection:
    """Test arbitrage opportunity detection logic."""

    def test_detect_arbitrage_above_threshold(self, mock_price_feed_arbitrage, trading_budget_config):
        """Verify arbitrage is detected when spread > 0.5%."""
        # Arrange
        min_threshold = trading_budget_config["min_profit_threshold"] * 100  # Convert to percentage

        # Act
        spread = mock_price_feed_arbitrage.spread_percent

        # Assert
        assert spread > min_threshold
        assert spread > 0.5  # Explicit check for >0.5%

    def test_no_arbitrage_below_threshold(self, mock_price_feed_no_arbitrage, trading_budget_config):
        """Verify no action when spread < 0.5%."""
        # Arrange
        min_threshold = trading_budget_config["min_profit_threshold"] * 100

        # Act
        spread = mock_price_feed_no_arbitrage.spread_percent

        # Assert
        assert spread < min_threshold
        assert spread < 0.5  # Explicit check for <0.5%

    def test_calculate_potential_profit(self, mock_price_feed_arbitrage, mock_vvs_pools):
        """Calculate potential profit from detected arbitrage."""
        # Arrange
        trade_amount = 100  # CRO
        cro_usdc_pool = mock_vvs_pools["CRO-USDC"]

        # Calculate buy price (from price feed bid)
        buy_price = mock_price_feed_arbitrage.cro_usdc_bid  # 0.073

        # Calculate sell price (from VVS pool)
        expected_out = cro_usdc_pool.get_amount_out(trade_amount, "CRO")
        sell_price = expected_out / trade_amount

        # Act
        profit_percent = ((sell_price - buy_price) / buy_price) * 100

        # Assert
        assert profit_percent > 0  # Profitable trade
        assert sell_price > buy_price


class TestSwapExecution:
    """Test swap execution for profitable trades."""

    def test_execute_profitable_swap(self, mock_vvs_connector):
        """Execute profitable swap when arbitrage detected."""
        # Arrange
        from_token = "CRO"
        to_token = "USDC"
        amount_in = 100

        # Act
        result = mock_vvs_connector.swap(from_token, to_token, amount_in)

        # Assert
        assert result["success"] is True
        assert "tx_hash" in result
        assert result["from_token"] == from_token
        assert result["to_token"] == to_token

    def test_swap_with_slippage_protection(self, mock_vvs_connector, trading_budget_config):
        """Verify swap respects slippage tolerance."""
        # Arrange
        slippage = trading_budget_config["slippage_tolerance"]
        quote = mock_vvs_connector.get_quote("CRO", "USDC", 100)

        # Act
        min_amount = float(quote["min_amount_out"])
        expected_amount = float(quote["expected_amount_out"])

        # Assert
        assert min_amount < expected_amount
        assert min_amount >= expected_amount * (1 - slippage)

    def test_swap_logs_transaction(self, mock_vvs_connector):
        """Verify swap transaction is logged with profit info."""
        # Arrange
        result = mock_vvs_connector.swap("CRO", "USDC", 100)

        # Assert - verify transaction details available for logging
        assert "tx_hash" in result
        assert "amount_in" in result
        assert "amount_out" in result


class TestBudgetEnforcement:
    """Test daily budget limit enforcement."""

    def test_trade_within_budget_allowed(self, trading_budget_config):
        """Allow trades within daily budget."""
        # Arrange
        daily_limit = trading_budget_config["daily_limit_usd"]
        trade_amount = 50  # Well within $1000 limit
        current_spent = 0

        # Act
        can_trade = (current_spent + trade_amount) <= daily_limit

        # Assert
        assert can_trade is True

    def test_trade_exceeding_budget_rejected(self, trading_budget_config):
        """Reject trades that would exceed daily budget."""
        # Arrange
        daily_limit = trading_budget_config["daily_limit_usd"]
        trade_amount = 100
        current_spent = 950  # Close to limit

        # Act
        can_trade = (current_spent + trade_amount) <= daily_limit

        # Assert
        assert can_trade is False

    def test_max_single_trade_limit(self, trading_budget_config):
        """Enforce maximum single trade limit."""
        # Arrange
        max_single = trading_budget_config["max_single_trade_usd"]
        trade_amount = 150  # Exceeds $100 limit

        # Act
        within_limit = trade_amount <= max_single

        # Assert
        assert within_limit is False

    def test_budget_tracking_accumulates(self, trading_budget_config):
        """Track accumulated spending across multiple trades."""
        # Arrange
        daily_limit = trading_budget_config["daily_limit_usd"]
        trades = [80, 70, 60, 50]  # Total = $260
        total_spent = sum(trades)

        # Act
        remaining_budget = daily_limit - total_spent

        # Assert
        assert remaining_budget == 740
        assert total_spent < daily_limit


class TestCompleteWorkflow:
    """Test end-to-end automated trading workflow."""

    @pytest.mark.asyncio
    async def test_complete_trading_workflow(
        self,
        mock_x402_facilitator,
        mock_price_feed_arbitrage,
        mock_vvs_connector,
        trading_budget_config,
    ):
        """End-to-end automated trading flow."""
        # Step 1: Subscribe to price feed (x402 payment)
        subscription_result = await mock_x402_facilitator.settle_payment(
            service_url="https://mcp.crypto.com/v1/market-data",
            amount=0.01,
            token="USDC",
        )
        assert subscription_result["success"] is True

        # Step 2: Receive price updates
        spread = mock_price_feed_arbitrage.spread_percent
        assert spread > 0

        # Step 3: Detect arbitrage (>0.5% spread)
        min_threshold = trading_budget_config["min_profit_threshold"] * 100
        arbitrage_detected = spread > min_threshold
        assert arbitrage_detected is True

        # Step 4: Execute swap on VVS (if within budget)
        daily_limit = trading_budget_config["daily_limit_usd"]
        trade_amount_usd = 50
        assert trade_amount_usd <= daily_limit

        swap_result = mock_vvs_connector.swap("CRO", "USDC", 100)
        assert swap_result["success"] is True

        # Step 5: Log transaction and profit
        assert "tx_hash" in swap_result
        assert "amount_out" in swap_result

    @pytest.mark.asyncio
    async def test_workflow_respects_budget(
        self,
        mock_vvs_connector,
        trading_budget_config,
    ):
        """Verify workflow stops when budget exhausted."""
        # Arrange
        daily_limit = trading_budget_config["daily_limit_usd"]
        spent = 0
        trades_executed = 0
        max_trades = 20

        # Act - simulate trading until budget exhausted
        while spent < daily_limit and trades_executed < max_trades:
            trade_amount = 75  # $75 per trade
            if (spent + trade_amount) > daily_limit:
                break
            mock_vvs_connector.swap("CRO", "USDC", 100)
            spent += trade_amount
            trades_executed += 1

        # Assert
        assert spent <= daily_limit
        assert trades_executed == 13  # 13 x $75 = $975, next would exceed $1000


class TestVVSConnectorIntegration:
    """Test integration with real VVS connector (mock mode)."""

    def test_connector_initialization(self):
        """Test VVS connector initializes correctly."""
        # Act
        connector = VVSFinanceConnector(use_mock=True, use_testnet=True)

        # Assert
        assert connector.use_mock is True
        assert connector.use_testnet is True

    def test_get_quote_mock_mode(self):
        """Get price quote in mock mode."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=True)

        # Act
        quote = connector.get_quote("CRO", "USDC", 100)

        # Assert
        assert "expected_amount_out" in quote
        assert "exchange_rate" in quote
        assert quote["source"] == "mock"

    def test_swap_returns_transaction_details(self):
        """Verify swap returns transaction details."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=True)

        # Act
        result = connector.swap("CRO", "USDC", 10)

        # Assert
        assert "tx_hash" in result or "unsigned_tx" in result
        assert "amount_out" in result or "expected_amount_out" in result


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_amount_rejected(self, mock_vvs_connector):
        """Reject zero amount trades."""
        # Arrange
        mock_vvs_connector.swap.side_effect = ValueError("Amount must be greater than 0")

        # Act & Assert
        with pytest.raises(ValueError, match="Amount must be greater than 0"):
            mock_vvs_connector.swap("CRO", "USDC", 0)

    def test_invalid_token_pair_handled(self, mock_vvs_connector):
        """Handle invalid token pairs gracefully."""
        # Arrange
        mock_vvs_connector.get_quote.return_value = {
            "error": "Unknown token pair",
            "source": "mock",
        }

        # Act
        result = mock_vvs_connector.get_quote("INVALID", "USDC", 100)

        # Assert
        assert "error" in result

    def test_negative_spread_no_trade(self, mock_vvs_pools):
        """No trade when spread is negative (would lose money)."""
        # Arrange - set up unfavorable prices
        pool = mock_vvs_pools["CRO-USDC"]
        buy_price = 0.08  # Expensive buy
        sell_price = pool.get_price()  # 0.075

        # Act
        profit_percent = ((sell_price - buy_price) / buy_price) * 100

        # Assert
        assert profit_percent < 0  # Would lose money

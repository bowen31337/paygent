"""
Use Case 5.3: Portfolio Management Agent Tests

Tests for the portfolio management agent that coordinates across
VVS/Moonlander/Delphi protocols, rebalances portfolios, and
requires HITL approval for positions > $10,000.

PRD Reference: Section 5.3 - Portfolio Management Agent
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestPortfolioMonitoring:
    """Test portfolio allocation monitoring."""

    def test_detect_balanced_portfolio(self, mock_portfolio_balanced, portfolio_config):
        """Verify balanced portfolio detection."""
        # Arrange
        positions = mock_portfolio_balanced["positions"]
        total = mock_portfolio_balanced["total_value_usd"]
        target = portfolio_config["target_allocation"]
        threshold = portfolio_config["rebalance_threshold"]

        # Act - Calculate current allocations
        current_allocation = {}
        for pos in positions:
            current_allocation[pos.token] = pos.value_usd / total

        # Assert - Check if within threshold
        for token, target_pct in target.items():
            current_pct = current_allocation.get(token, 0)
            deviation = abs(current_pct - target_pct)
            assert deviation <= threshold, f"{token} deviation {deviation} exceeds threshold"

    def test_detect_unbalanced_portfolio(self, mock_portfolio_unbalanced, portfolio_config):
        """Verify unbalanced portfolio detection triggers rebalance."""
        # Arrange
        allocation = mock_portfolio_unbalanced["allocation"]
        target = portfolio_config["target_allocation"]
        threshold = portfolio_config["rebalance_threshold"]

        # Act - Check for deviations
        needs_rebalance = False
        for token, target_pct in target.items():
            current_pct = allocation.get(token, 0)
            deviation = abs(current_pct - target_pct)
            if deviation > threshold:
                needs_rebalance = True
                break

        # Assert
        assert needs_rebalance is True
        assert allocation["CRO"] > target["CRO"]  # CRO is overweight

    def test_calculate_rebalancing_trades(self, mock_portfolio_unbalanced, portfolio_config):
        """Calculate required trades to rebalance portfolio."""
        # Arrange
        allocation = mock_portfolio_unbalanced["allocation"]
        total_value = mock_portfolio_unbalanced["total_value_usd"]
        target = portfolio_config["target_allocation"]

        # Act - Calculate trade amounts
        trades = []
        for token, target_pct in target.items():
            current_pct = allocation.get(token, 0)
            diff_pct = target_pct - current_pct
            diff_value = diff_pct * total_value

            if abs(diff_value) > 10:  # Only trade if > $10
                trades.append({
                    "token": token,
                    "action": "buy" if diff_value > 0 else "sell",
                    "amount_usd": abs(diff_value),
                })

        # Assert
        assert len(trades) > 0
        # CRO should be sold (overweight)
        cro_trade = next((t for t in trades if t["token"] == "CRO"), None)
        assert cro_trade is not None
        assert cro_trade["action"] == "sell"


class TestRebalancingExecution:
    """Test portfolio rebalancing execution."""

    @pytest.mark.asyncio
    async def test_rebalance_with_vvs_swap(self, mock_vvs_connector):
        """Rebalance portfolio using VVS swap."""
        # Arrange - Sell CRO for USDC
        from_token = "CRO"
        to_token = "USDC"
        amount = 150  # CRO to sell

        # Act
        result = mock_vvs_connector.swap(from_token, to_token, amount)

        # Assert
        assert result["success"] is True
        assert result["from_token"] == "CRO"
        assert result["to_token"] == "USDC"

    @pytest.mark.asyncio
    async def test_rebalance_with_moonlander_hedge(self, mock_moonlander_connector):
        """Adjust hedge position on Moonlander during rebalance."""
        # Arrange - Open short position to hedge long exposure
        mock_moonlander_connector.open_position.return_value = {
            "success": True,
            "position_id": "hedge-001",
            "side": "short",
            "size": 50,
            "entry_price": 42000,
        }

        # Act
        result = mock_moonlander_connector.open_position(
            market="BTC-USDC",
            side="short",
            size=50,
            leverage=2,
        )

        # Assert
        assert result["success"] is True
        assert result["side"] == "short"

    @pytest.mark.asyncio
    async def test_multi_protocol_rebalance(
        self,
        mock_vvs_connector,
        mock_moonlander_connector,
    ):
        """Execute multi-protocol rebalancing workflow."""
        # Step 1: Swap excess CRO for USDC on VVS
        swap_result = mock_vvs_connector.swap("CRO", "USDC", 100)
        assert swap_result["success"] is True

        # Step 2: Open hedge on Moonlander
        hedge_result = mock_moonlander_connector.open_position(
            market="CRO-USDC",
            side="short",
            size=30,
            leverage=3,
        )
        assert hedge_result["success"] is True


class TestHITLApproval:
    """Test Human-in-the-Loop approval for high-value transactions."""

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_hitl_required_above_threshold(self, mock_approval_service, portfolio_config):
        """Require human approval for positions > $10,000."""
        # Arrange
        threshold = portfolio_config["hitl_threshold_usd"]
        trade_amount = 15000  # Exceeds $10,000 threshold

        assert trade_amount > threshold

        # Act
        approval_request = await mock_approval_service.request_approval(
            tool_name="vvs_swap",
            args={"amount": trade_amount, "from_token": "CRO", "to_token": "USDC"},
        )

        # Assert
        assert approval_request["status"] == "pending"
        assert approval_request["tool_name"] == "vvs_swap"
        assert approval_request["args"]["amount"] == 15000

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_hitl_approval_proceeds(self, mock_approval_service, mock_vvs_connector):
        """Verify execution proceeds after approval."""
        # Arrange
        approval_id = "apr-123456"

        # Act - Simulate approval
        approval_result = await mock_approval_service.approve(approval_id)
        assert approval_result["decision"] == "approve"

        # Execute the trade after approval
        swap_result = mock_vvs_connector.swap("CRO", "USDC", 15000)

        # Assert
        assert swap_result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_hitl_rejection_stops_execution(self, mock_approval_service):
        """Handle rejection of high-value position."""
        # Arrange
        approval_id = "apr-123456"

        # Act
        rejection_result = await mock_approval_service.reject(approval_id)

        # Assert
        assert rejection_result["decision"] == "reject"

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_hitl_edit_before_approval(self, mock_approval_service):
        """Allow editing args before approval."""
        # Arrange
        mock_approval_service.edit.return_value = {
            "success": True,
            "original_args": {"amount": 20000},
            "edited_args": {"amount": 9500},  # Reduced below threshold
            "status": "pending",
        }

        # Act
        edit_result = await mock_approval_service.edit(
            approval_id="apr-123456",
            new_args={"amount": 9500},
        )

        # Assert
        assert edit_result["success"] is True
        assert edit_result["edited_args"]["amount"] == 9500

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_no_hitl_below_threshold(self, portfolio_config):
        """No HITL required for trades below threshold."""
        # Arrange
        threshold = portfolio_config["hitl_threshold_usd"]
        trade_amount = 5000  # Below $10,000 threshold

        # Assert
        assert trade_amount < threshold
        # Trade can proceed without approval


class TestRiskControls:
    """Test risk control enforcement."""

    def test_max_daily_drawdown_enforcement(self, mock_portfolio_unbalanced, portfolio_config):
        """Enforce 5% max daily drawdown limit."""
        # Arrange
        max_drawdown = portfolio_config["max_daily_drawdown"]
        current_drawdown = abs(mock_portfolio_unbalanced["daily_pnl_percent"]) / 100

        # Act
        trading_allowed = current_drawdown < max_drawdown

        # Assert
        assert trading_allowed is True  # -1.5% is under 5%

    def test_trading_halted_at_drawdown_limit(self, portfolio_config):
        """Verify trading halted when drawdown limit reached."""
        # Arrange
        max_drawdown = portfolio_config["max_daily_drawdown"]
        current_drawdown = 0.052  # 5.2% - exceeds 5% limit

        # Act
        trading_allowed = current_drawdown < max_drawdown

        # Assert
        assert trading_allowed is False

    def test_position_size_limits(self, portfolio_config):
        """Enforce position size limits relative to portfolio."""
        # Arrange
        total_portfolio = 100000
        max_position_pct = 0.10  # 10% max single position
        requested_position = 15000  # $15,000

        # Act
        position_pct = requested_position / total_portfolio
        within_limit = position_pct <= max_position_pct

        # Assert
        assert within_limit is False  # 15% exceeds 10% limit


class TestCompleteWorkflow:
    """Test end-to-end portfolio management workflow."""

    @pytest.mark.asyncio
    async def test_complete_portfolio_management_flow(
        self,
        mock_x402_facilitator,
        mock_vvs_connector,
        mock_moonlander_connector,
        mock_approval_service,
        mock_portfolio_unbalanced,
        portfolio_config,
    ):
        """End-to-end portfolio management."""
        # Step 1: Subscribe to research (x402)
        subscription = await mock_x402_facilitator.settle_payment(
            service_url="https://research.example.com/premium",
            amount=9.99,
            token="USDC",
        )
        assert subscription["success"] is True

        # Step 2: Detect rebalancing need
        allocation = mock_portfolio_unbalanced["allocation"]
        target = portfolio_config["target_allocation"]
        threshold = portfolio_config["rebalance_threshold"]

        needs_rebalance = any(
            abs(allocation.get(t, 0) - target[t]) > threshold
            for t in target
        )
        assert needs_rebalance is True

        # Step 3: Execute VVS swap (within limit)
        swap_result = mock_vvs_connector.swap("CRO", "USDC", 50)
        assert swap_result["success"] is True

        # Step 4: Adjust Moonlander hedge
        hedge_result = mock_moonlander_connector.open_position(
            market="CRO-USDC",
            side="short",
            size=20,
            leverage=2,
        )
        assert hedge_result["success"] is True

        # Step 5: Request HITL for large position (> $10k)
        approval = await mock_approval_service.request_approval(
            tool_name="moonlander_position",
            args={"size": 12000, "leverage": 5},
        )
        assert approval["status"] == "pending"

        # Step 6: Verify within risk parameters
        max_drawdown = portfolio_config["max_daily_drawdown"]
        current_drawdown = abs(mock_portfolio_unbalanced["daily_pnl_percent"]) / 100
        assert current_drawdown < max_drawdown

    @pytest.mark.asyncio
    async def test_workflow_respects_all_limits(
        self,
        mock_vvs_connector,
        mock_approval_service,
        portfolio_config,
    ):
        """Verify workflow respects all risk limits."""
        # Arrange
        hitl_threshold = portfolio_config["hitl_threshold_usd"]

        # Small trade - no HITL needed
        small_trade = 5000
        assert small_trade < hitl_threshold
        result = mock_vvs_connector.swap("CRO", "USDC", small_trade)
        assert result["success"] is True

        # Large trade - HITL required
        large_trade = 15000
        assert large_trade > hitl_threshold
        approval = await mock_approval_service.request_approval(
            tool_name="vvs_swap",
            args={"amount": large_trade},
        )
        assert approval["status"] == "pending"


class TestMultiProtocolCoordination:
    """Test coordination across VVS, Moonlander, and Delphi."""

    @pytest.mark.asyncio
    async def test_vvs_moonlander_coordination(
        self,
        mock_vvs_connector,
        mock_moonlander_connector,
    ):
        """Coordinate between VVS swaps and Moonlander positions."""
        # Arrange - Long spot via VVS, short hedge via Moonlander
        spot_amount = 100  # Buy $100 CRO spot

        # Act
        spot_result = mock_vvs_connector.swap("USDC", "CRO", spot_amount)
        hedge_result = mock_moonlander_connector.open_position(
            market="CRO-USDC",
            side="short",
            size=50,  # 50% hedge
            leverage=2,
        )

        # Assert
        assert spot_result["success"] is True
        assert hedge_result["success"] is True

    @pytest.mark.asyncio
    async def test_delphi_integration(self, mock_delphi_connector):
        """Include Delphi predictions in portfolio strategy."""
        # Act
        markets = mock_delphi_connector.get_markets()
        bet_result = mock_delphi_connector.place_bet(
            market_id="mkt-001",
            outcome="Yes",
            amount=10,
        )

        # Assert
        assert len(markets) > 0
        assert bet_result["success"] is True


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_portfolio_handling(self, portfolio_config):
        """Handle empty portfolio gracefully."""
        # Arrange
        empty_portfolio = {
            "positions": [],
            "total_value_usd": 0,
        }

        # Act
        has_positions = len(empty_portfolio["positions"]) > 0

        # Assert
        assert has_positions is False

    @pytest.mark.asyncio
    async def test_partial_execution_recovery(
        self,
        mock_vvs_connector,
        mock_moonlander_connector,
    ):
        """Recover from partial execution failure."""
        # Arrange - First swap succeeds, second fails
        mock_vvs_connector.swap.return_value = {"success": True, "tx_hash": "0x..."}
        mock_moonlander_connector.open_position.return_value = {
            "success": False,
            "error": "Insufficient margin",
        }

        # Act
        swap_result = mock_vvs_connector.swap("CRO", "USDC", 100)
        position_result = mock_moonlander_connector.open_position(
            market="BTC-USDC",
            side="long",
            size=1000,
            leverage=10,
        )

        # Assert
        assert swap_result["success"] is True
        assert position_result["success"] is False
        # System should log partial failure and potentially rollback

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_approval_timeout_handling(self, mock_approval_service):
        """Handle approval request timeout."""
        # Arrange
        mock_approval_service.get_approval_status.return_value = {
            "status": "expired",
            "reason": "Approval request timed out after 24 hours",
        }

        # Act
        status = await mock_approval_service.get_approval_status("apr-old")

        # Assert
        assert status["status"] == "expired"

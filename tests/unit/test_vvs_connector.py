"""
Unit tests for VVS Finance connector.

Tests all VVS Finance connector functionality including:
- Token swaps with slippage protection
- Liquidity pool management
- Yield farming
- Price quotes
"""

import pytest
from decimal import Decimal

from src.connectors.vvs import VVSFinanceConnector


class TestVVSFinanceConnector:
    """Test suite for VVS Finance connector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.vvs = VVSFinanceConnector()

    def test_get_quote_cro_to_usdc(self):
        """Test getting quote for CRO to USDC swap."""
        quote = self.vvs.get_quote("CRO", "USDC", 100.0, slippage_tolerance=1.0)

        assert quote["from_token"] == "CRO"
        assert quote["to_token"] == "USDC"
        assert quote["amount_in"] == "100"
        assert quote["expected_amount_out"] == "7.5"  # 100 * 0.075
        assert quote["min_amount_out"] == "7.425"  # 7.5 * 0.99
        assert quote["exchange_rate"] == "0.075"
        assert quote["slippage_tolerance"] == 1.0
        assert "fee" in quote
        assert "price_impact" in quote

    def test_get_quote_usdc_to_cro(self):
        """Test getting quote for USDC to CRO swap."""
        quote = self.vvs.get_quote("USDC", "CRO", 10.0, slippage_tolerance=1.0)

        assert quote["from_token"] == "USDC"
        assert quote["to_token"] == "CRO"
        assert quote["amount_in"] == "10"
        assert quote["expected_amount_out"] == "133.33"  # 10 * 13.333
        assert quote["exchange_rate"] == "13.333"

    def test_get_quote_with_different_slippage(self):
        """Test quote with different slippage tolerance."""
        quote_1pct = self.vvs.get_quote("CRO", "USDC", 100.0, slippage_tolerance=1.0)
        quote_5pct = self.vvs.get_quote("CRO", "USDC", 100.0, slippage_tolerance=5.0)

        # 5% slippage should have lower minimum output
        min_1pct = Decimal(quote_1pct["min_amount_out"])
        min_5pct = Decimal(quote_5pct["min_amount_out"])

        assert min_5pct < min_1pct

    def test_swap_executes_successfully(self):
        """Test swap execution returns valid result."""
        result = self.vvs.swap(
            from_token="CRO",
            to_token="USDC",
            amount=100.0,
            slippage_tolerance=1.0,
            deadline=120
        )

        assert result["success"] is True
        assert result["from_token"] == "CRO"
        assert result["to_token"] == "USDC"
        assert result["amount_in"] == "100"
        assert result["amount_out"] == "7.5"
        assert result["min_amount_out"] == "7.425"
        assert result["slippage_tolerance"] == 1.0
        assert result["deadline"] == 120
        assert result["tx_hash"].startswith("0x")
        assert len(result["tx_hash"]) == 66  # 0x + 64 hex chars

    def test_swap_with_default_deadline(self):
        """Test swap uses default deadline when not specified."""
        result = self.vvs.swap(
            from_token="CRO",
            to_token="USDC",
            amount=100.0
        )

        assert result["deadline"] == 120  # Default 2 minutes

    def test_add_liquidity(self):
        """Test adding liquidity to a pool."""
        result = self.vvs.add_liquidity(
            token_a="CRO",
            token_b="USDC",
            amount_a=1000.0,
            amount_b=75.0,
            slippage_tolerance=1.0
        )

        assert result["success"] is True
        assert result["pair"] == "CRO-USDC"
        assert result["token_a"] == "CRO"
        assert result["token_b"] == "USDC"
        assert result["amount_a"] == "1000.0"
        assert result["amount_b"] == "75.0"
        assert "lp_tokens_received" in result
        assert "min_lp_tokens" in result
        assert result["lp_token_address"] is not None
        assert result["tx_hash"].startswith("0x")

    def test_remove_liquidity(self):
        """Test removing liquidity from a pool."""
        result = self.vvs.remove_liquidity(
            token_a="CRO",
            token_b="USDC",
            lp_amount=100.0
        )

        assert result["success"] is True
        assert result["pair"] == "CRO-USDC"
        assert result["lp_tokens_burned"] == "100.0"
        assert "amount_a_received" in result
        assert "amount_b_received" in result
        assert result["token_a"] == "CRO"
        assert result["token_b"] == "USDC"
        assert result["tx_hash"].startswith("0x")

    def test_stake_lp_tokens(self):
        """Test staking LP tokens in yield farm."""
        result = self.vvs.stake_lp_tokens(
            token_a="CRO",
            token_b="USDC",
            amount=100.0
        )

        assert result["success"] is True
        assert result["pair"] == "CRO-USDC"
        assert result["lp_tokens_staked"] == "100.0"
        assert "farm_id" in result
        assert result["reward_token"] == "VVS"
        assert "estimated_daily_reward" in result
        assert result["tx_hash"].startswith("0x")

    def test_stake_lp_tokens_with_custom_farm(self):
        """Test staking LP tokens in a specific farm."""
        result = self.vvs.stake_lp_tokens(
            token_a="CRO",
            token_b="USDC",
            amount=100.0,
            farm_id="custom_farm_1"
        )

        assert result["farm_id"] == "custom_farm_1"

    def test_get_price_impact(self):
        """Test price impact calculation."""
        # Small amount = low impact
        impact_small = self.vvs.get_price_impact("CRO", "USDC", 5.0)
        assert impact_small < Decimal("0.5")

        # Large amount = higher impact
        impact_large = self.vvs.get_price_impact("CRO", "USDC", 1000.0)
        assert impact_large > impact_small

    def test_unknown_pair_fallback(self):
        """Test unknown token pair uses fallback rate."""
        quote = self.vvs.get_quote("ABC", "XYZ", 100.0)

        assert quote["from_token"] == "ABC"
        assert quote["to_token"] == "XYZ"
        assert quote["exchange_rate"] == "1"  # Fallback

    def test_mock_tx_hash_format(self):
        """Test mock transaction hash format."""
        hash1 = self.vvs._generate_mock_tx_hash()
        hash2 = self.vvs._generate_mock_tx_hash()

        assert hash1.startswith("0x")
        assert len(hash1) == 66  # 0x + 64 chars
        assert hash1 != hash2  # Should be random

    def test_lp_token_addresses(self):
        """Test LP token address lookup."""
        assert "CRO-USDC" in self.vvs.LP_TOKENS
        assert "CRO-USDT" in self.vvs.LP_TOKENS
        assert self.vvs.LP_TOKENS["CRO-USDC"].startswith("0x")

    def test_mock_rates_defined(self):
        """Test that mock rates are defined for common pairs."""
        assert ("CRO", "USDC") in self.vvs.MOCK_RATES
        assert ("USDC", "CRO") in self.vvs.MOCK_RATES
        assert ("CRO", "USDT") in self.vvs.MOCK_RATES
        assert ("USDT", "CRO") in self.vvs.MOCK_RATES
        assert ("USDC", "USDT") in self.vvs.MOCK_RATES


class TestVVSQuoteTool:
    """Test VVS quote tool."""

    def setup_method(self):
        from src.tools.simple_tools import VVSQuoteTool
        self.tool = VVSQuoteTool()

    def test_tool_properties(self):
        assert self.tool.name == "vvs_quote"
        assert "price quote" in self.tool.description.lower()

    def test_run_returns_quote(self):
        result = self.tool.run(
            from_token="CRO",
            to_token="USDC",
            amount=100.0,
            slippage_tolerance_percent=1.0
        )

        assert result["from_token"] == "CRO"
        assert result["to_token"] == "USDC"
        assert result["amount_in"] == "100"


class TestSwapTokensTool:
    """Test swap tokens tool."""

    def setup_method(self):
        from src.tools.simple_tools import SwapTokensTool
        self.tool = SwapTokensTool()

    def test_tool_properties(self):
        assert self.tool.name == "swap_tokens"
        assert "VVS Finance" in self.tool.description

    def test_run_executes_swap(self):
        result = self.tool.run(
            from_token="CRO",
            to_token="USDC",
            amount=100.0,
            slippage_tolerance_percent=1.0,
            deadline=120
        )

        assert result["success"] is True
        assert result["from_token"] == "CRO"
        assert result["to_token"] == "USDC"
        assert result["tx_hash"].startswith("0x")

    def test_run_with_defaults(self):
        result = self.tool.run(
            from_token="CRO",
            to_token="USDC",
            amount=100.0
        )

        assert result["success"] is True
        assert result["slippage_tolerance"] == 1.0


class TestVVSLiquidityTool:
    """Test VVS liquidity tool."""

    def setup_method(self):
        from src.tools.simple_tools import VVSLiquidityTool
        self.tool = VVSLiquidityTool()

    def test_tool_properties(self):
        assert self.tool.name == "vvs_liquidity"
        assert "liquidity" in self.tool.description.lower()

    def test_add_liquidity(self):
        result = self.tool.run(
            action="add",
            token_a="CRO",
            token_b="USDC",
            amount_a=1000.0,
            amount_b=75.0
        )

        assert result["success"] is True
        assert result["pair"] == "CRO-USDC"

    def test_remove_liquidity(self):
        result = self.tool.run(
            action="remove",
            token_a="CRO",
            token_b="USDC",
            lp_amount=100.0
        )

        assert result["success"] is True
        assert result["lp_tokens_burned"] == "100.0"

    def test_invalid_action(self):
        with pytest.raises(ValueError, match="Unknown action"):
            self.tool.run(
                action="invalid",
                token_a="CRO",
                token_b="USDC"
            )

    def test_missing_amount_for_add(self):
        with pytest.raises(ValueError, match="amount_a and amount_b required"):
            self.tool.run(
                action="add",
                token_a="CRO",
                token_b="USDC"
            )

    def test_missing_lp_amount_for_remove(self):
        with pytest.raises(ValueError, match="lp_amount required"):
            self.tool.run(
                action="remove",
                token_a="CRO",
                token_b="USDC"
            )


class TestVVSFarmingTool:
    """Test VVS farming tool."""

    def setup_method(self):
        from src.tools.simple_tools import VVSFarmingTool
        self.tool = VVSFarmingTool()

    def test_tool_properties(self):
        assert self.tool.name == "vvs_farm"
        assert "farm" in self.tool.description.lower()

    def test_stake_lp_tokens(self):
        result = self.tool.run(
            token_a="CRO",
            token_b="USDC",
            amount=100.0
        )

        assert result["success"] is True
        assert result["lp_tokens_staked"] == "100.0"
        assert result["reward_token"] == "VVS"

    def test_stake_with_custom_farm(self):
        result = self.tool.run(
            token_a="CRO",
            token_b="USDC",
            amount=100.0,
            farm_id="custom_farm"
        )

        assert result["farm_id"] == "custom_farm"


class TestGetAllTools:
    """Test get_all_tools function."""

    def test_all_vvs_tools_present(self):
        from src.tools.simple_tools import get_all_tools

        tools = get_all_tools()

        assert "swap_tokens" in tools
        assert "vvs_quote" in tools
        assert "vvs_liquidity" in tools
        assert "vvs_farm" in tools

    def test_tools_are_instances(self):
        from src.tools.simple_tools import get_all_tools, SimpleTool

        tools = get_all_tools()

        for name, tool in tools.items():
            assert isinstance(tool, SimpleTool)
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "run")

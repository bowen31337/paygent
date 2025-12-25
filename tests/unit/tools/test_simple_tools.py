"""Unit tests for simple agent tools."""

from unittest.mock import MagicMock, patch

import pytest

from src.tools.simple_tools import (
    CheckBalanceTool,
    DiscoverServicesTool,
    SwapTokensTool,
    VVSFarmingTool,
    VVSLiquidityTool,
    VVSQuoteTool,
    X402PaymentTool,
    get_all_tools,
)


class TestCheckBalanceTool:
    def test_tool_attributes(self):
        tool = CheckBalanceTool()
        assert tool.name == "check_balance"
        assert "balance" in tool.description.lower()

    def test_run_with_default_tokens(self):
        tool = CheckBalanceTool()
        result = tool.run()
        assert "balances" in result
        assert "CRO" in result["balances"]

    def test_run_with_custom_wallet(self):
        tool = CheckBalanceTool()
        wallet = "0x1234567890123456789012345678901234567890"
        result = tool.run(wallet_address=wallet)
        assert result["wallet_address"] == wallet


class TestX402PaymentTool:
    def test_tool_attributes(self):
        tool = X402PaymentTool()
        assert tool.name == "x402_payment"

    def test_run_basic_payment(self):
        tool = X402PaymentTool()
        result = tool.run(service_url="https://api.example.com/data", amount=1.5)
        assert result["status"] == "confirmed"
        assert result["tx_hash"].startswith("0x")


class TestSwapTokensTool:
    def test_tool_attributes(self):
        tool = SwapTokensTool()
        assert tool.name == "swap_tokens"

    @patch("src.tools.simple_tools.VVSFinanceConnector")
    def test_run_swap(self, mock_connector_class):
        mock_connector = MagicMock()
        mock_connector_class.return_value = mock_connector
        mock_connector.swap.return_value = {"status": "success", "from_token": "CRO"}

        tool = SwapTokensTool()
        result = tool.run(from_token="CRO", to_token="USDC", amount=100.0)
        assert result["status"] == "success"


class TestVVSQuoteTool:
    def test_tool_attributes(self):
        tool = VVSQuoteTool()
        assert tool.name == "vvs_quote"

    @patch("src.tools.simple_tools.VVSFinanceConnector")
    def test_run_quote(self, mock_connector_class):
        mock_connector = MagicMock()
        mock_connector_class.return_value = mock_connector
        mock_connector.get_quote.return_value = {"from_token": "CRO", "amount_out": 25.5}

        tool = VVSQuoteTool()
        result = tool.run(from_token="CRO", to_token="USDC", amount=100.0)
        assert result["amount_out"] == 25.5


class TestVVSLiquidityTool:
    def test_tool_attributes(self):
        tool = VVSLiquidityTool()
        assert tool.name == "vvs_liquidity"

    @patch("src.tools.simple_tools.VVSFinanceConnector")
    def test_add_liquidity(self, mock_connector_class):
        mock_connector = MagicMock()
        mock_connector_class.return_value = mock_connector
        mock_connector.add_liquidity.return_value = {"status": "success"}

        tool = VVSLiquidityTool()
        result = tool.run(action="add", token_a="CRO", token_b="USDC", amount_a=100.0, amount_b=25.0)
        assert result["status"] == "success"

    def test_invalid_action(self):
        tool = VVSLiquidityTool()
        with pytest.raises(ValueError, match="Unknown action"):
            tool.run(action="invalid", token_a="CRO", token_b="USDC")


class TestVVSFarmingTool:
    def test_tool_attributes(self):
        tool = VVSFarmingTool()
        assert tool.name == "vvs_farm"

    @patch("src.tools.simple_tools.VVSFinanceConnector")
    def test_run_farm(self, mock_connector_class):
        mock_connector = MagicMock()
        mock_connector_class.return_value = mock_connector
        mock_connector.stake_lp_tokens.return_value = {"status": "success"}

        tool = VVSFarmingTool()
        result = tool.run(token_a="CRO", token_b="USDC", amount=100.0)
        assert result["status"] == "success"


class TestDiscoverServicesTool:
    def test_tool_attributes(self):
        tool = DiscoverServicesTool()
        assert tool.name == "discover_services"

    def test_run_discover_all(self):
        tool = DiscoverServicesTool()
        result = tool.run()
        assert "services" in result
        assert result["total"] > 0

    def test_run_discover_by_category(self):
        tool = DiscoverServicesTool()
        result = tool.run(category="market_data")
        assert result["total"] == 1


class TestGetAllTools:
    def test_returns_all_tools(self):
        tools = get_all_tools()
        expected = ["check_balance", "x402_payment", "swap_tokens", "vvs_quote", "vvs_liquidity", "vvs_farm", "discover_services"]
        assert set(tools.keys()) == set(expected)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Test MCP integration with LangChain.

Tests that the MCP client connects to the server and LangChain tools work properly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.mcp_client import MCPServerClient, MCPServerError, get_mcp_client
from src.tools.market_data_tools import GetPriceTool, GetPricesTool, GetMarketStatusTool


@pytest.mark.asyncio
async def test_mcp_client_initialization():
    """Test that MCP client initializes with correct configuration."""
    client = MCPServerClient()

    assert client.server_url == "https://mcp.crypto.com"
    assert client.session is not None
    assert client.rate_limit_delay == 0.1


@pytest.mark.asyncio
async def test_mcp_client_health_check():
    """Test MCP client health check functionality."""
    client = MCPServerClient()

    # Mock successful health check
    with patch.object(client, 'get_market_status', return_value={"status": "ok"}):
        is_healthy = await client.health_check()
        assert is_healthy is True


@pytest.mark.asyncio
async def test_mcp_get_price():
    """Test getting price from MCP server."""
    client = MCPServerClient()

    # Mock the request method
    mock_response = {
        "symbol": "BTC_USDT",
        "price": 50000.0,
        "volume": 1000.0,
        "change": 2.5,
        "timestamp": 1234567890
    }

    with patch.object(client, '_make_request', return_value=mock_response):
        price_data = await client.get_price("BTC_USDT")

        assert price_data.symbol == "BTC_USDT"
        assert price_data.price == 50000.0
        assert price_data.volume_24h == 1000.0
        assert price_data.change_24h == 2.5


@pytest.mark.asyncio
async def test_langchain_get_price_tool():
    """Test LangChain tool for getting price."""
    tool = GetPriceTool()

    assert tool.name == "get_crypto_price"
    assert tool.args_schema is not None

    # Mock the async method
    with patch.object(tool, '_get_price_async', return_value={
        "symbol": "BTC_USDT",
        "price": 50000.0,
        "success": True
    }):
        result = tool._run("BTC_USDT")
        assert result["success"] is True
        assert result["price"] == 50000.0


@pytest.mark.asyncio
async def test_langchain_get_prices_tool():
    """Test LangChain tool for getting multiple prices."""
    tool = GetPricesTool()

    assert tool.name == "get_crypto_prices"

    # Mock the async method
    with patch.object(tool, '_get_prices_async', return_value={
        "symbols": ["BTC_USDT", "ETH_USDT"],
        "total_symbols": 2,
        "success": True
    }):
        result = tool._run(["BTC_USDT", "ETH_USDT"])
        assert result["success"] is True
        assert result["total_symbols"] == 2


@pytest.mark.asyncio
async def test_langchain_market_status_tool():
    """Test LangChain tool for market status."""
    tool = GetMarketStatusTool()

    assert tool.name == "get_market_status"

    # Mock the async method
    with patch.object(tool, '_get_market_status_async', return_value={
        "server_health": True,
        "market_status": "open",
        "success": True
    }):
        result = tool._run()
        assert result["success"] is True
        assert result["server_health"] is True


@pytest.mark.asyncio
async def test_mcp_error_handling():
    """Test MCP server error handling."""
    client = MCPServerClient()

    # Mock HTTP error
    import httpx
    with patch.object(client, '_make_request', side_effect=httpx.HTTPStatusError(
        "Server error", request=MagicMock(), response=MagicMock(status_code=500)
    )):
        with pytest.raises(MCPServerError) as exc_info:
            await client.get_price("BTC_USDT")

        assert "HTTP 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mcp_rate_limiting():
    """Test that MCP client enforces rate limiting."""
    client = MCPServerClient()
    client.rate_limit_delay = 0.05  # 50ms for testing

    import time
    with patch.object(client, '_make_request', return_value={"status": "ok"}):
        start = time.time()
        await client.get_market_status()
        await client.get_market_status()
        elapsed = time.time() - start

        # Should take at least 50ms due to rate limiting
        assert elapsed >= 0.05


@pytest.mark.asyncio
async def test_get_mcp_client_singleton():
    """Test that get_mcp_client returns singleton instance."""
    client1 = get_mcp_client()
    client2 = get_mcp_client()

    assert client1 is client2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

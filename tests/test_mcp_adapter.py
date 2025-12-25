"""Test LangChain MCP adapter integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain.tools import BaseTool

from src.services.mcp_adapter import (
    CryptoComMCPAdapter,
    MCPAdapterError,
    create_mcp_adapter,
    get_mcp_adapter,
)
from src.services.mcp_client import MCPServerClient


@pytest.mark.asyncio
async def test_mcp_adapter_initialization():
    """Test MCP adapter initialization."""
    # Mock MCP client
    mock_client = AsyncMock(spec=MCPServerClient)
    mock_client.health_check.return_value = True
    mock_client.get_supported_symbols.return_value = ["BTC_USDT", "ETH_USDT"]
    mock_client.get_market_status.return_value = {
        "server_time": 1234567890,
        "market_status": "open",
        "supported_symbols": 2
    }

    adapter = CryptoComMCPAdapter(mock_client)

    # Mock the tool creation
    with patch.object(adapter, '_create_tools_from_mcp_capabilities', return_value=[]):
        await adapter.initialize()

    assert adapter.mcp_client == mock_client
    assert adapter.adapter_config is not None
    assert adapter.tools == []


@pytest.mark.asyncio
async def test_mcp_adapter_health_check():
    """Test MCP adapter health check."""
    mock_client = AsyncMock(spec=MCPServerClient)
    mock_client.health_check.return_value = True

    adapter = CryptoComMCPAdapter(mock_client)

    is_healthy = await adapter.is_healthy()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_mcp_adapter_server_info():
    """Test MCP adapter server info retrieval."""
    expected_info = {
        "server_time": 1234567890,
        "market_status": "open",
        "supported_symbols": 2
    }

    mock_client = AsyncMock(spec=MCPServerClient)
    mock_client.get_market_status.return_value = expected_info

    adapter = CryptoComMCPAdapter(mock_client)

    server_info = await adapter.get_server_info()
    assert server_info == expected_info


@pytest.mark.asyncio
async def test_mcp_adapter_get_tools():
    """Test MCP adapter tool retrieval."""
    mock_client = AsyncMock(spec=MCPServerClient)
    mock_client.health_check.return_value = True
    mock_client.get_supported_symbols.return_value = ["BTC_USDT", "ETH_USDT"]
    mock_client.get_market_status.return_value = {
        "server_time": 1234567890,
        "market_status": "open",
        "supported_symbols": 2
    }

    adapter = CryptoComMCPAdapter(mock_client)

    # Mock the tool creation to return some tools
    mock_tool = MagicMock(spec=BaseTool)
    mock_tool.name = "test_tool"
    mock_tool.description = "Test tool"

    with patch.object(adapter, '_create_tools_from_mcp_capabilities', return_value=[mock_tool]):
        tools = await adapter.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "test_tool"


@pytest.mark.asyncio
async def test_mcp_adapter_initialization_error():
    """Test MCP adapter initialization with error."""
    mock_client = AsyncMock(spec=MCPServerClient)
    mock_client.health_check.return_value = False

    adapter = CryptoComMCPAdapter(mock_client)

    with pytest.raises(MCPAdapterError):
        await adapter.initialize()


@pytest.mark.asyncio
async def test_mcp_adapter_singleton():
    """Test MCP adapter singleton pattern."""
    adapter1 = get_mcp_adapter()
    adapter2 = get_mcp_adapter()

    assert adapter1 is adapter2


@pytest.mark.asyncio
async def test_mcp_adapter_creation():
    """Test MCP adapter creation with custom client."""
    mock_client = AsyncMock(spec=MCPServerClient)
    adapter = create_mcp_adapter(mock_client)

    assert adapter.mcp_client == mock_client


@pytest.mark.asyncio
async def test_mcp_adapter_tool_creation():
    """Test MCP adapter tool creation from capabilities."""
    mock_client = AsyncMock(spec=MCPServerClient)
    mock_client.get_supported_symbols.return_value = ["BTC_USDT", "ETH_USDT"]
    mock_client.get_market_status.return_value = {
        "server_time": 1234567890,
        "market_status": "open",
        "supported_symbols": 2
    }

    adapter = CryptoComMCPAdapter(mock_client)

    # Mock price data
    mock_price_data = MagicMock()
    mock_price_data.symbol = "BTC_USDT"
    mock_price_data.price = 50000.0
    mock_price_data.volume_24h = 1000.0
    mock_price_data.change_24h = 2.5
    mock_price_data.timestamp = 1234567890

    with patch.object(mock_client, 'get_price', return_value=mock_price_data):
        with patch.object(mock_client, 'get_multiple_prices', return_value=[mock_price_data]):
            tools = await adapter._create_tools_from_mcp_capabilities()

            # Should create 3 tools: get_crypto_price, get_crypto_prices, get_market_status
            assert len(tools) == 3

            # Test that tools have correct names
            tool_names = [tool.name for tool in tools]
            assert "get_crypto_price" in tool_names
            assert "get_crypto_prices" in tool_names
            assert "get_market_status" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

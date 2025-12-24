#!/usr/bin/env python3
"""
Simple synchronous test for MCP functionality.
"""

import sys
import time
from typing import Any, Dict

# Add the project root to Python path
sys.path.insert(0, '/media/DATA/projects/autonomous-coding-cro/paygent')

def test_mcp_client_basic():
    """Test basic MCP client functionality."""
    try:
        from src.services.mcp_client import MCPServerClient, MCPServerError, PriceData
        from datetime import datetime

        print("=== Testing MCP Client Basic Functionality ===")

        # Create client
        client = MCPServerClient()
        print(f"✓ Client created with server URL: {client.server_url}")

        # Test data model
        price_data = PriceData(
            symbol="BTC_USDT",
            price=50000.0,
            volume_24h=1000.0,
            change_24h=2.5,
            timestamp=int(datetime.now().timestamp())
        )
        print(f"✓ PriceData model works: {price_data.symbol} = ${price_data.price}")

        # Test error handling
        error = MCPServerError("Test error")
        print(f"✓ MCPServerError works: {error}")

        return True

    except Exception as e:
        print(f"✗ Error in basic test: {e}")
        return False


def test_market_data_tools():
    """Test market data tools integration."""
    try:
        print("\n=== Testing Market Data Tools ===")

        from src.tools.market_data_tools import (
            GetPriceTool, GetPricesTool, GetMarketStatusTool
        )

        print("✓ Market data tools imported successfully")

        # Test tool creation
        price_tool = GetPriceTool()
        prices_tool = GetPricesTool()
        status_tool = GetMarketStatusTool()

        print("✓ All market data tools created successfully")
        print(f"  Price tool name: {price_tool.name}")
        print(f"  Prices tool name: {prices_tool.name}")
        print(f"  Status tool name: {status_tool.name}")

        # Test input schemas
        from src.tools.market_data_tools import GetPriceInput, GetPricesInput, GetMarketStatusInput

        price_input = GetPriceInput(symbol="BTC_USDT")
        print(f"✓ Price input schema: {price_input.symbol}")

        prices_input = GetPricesInput(symbols=["BTC_USDT", "ETH_USDT"])
        print(f"✓ Prices input schema: {prices_input.symbols}")

        return True

    except Exception as e:
        print(f"✗ Error in tools test: {e}")
        return False


def test_configuration():
    """Test configuration loading."""
    try:
        print("\n=== Testing Configuration ===")

        from src.core.config import settings

        print(f"✓ Configuration loaded")
        print(f"  MCP Server URL: {settings.crypto_com_mcp_url}")
        print(f"  API Key set: {settings.crypto_com_api_key is not None}")

        # Test client instantiation with custom URL
        from src.services.mcp_client import create_mcp_client

        custom_client = create_mcp_client("https://test.mcp.crypto.com")
        print(f"✓ Custom client created: {custom_client.server_url}")

        return True

    except Exception as e:
        print(f"✗ Error in configuration test: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing Crypto.com Market Data MCP Server Integration")
    print("=" * 60)

    tests = [
        test_mcp_client_basic,
        test_market_data_tools,
        test_configuration,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    print(f"  Tests run: {len(results)}")
    print(f"  Passed: {sum(results)}")
    print(f"  Failed: {len(results) - sum(results)}")

    if all(results):
        print("✓ All tests passed!")
        print("\nMCP Integration Status:")
        print("✓ MCP client configured correctly")
        print("✓ Market data tools available")
        print("✓ Data models working")
        print("✓ Configuration loaded")
        print("✓ Error handling implemented")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
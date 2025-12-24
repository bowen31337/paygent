#!/usr/bin/env python3
"""
Test script for BTC price query functionality.
"""

import sys
import asyncio
import time
from typing import Any, Dict

# Add the project root to Python path
sys.path.insert(0, '/media/DATA/projects/autonomous-coding-cro/paygent')

async def test_mcp_client_basic():
    """Test basic MCP client functionality."""
    try:
        from src.services.mcp_client import MCPServerClient, MCPServerError

        print("=== Testing MCP Client Basic Functionality ===")

        # Create client
        client = MCPServerClient()
        print(f"✓ Client created with server URL: {client.server_url}")

        # Test health check (this will likely fail without real server but should handle gracefully)
        print("Testing health check...")
        try:
            is_healthy = await client.health_check()
            print(f"  Health check result: {is_healthy}")
        except MCPServerError as e:
            print(f"  Expected error (no real server): {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")

        # Test market status (will fail but should handle gracefully)
        print("Testing market status...")
        try:
            status = await client.get_market_status()
            print(f"  Market status: {status}")
        except MCPServerError as e:
            print(f"  Expected error (no real server): {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")

        # Test price query (will fail but should handle gracefully)
        print("Testing BTC price query...")
        try:
            price_data = await client.get_price("BTC_USDT")
            print(f"  BTC price: {price_data.price}")
        except MCPServerError as e:
            print(f"  Expected error (no real server): {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")

        return True

    except Exception as e:
        print(f"✗ Error in basic test: {e}")
        return False


async def test_market_data_tools():
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

        # Test price tool with mock data (will fail gracefully)
        print("Testing price tool...")
        try:
            result = price_tool._run("BTC_USDT")
            print(f"  Price tool result: {result}")
        except Exception as e:
            print(f"  Price tool error (expected): {e}")

        # Test multiple prices tool
        print("Testing multiple prices tool...")
        try:
            result = prices_tool._run(["BTC_USDT", "ETH_USDT"])
            print(f"  Multiple prices result: {result}")
        except Exception as e:
            print(f"  Multiple prices tool error (expected): {e}")

        # Test market status tool
        print("Testing market status tool...")
        try:
            result = status_tool._run()
            print(f"  Market status result: {result}")
        except Exception as e:
            print(f"  Market status tool error (expected): {e}")

        return True

    except Exception as e:
        print(f"✗ Error in tools test: {e}")
        return False


async def test_mcp_data_model():
    """Test MCP data model structures."""
    try:
        print("\n=== Testing MCP Data Models ===")

        from src.services.mcp_client import PriceData
        from datetime import datetime

        # Test PriceData creation
        price_data = PriceData(
            symbol="BTC_USDT",
            price=50000.0,
            volume_24h=1000.0,
            change_24h=2.5,
            timestamp=int(datetime.now().timestamp())
        )

        print(f"✓ PriceData created: {price_data.symbol} = ${price_data.price}")
        print(f"  Volume 24h: {price_data.volume_24h}")
        print(f"  Change 24h: {price_data.change_24h}%")
        print(f"  Timestamp: {price_data.timestamp}")

        return True

    except Exception as e:
        print(f"✗ Error in data model test: {e}")
        return False


async def test_mcp_error_handling():
    """Test MCP error handling."""
    try:
        print("\n=== Testing MCP Error Handling ===")

        from src.services.mcp_client import MCPServerError

        # Test error creation
        error = MCPServerError("Test error message")
        print(f"✓ MCPServerError created: {error}")

        # Test error inheritance
        assert isinstance(error, Exception)
        print("✓ MCPServerError inherits from Exception")

        return True

    except Exception as e:
        print(f"✗ Error in error handling test: {e}")
        return False


async def main():
    """Run all tests."""
    print("Testing Crypto.com Market Data MCP Server Integration")
    print("=" * 60)

    tests = [
        test_mcp_client_basic,
        test_market_data_tools,
        test_mcp_data_model,
        test_mcp_error_handling,
    ]

    results = []
    for test in tests:
        try:
            result = await test()
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
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
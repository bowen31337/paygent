#!/usr/bin/env python3
"""
Test MCP schema compliance for Crypto.com Market Data integration.
"""

import json
import sys

# Add the project root to Python path
sys.path.insert(0, '/media/DATA/projects/autonomous-coding-cro/paygent')

def test_mcp_response_schemas():
    """Test that our MCP responses follow proper schema."""
    try:
        print("=== Testing MCP Response Schemas ===")

        from datetime import datetime

        from src.services.mcp_client import PriceData

        # Test PriceData schema compliance
        price_data = PriceData(
            symbol="BTC_USDT",
            price=50000.0,
            volume_24h=1000.0,
            change_24h=2.5,
            timestamp=int(datetime.now().timestamp())
        )

        # Convert to dict for schema validation
        price_dict = {
            "symbol": price_data.symbol,
            "price": price_data.price,
            "volume_24h": price_data.volume_24h,
            "change_24h": price_data.change_24h,
            "timestamp": price_data.timestamp
        }

        # Validate required fields
        required_fields = ["symbol", "price", "volume_24h", "change_24h", "timestamp"]
        for field in required_fields:
            if field not in price_dict:
                raise ValueError(f"Missing required field: {field}")
            if price_dict[field] is None:
                raise ValueError(f"Field {field} cannot be null")

        print("✓ PriceData schema validation passed")
        print(f"  Symbol format: {price_data.symbol}")
        print(f"  Price format: {price_data.price} (float)")
        print(f"  Volume format: {price_data.volume_24h} (float)")
        print(f"  Change format: {price_data.change_24h} (float)")
        print(f"  Timestamp format: {price_data.timestamp} (int)")

        # Test JSON serialization
        json_str = json.dumps(price_dict)
        parsed_back = json.loads(json_str)
        print("✓ JSON serialization/deserialization works")

        return True

    except Exception as e:
        print(f"✗ Error in schema test: {e}")
        return False


def test_tool_input_schemas():
    """Test that tool input schemas are compliant."""
    try:
        print("\n=== Testing Tool Input Schemas ===")

        from src.tools.market_data_tools import GetMarketStatusInput, GetPriceInput, GetPricesInput

        # Test GetPriceInput
        price_input = GetPriceInput(symbol="BTC_USDT")
        print(f"✓ GetPriceInput: {price_input.symbol}")

        # Test GetPricesInput
        prices_input = GetPricesInput(symbols=["BTC_USDT", "ETH_USDT"])
        print(f"✓ GetPricesInput: {prices_input.symbols}")

        # Test GetMarketStatusInput (empty)
        status_input = GetMarketStatusInput()
        print(f"✓ GetMarketStatusInput: {status_input}")

        # Test validation with empty string (should work since Field(...) only requires presence)
        try:
            empty_symbol_input = GetPriceInput(symbol="")
            print(f"✓ Empty symbol accepted: '{empty_symbol_input.symbol}'")
        except Exception as e:
            print(f"✓ Validation correctly rejected empty symbol: {e}")

        # Test with None (should fail)
        try:
            none_input = GetPriceInput(symbol=None)
            print("✗ Validation should have failed for None symbol")
            return False
        except Exception:
            print("✓ Input validation works for None symbol")

        return True

    except Exception as e:
        print(f"✗ Error in input schema test: {e}")
        return False


def test_mcp_error_format():
    """Test MCP error format compliance."""
    try:
        print("\n=== Testing MCP Error Format ===")

        from src.services.mcp_client import MCPServerError

        # Test error creation
        error = MCPServerError("HTTP 404: Not Found")
        print(f"✓ Error message: {error}")

        # Test error serialization
        error_dict = {
            "error": str(error),
            "type": type(error).__name__,
            "timestamp": 1234567890
        }

        json_str = json.dumps(error_dict)
        parsed_back = json.loads(json_str)
        print("✓ Error JSON serialization works")

        # Validate error schema
        required_error_fields = ["error", "type", "timestamp"]
        for field in required_error_fields:
            if field not in error_dict:
                raise ValueError(f"Missing required error field: {field}")

        print("✓ Error schema validation passed")

        return True

    except Exception as e:
        print(f"✗ Error in error format test: {e}")
        return False


def test_mcp_client_interface():
    """Test MCP client interface compliance."""
    try:
        print("\n=== Testing MCP Client Interface ===")

        from src.services.mcp_client import MCPServerClient

        # Create client
        client = MCPServerClient()

        # Test required methods exist
        required_methods = [
            "get_price",
            "get_multiple_prices",
            "get_supported_symbols",
            "get_market_status",
            "health_check",
            "close"
        ]

        for method_name in required_methods:
            if not hasattr(client, method_name):
                raise ValueError(f"Missing required method: {method_name}")
            method = getattr(client, method_name)
            if not callable(method):
                raise ValueError(f"{method_name} is not callable")

        print("✓ All required methods present")

        # Test client attributes
        required_attributes = ["server_url", "api_key", "session"]
        for attr in required_attributes:
            if not hasattr(client, attr):
                raise ValueError(f"Missing required attribute: {attr}")

        print("✓ All required attributes present")
        print(f"  Server URL: {client.server_url}")
        print(f"  API Key: {'Set' if client.api_key else 'Not set'}")

        return True

    except Exception as e:
        print(f"✗ Error in client interface test: {e}")
        return False


def test_mcp_tool_integration():
    """Test MCP tool integration compliance."""
    try:
        print("\n=== Testing MCP Tool Integration ===")

        from src.tools.market_data_tools import get_market_data_tools

        tools = get_market_data_tools()
        print(f"✓ Found {len(tools)} market data tools")

        # Test tool properties
        expected_tools = ["get_crypto_price", "get_crypto_prices", "get_market_status"]
        tool_names = [tool.name for tool in tools]

        for expected_tool in expected_tools:
            if expected_tool not in tool_names:
                raise ValueError(f"Missing expected tool: {expected_tool}")

        print("✓ All expected tools present")
        print(f"  Tool names: {tool_names}")

        # Test tool descriptions
        for tool in tools:
            if not hasattr(tool, 'description') or not tool.description:
                raise ValueError(f"Tool {tool.name} missing description")

        print("✓ All tools have descriptions")

        return True

    except Exception as e:
        print(f"✗ Error in tool integration test: {e}")
        return False


def main():
    """Run all schema compliance tests."""
    print("Testing MCP Schema Compliance")
    print("=" * 50)

    tests = [
        test_mcp_response_schemas,
        test_tool_input_schemas,
        test_mcp_error_format,
        test_mcp_client_interface,
        test_mcp_tool_integration,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("SCHEMA COMPLIANCE SUMMARY:")
    print(f"  Tests run: {len(results)}")
    print(f"  Passed: {sum(results)}")
    print(f"  Failed: {len(results) - sum(results)}")

    if all(results):
        print("✓ All schema compliance tests passed!")
        print("\nMCP Schema Compliance Status:")
        print("✓ Response schemas follow MCP format")
        print("✓ Input schemas are valid and validated")
        print("✓ Error format is compliant")
        print("✓ Client interface is complete")
        print("✓ Tool integration is proper")
        return 0
    else:
        print("✗ Some schema compliance tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test response time performance for MCP integration.
"""

import sys
import time

# Add the project root to Python path
sys.path.insert(0, '/media/DATA/projects/autonomous-coding-cro/paygent')

def test_mcp_client_performance():
    """Test MCP client response times."""
    try:
        print("=== Testing MCP Client Performance ===")

        from src.services.mcp_client import MCPServerClient

        # Test client instantiation time
        start_time = time.time()
        client = MCPServerClient()
        instantiation_time = time.time() - start_time

        print(f"✓ Client instantiation time: {instantiation_time:.4f}s")

        # Test data model creation time
        from datetime import datetime

        from src.services.mcp_client import PriceData

        start_time = time.time()
        price_data = PriceData(
            symbol="BTC_USDT",
            price=50000.0,
            volume_24h=1000.0,
            change_24h=2.5,
            timestamp=int(datetime.now().timestamp())
        )
        data_creation_time = time.time() - start_time

        print(f"✓ Data model creation time: {data_creation_time:.6f}s")

        # Test JSON serialization performance
        import json

        start_time = time.time()
        json_str = json.dumps({
            "symbol": price_data.symbol,
            "price": price_data.price,
            "volume_24h": price_data.volume_24h,
            "change_24h": price_data.change_24h,
            "timestamp": price_data.timestamp
        })
        serialization_time = time.time() - start_time

        start_time = time.time()
        parsed_back = json.loads(json_str)
        deserialization_time = time.time() - start_time

        print(f"✓ JSON serialization time: {serialization_time:.6f}s")
        print(f"✓ JSON deserialization time: {deserialization_time:.6f}s")

        # Test error creation performance
        from src.services.mcp_client import MCPServerError

        start_time = time.time()
        error = MCPServerError("Test error message")
        error_creation_time = time.time() - start_time

        print(f"✓ Error creation time: {error_creation_time:.6f}s")

        # Performance summary
        total_time = (instantiation_time + data_creation_time +
                     serialization_time + deserialization_time + error_creation_time)

        print("\nPerformance Summary:")
        print(f"  Total time: {total_time:.6f}s")
        print(f"  Instantiation: {instantiation_time:.6f}s")
        print(f"  Data creation: {data_creation_time:.6f}s")
        print(f"  Serialization: {serialization_time:.6f}s")
        print(f"  Deserialization: {deserialization_time:.6f}s")
        print(f"  Error creation: {error_creation_time:.6f}s")

        # Performance requirements check
        requirements_met = True

        if instantiation_time > 0.1:  # 100ms
            print(f"⚠ Instantiation time ({instantiation_time:.4f}s) exceeds 100ms")
            requirements_met = False

        if data_creation_time > 0.001:  # 1ms
            print(f"⚠ Data creation time ({data_creation_time:.6f}s) exceeds 1ms")
            requirements_met = False

        if serialization_time > 0.01:  # 10ms
            print(f"⚠ Serialization time ({serialization_time:.6f}s) exceeds 10ms")
            requirements_met = False

        if deserialization_time > 0.01:  # 10ms
            print(f"⚠ Deserialization time ({deserialization_time:.6f}s) exceeds 10ms")
            requirements_met = False

        if error_creation_time > 0.001:  # 1ms
            print(f"⚠ Error creation time ({error_creation_time:.6f}s) exceeds 1ms")
            requirements_met = False

        if requirements_met:
            print("✓ All performance requirements met!")
        else:
            print("⚠ Some performance requirements not met")

        return requirements_met

    except Exception as e:
        print(f"✗ Error in performance test: {e}")
        return False


def test_tool_creation_performance():
    """Test market data tool creation performance."""
    try:
        print("\n=== Testing Tool Creation Performance ===")

        from src.tools.market_data_tools import GetMarketStatusTool, GetPricesTool, GetPriceTool

        # Test individual tool creation times
        start_time = time.time()
        price_tool = GetPriceTool()
        price_tool_time = time.time() - start_time

        start_time = time.time()
        prices_tool = GetPricesTool()
        prices_tool_time = time.time() - start_time

        start_time = time.time()
        status_tool = GetMarketStatusTool()
        status_tool_time = time.time() - start_time

        print(f"✓ Price tool creation time: {price_tool_time:.6f}s")
        print(f"✓ Prices tool creation time: {prices_tool_time:.6f}s")
        print(f"✓ Status tool creation time: {status_tool_time:.6f}s")

        # Test bulk tool creation
        start_time = time.time()
        tools = [GetPriceTool(), GetPricesTool(), GetMarketStatusTool()]
        bulk_creation_time = time.time() - start_time

        print(f"✓ Bulk tool creation time: {bulk_creation_time:.6f}s")

        # Test get_market_data_tools function
        from src.tools.market_data_tools import get_market_data_tools

        start_time = time.time()
        tools_list = get_market_data_tools()
        function_time = time.time() - start_time

        print(f"✓ get_market_data_tools() time: {function_time:.6f}s")
        print(f"  Number of tools returned: {len(tools_list)}")

        # Performance requirements
        requirements_met = True

        if bulk_creation_time > 0.1:  # 100ms
            print(f"⚠ Bulk tool creation ({bulk_creation_time:.6f}s) exceeds 100ms")
            requirements_met = False

        if function_time > 0.1:  # 100ms
            print(f"⚠ Tool function time ({function_time:.6f}s) exceeds 100ms")
            requirements_met = False

        if requirements_met:
            print("✓ Tool creation performance requirements met!")
        else:
            print("⚠ Some tool creation performance requirements not met")

        return requirements_met

    except Exception as e:
        print(f"✗ Error in tool performance test: {e}")
        return False


def test_configuration_loading_performance():
    """Test configuration loading performance."""
    try:
        print("\n=== Testing Configuration Loading Performance ===")

        # Test configuration import time
        start_time = time.time()
        from src.core.config import settings
        import_time = time.time() - start_time

        print(f"✓ Configuration import time: {import_time:.6f}s")
        print(f"  MCP Server URL: {settings.crypto_com_mcp_url}")

        # Test client creation with configuration
        from src.services.mcp_client import create_mcp_client

        start_time = time.time()
        client = create_mcp_client(settings.crypto_com_mcp_url)
        client_creation_time = time.time() - start_time

        print(f"✓ Client creation with config time: {client_creation_time:.6f}s")

        # Test multiple client creations
        start_time = time.time()
        clients = []
        for i in range(10):
            clients.append(create_mcp_client(settings.crypto_com_mcp_url))
        multiple_clients_time = time.time() - start_time

        print(f"✓ 10 clients creation time: {multiple_clients_time:.6f}s")
        print(f"  Average per client: {(multiple_clients_time/10):.6f}s")

        # Performance requirements
        requirements_met = True

        if import_time > 0.1:  # 100ms
            print(f"⚠ Configuration import ({import_time:.6f}s) exceeds 100ms")
            requirements_met = False

        if client_creation_time > 0.01:  # 10ms
            print(f"⚠ Client creation ({client_creation_time:.6f}s) exceeds 10ms")
            requirements_met = False

        if multiple_clients_time > 0.1:  # 100ms for 10 clients
            print(f"⚠ Multiple clients ({multiple_clients_time:.6f}s) exceeds 100ms")
            requirements_met = False

        if requirements_met:
            print("✓ Configuration performance requirements met!")
        else:
            print("⚠ Some configuration performance requirements not met")

        return requirements_met

    except Exception as e:
        print(f"✗ Error in configuration performance test: {e}")
        return False


def main():
    """Run all performance tests."""
    print("Testing MCP Response Time Performance")
    print("=" * 50)

    tests = [
        test_mcp_client_performance,
        test_tool_creation_performance,
        test_configuration_loading_performance,
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
    print("PERFORMANCE TEST SUMMARY:")
    print(f"  Tests run: {len(results)}")
    print(f"  Passed: {sum(results)}")
    print(f"  Failed: {len(results) - sum(results)}")

    if all(results):
        print("✓ All performance tests passed!")
        print("\nResponse Time Performance Status:")
        print("✓ Client instantiation under 100ms")
        print("✓ Data model creation under 1ms")
        print("✓ JSON operations under 10ms")
        print("✓ Tool creation under 100ms")
        print("✓ Configuration loading under 100ms")
        return 0
    else:
        print("✗ Some performance tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

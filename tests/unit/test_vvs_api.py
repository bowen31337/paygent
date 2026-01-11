#!/usr/bin/env python3
"""
API test script for VVS Trader Subagent functionality.

This script tests the VVS subagent through the API endpoint.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from uuid import uuid4

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_api_endpoint():
    """Test the agent execution API endpoint."""
    logger.info("🧪 Testing API endpoint for VVS subagent...")

    # Test different swap commands
    test_commands = [
        {
            "command": "Swap 100 USDC for CRO",
            "description": "Simple swap command",
            "should_trigger_vvs": True
        },
        {
            "command": "Exchange 50 CRO to USDC",
            "description": "Exchange command",
            "should_trigger_vvs": True
        },
        {
            "command": "Trade 200 USDC into CRO",
            "description": "Trade command",
            "should_trigger_vvs": True
        },
        {
            "command": "Check my wallet balance",
            "description": "Balance check (should not trigger VVS)",
            "should_trigger_vvs": False
        },
        {
            "command": "Pay 0.10 USDC to API service",
            "description": "Payment command (should not trigger VVS)",
            "should_trigger_vvs": False
        }
    ]

    # Try different ports where the server might be running
    for port in [8000, 8001, 8002, 8005, 8007]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test health endpoint first
                health_response = await client.get(f"http://localhost:{port}/health")
                if health_response.status_code == 200:
                    logger.info(f"✅ Found server on port {port}")
                    break
            break
        except (httpx.ConnectError, httpx.TimeoutException):
            logger.info(f"❌ No server on port {port}")
            continue
    else:
        logger.error("❌ No running server found on any port")
        return False

    results = []

    for test_case in test_commands:
        command = test_case["command"]
        should_trigger_vvs = test_case["should_trigger_vvs"]

        try:
            # Create a new session ID for each test
            session_id = str(uuid4())

            response = await client.post(
                f"http://localhost:{port}/api/v1/agent/execute",
                json={
                    "command": command,
                    "session_id": session_id,
                    "budget_limit_usd": 100.0
                }
            )

            if response.status_code == 200:
                result = response.json()

                # Check if VVS subagent was triggered
                action = result.get("result", {}).get("action", "")
                vvs_triggered = "vvs" in action.lower() or "subagent" in str(result).lower()

                status = "✅" if vvs_triggered == should_trigger_vvs else "❌"
                print(f"   {status} Command: '{command}'")
                print(f"      Should trigger VVS: {should_trigger_vvs}")
                print(f"      Actually triggered: {vvs_triggered}")
                print(f"      Action: {action}")
                print(f"      Success: {result.get('success', False)}")
                print()

                results.append({
                    "command": command,
                    "expected_vvs": should_trigger_vvs,
                    "actual_vvs": vvs_triggered,
                    "success": vvs_triggered == should_trigger_vvs,
                    "full_result": result
                })

            else:
                logger.error(f"❌ API call failed for '{command}': {response.status_code}")
                results.append({
                    "command": command,
                    "expected_vvs": should_trigger_vvs,
                    "actual_vvs": False,
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })

        except Exception as e:
            logger.error(f"❌ Exception for '{command}': {e}")
            results.append({
                "command": command,
                "expected_vvs": should_trigger_vvs,
                "actual_vvs": False,
                "success": False,
                "error": str(e)
            })

    return results


async def main():
    """Run API tests."""
    logger.info("🚀 Starting VVS Subagent API Tests")
    logger.info("=" * 50)

    results = await test_api_endpoint()

    if not results:
        logger.error("❌ No test results - server might not be running")
        return

    # Summary
    successful_tests = [r for r in results if r["success"]]
    failed_tests = [r for r in results if not r["success"]]

    print("=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Total tests: {len(results)}")
    print(f"   Successful: {len(successful_tests)}")
    print(f"   Failed: {len(failed_tests)}")

    if failed_tests:
        print("\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - '{test['command']}' (expected: {test['expected_vvs']}, got: {test['actual_vvs']})")

    if len(successful_tests) == len(results):
        print("\n🎉 All VVS subagent tests passed!")
        print("✅ Feature 20: Agent spawns VVS trader subagent for DeFi swap operations")
    else:
        print(f"\n⚠️  {len(failed_tests)} tests failed")


if __name__ == "__main__":
    asyncio.run(main())

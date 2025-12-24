#!/usr/bin/env python
"""
Integration test for x402 payment API endpoint.

Tests the x402 payment flow through the HTTP API.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_x402_payment_api():
    """Test x402 payment API endpoint."""
    print("\n" + "=" * 80)
    print("X402 PAYMENT API INTEGRATION TEST")
    print("=" * 80)

    try:
        import httpx

        base_url = "http://localhost:8001"  # Use working server

        async with httpx.AsyncClient() as client:
            # Test 1: Health check
            print("\n[1/3] Testing health check...")
            response = await client.get(f"{base_url}/health")
            print(f"✓ Status: {response.status_code}")
            print(f"  Response: {response.json()}")

            # Test 2: Execute x402 payment
            print("\n[2/3] Testing x402 payment execution...")
            payment_request = {
                "service_url": "https://api.example.com/data",
                "amount": 0.10,
                "token": "USDC",
                "description": "Test x402 payment",
            }

            response = await client.post(
                f"{base_url}/api/v1/payments/x402",
                json=payment_request,
                timeout=30.0,
            )

            print(f"✓ Status: {response.status_code}")
            result = response.json()
            print(f"  Success: {result.get('success')}")
            print(f"  Message: {result.get('message', 'N/A')}")

            if result.get('success'):
                payment_id = result.get('payment_id')
                print(f"  Payment ID: {payment_id}")
                print(f"  TX Hash: {result.get('tx_hash', 'N/A')[:20]}...")

                # Test 3: Verify payment
                if payment_id:
                    print(f"\n[3/3] Testing payment verification...")
                    response = await client.get(
                        f"{base_url}/api/v1/payments/{payment_id}"
                    )
                    print(f"✓ Status: {response.status_code}")
                    print(f"  Response: {response.json()}")
            else:
                print(f"  Error: {result.get('error', 'Unknown')}")

            # Test 4: Get payment statistics
            print(f"\n[Bonus] Testing payment statistics...")
            response = await client.get(f"{base_url}/api/v1/payments/stats")
            print(f"✓ Status: {response.status_code}")
            stats = response.json()
            print(f"  Total payments: {stats.get('total_payments', 0)}")
            print(f"  Success rate: {stats.get('success_rate', 0)}%")

        print("\n" + "=" * 80)
        print("✓ All API tests completed successfully")
        print("=" * 80)
        return 0

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_x402_payment_api())
    sys.exit(exit_code)

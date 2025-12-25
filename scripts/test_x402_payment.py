#!/usr/bin/env python
"""Test x402 payment flow end-to-end."""
import asyncio

import httpx


async def test_x402_payment_flow():
    """Test the x402 payment flow endpoint."""
    base = "http://localhost:8000"

    print("\n=== Testing x402 Payment Flow ===\n")

    async with httpx.AsyncClient() as client:
        # Test 1: Execute x402 payment with mock service
        print("1. Testing POST /api/v1/payments/x402 endpoint...")

        try:
            # Use a mock service URL that will trigger 402
            response = await client.post(
                f"{base}/api/v1/payments/x402",
                json={
                    "service_url": "https://httpbin.org/status/402",  # Returns 402
                    "amount": 0.10,
                    "token": "USDC"
                },
                timeout=30.0
            )

            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("   ✓ Payment initiated successfully")
                print(f"   Payment ID: {data.get('payment_id')}")
                print(f"   Status: {data.get('status')}")
                print(f"   TX Hash: {data.get('tx_hash')}")

                # Test 2: Verify payment was recorded
                print("\n2. Testing GET /api/v1/payments/history...")
                history_response = await client.get(f"{base}/api/v1/payments/history")
                print(f"   Status: {history_response.status_code}")

                if history_response.status_code == 200:
                    history = history_response.json()
                    print("   ✓ Payment history retrieved")
                    print(f"   Total payments: {history.get('total', 0)}")

                # Test 3: Get payment stats
                print("\n3. Testing GET /api/v1/payments/stats...")
                stats_response = await client.get(f"{base}/api/v1/payments/stats")
                print(f"   Status: {stats_response.status_code}")

                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    print("   ✓ Payment stats retrieved")
                    print(f"   Total payments: {stats.get('total_payments')}")
                    print(f"   Success rate: {stats.get('success_rate'):.1%}")

                return True
            else:
                print(f"   ✗ Failed: {response.text[:200]}")
                return False

        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False


async def main():
    """Run x402 payment tests."""
    success = await test_x402_payment_flow()

    print("\n=== SUMMARY ===")
    if success:
        print("✓ x402 payment flow tests PASSED")
        return 0
    else:
        print("✗ x402 payment flow tests FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

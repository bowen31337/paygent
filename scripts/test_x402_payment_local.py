#!/usr/bin/env python
"""Test x402 payment flow with local mock service."""
import asyncio
import subprocess

import httpx


async def test_x402_with_local_mock():
    """Test x402 payment with local mock service."""
    base = "http://localhost:8000"
    mock_service = "http://localhost:8001"

    print("\n=== Testing x402 Payment Flow with Local Mock ===\n")

    # Start mock service
    print("1. Starting mock x402 service...")
    mock_process = subprocess.Popen(
        ["uv", "run", "python", "scripts/mock_x402_service.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/media/DATA/projects/autonomous-cro/paygent"
    )

    # Wait for mock service to start
    print("   Waiting for mock service to start...")
    await asyncio.sleep(3)

    try:
        # Verify mock service is running
        print("\n2. Verifying mock service is running...")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{mock_service}/free", timeout=2.0)
                if resp.status_code == 200:
                    print("   ✓ Mock service is running")
                else:
                    print(f"   ✗ Mock service returned {resp.status_code}")
                    return False
        except Exception as e:
            print(f"   ✗ Mock service not accessible: {e}")
            return False

        # Test x402 payment
        print("\n3. Testing x402 payment flow...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base}/api/v1/payments/x402",
                json={
                    "service_url": f"{mock_service}/",
                    "amount": 0.10,
                    "token": "USDC"
                }
            )

            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("   ✓ Payment initiated successfully")
                print(f"   Payment ID: {data.get('payment_id')}")
                print(f"   Status: {data.get('status')}")

                if data.get('service_response'):
                    print(f"   Service Response: {data['service_response']}")

                return True
            else:
                print(f"   ✗ Failed: {response.text[:200]}")
                return False

    finally:
        # Cleanup: stop mock service
        print("\n4. Stopping mock service...")
        mock_process.terminate()
        mock_process.wait(timeout=5)
        print("   ✓ Mock service stopped")


async def main():
    """Run x402 payment tests."""
    try:
        success = await test_x402_with_local_mock()

        print("\n=== SUMMARY ===")
        if success:
            print("✓ x402 payment flow tests PASSED")
            return 0
        else:
            print("✗ x402 payment flow tests FAILED")
            return 1
    except KeyboardInterrupt:
        print("\n\nTests interrupted")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

#!/usr/bin/env python
"""
Simple x402 payment flow test without pytest.

This script tests the x402 payment implementation directly.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_signature_generation():
    """Test EIP-712 signature generation."""
    print("\n" + "=" * 80)
    print("TEST 1: EIP-712 Signature Generation")
    print("=" * 80)

    try:
        from src.x402.signature import EIP712SignatureGenerator

        # Use test private key
        test_private_key = "0x" + "1" * 64
        generator = EIP712SignatureGenerator(private_key=test_private_key)

        print("✓ Signature generator initialized")
        print(f"  Domain: {generator.domain['name']} v{generator.domain['version']}")
        print(f"  Chain ID: {generator.domain['chainId']}")

        # Create payment data
        payment_data = generator.create_payment_data(
            service_url="https://api.example.com/data",
            amount=0.10,
            token="USDC",
            wallet_address=generator.account.address,
            description="Test payment",
        )

        print("\n✓ Payment data created")
        print(f"  Service URL: {payment_data.service_url}")
        print(f"  Amount: {payment_data.amount} (scaled)")
        print(f"  Token: {payment_data.token}")
        print(f"  Nonce: {payment_data.nonce}")

        # Sign payment
        result = generator.sign_payment(payment_data)

        if result["success"]:
            print("\n✓ Payment signed successfully")
            print(f"  Signer: {result['signer']}")
            print(f"  Signature: {result['signature']['signature'][:20]}...")

            # Verify signature
            is_valid = generator.verify_signature(
                signature=result['signature']['signature'],
                message=result['signature']['message'],
                expected_address=generator.account.address,
            )

            if is_valid:
                print("\n✓ Signature verification passed")
            else:
                print("\n✗ Signature verification failed")
                return False
        else:
            print(f"\n✗ Payment signing failed: {result.get('error')}")
            return False

        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mock_facilitator():
    """Test mock facilitator."""
    print("\n" + "=" * 80)
    print("TEST 2: Mock Facilitator")
    print("=" * 80)

    try:
        from src.x402.mock_facilitator import MockX402Facilitator

        facilitator = MockX402Facilitator()
        print("✓ Mock facilitator initialized")

        # Create mock signature
        mock_signature = {
            "domain": {"name": "Paygent", "version": "1.0"},
            "message": {"amount": 100000},
            "signature": "0x" + "a" * 130,
        }

        # Submit payment
        result = await facilitator.submit_payment(
            service_url="https://api.example.com/data",
            amount=0.10,
            token="USDC",
            signature=mock_signature,
            description="Test payment",
        )

        if "paymentId" in result:
            print("\n✓ Payment submitted to mock facilitator")
            print(f"  Payment ID: {result['paymentId']}")
            print(f"  TX Hash: {result['txHash'][:20]}...")
            print(f"  Status: {result['status']}")

            # Verify payment
            payment_id = result['paymentId']
            verify_result = await facilitator.verify_payment(payment_id)

            if verify_result.get('verified'):
                print("\n✓ Payment verified successfully")
                print(f"  Status: {verify_result['status']}")
                return True
            else:
                print("\n✗ Payment verification failed")
                return False
        else:
            print(f"\n✗ Payment submission failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_x402_service():
    """Test x402 payment service."""
    print("\n" + "=" * 80)
    print("TEST 3: X402 Payment Service")
    print("=" * 80)

    try:
        from src.services.x402_service import X402PaymentService

        service = X402PaymentService()
        print("✓ X402 service initialized")
        print(f"  Facilitator URL: {service.facilitator_url or 'Mock mode'}")
        print(f"  Retry attempts: {service.retry_attempts}")

        # Test payment execution (will use mock facilitator)
        result = await service.execute_payment(
            service_url="https://api.example.com/data",
            amount=0.10,
            token="USDC",
            description="Test payment via x402 service",
        )

        print("\n✓ Payment execution completed")
        print(f"  Success: {result.get('success')}")
        print(f"  Message: {result.get('message', 'N/A')}")

        if result.get('success'):
            if result.get('payment_id'):
                print(f"  Payment ID: {result['payment_id']}")
            if result.get('tx_hash'):
                print(f"  TX Hash: {result['tx_hash'][:20]}...")

        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("X402 PAYMENT FLOW TEST SUITE")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("Signature Generation", await test_signature_generation()))
    results.append(("Mock Facilitator", await test_mock_facilitator()))
    results.append(("X402 Service", await test_x402_service()))

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

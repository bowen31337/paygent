#!/usr/bin/env python3
"""
Test script for x402 payment facilitator integration.
This tests Feature 370: x402 payment successfully integrates with Cronos Facilitator.
"""

import asyncio
import os
import sys
import traceback

# Add the project root to Python path
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

async def test_x402_facilitator_integration():
    """Test x402 payment facilitator integration functionality."""
    print("🧪 Testing x402 Payment Facilitator Integration (Feature 370)")
    print("=" * 60)

    try:
        # Import the x402 service
        from src.services.x402_service import X402PaymentService

        # Test 1: Create x402 payment service instance
        print("✅ Test 1: Creating x402 payment service instance")
        service = X402PaymentService()
        assert service is not None, "Service should be created successfully"
        print(f"   ✓ Service created with facilitator URL: {service.facilitator_url}")
        print(f"   ✓ Retry attempts: {service.retry_attempts}, delay: {service.retry_delay}s")

        # Test 2: Test mock facilitator integration
        print("\n✅ Test 2: Testing mock facilitator integration")
        from src.x402.mock_facilitator import get_mock_facilitator

        mock_facilitator = get_mock_facilitator()
        assert mock_facilitator is not None, "Mock facilitator should be available"
        print("   ✓ Mock facilitator service available")

        # Test 3: Test payment submission to mock facilitator
        print("\n✅ Test 3: Testing payment submission to mock facilitator")
        payment_result = await mock_facilitator.submit_payment(
            service_url="https://api.example.com/v1/data",
            amount=0.10,
            token="USDC",
            signature={
                "domain": {"name": "PaygentPayment", "version": "1.0", "chainId": 338},
                "types": {"Payment": []},
                "message": {
                    "serviceUrl": "https://api.example.com/v1/data",
                    "amount": 100000,
                    "token": "USDC",
                    "description": "",
                    "timestamp": 1640995200,
                    "nonce": 1,
                    "walletAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
                },
                "signature": "0x88794c3c7ac29e7c535d482821b8f15c5a53f57e98f5b8a6a76f39d2a795242261b",
                "signerAddress": "0xFCAd0B19bB29D4674531d6f115237E16AfCE377c"
            },
            description="Market data subscription"
        )

        assert "paymentId" in payment_result, "Payment result should contain paymentId"
        assert "txHash" in payment_result, "Payment result should contain txHash"
        assert "paymentProof" in payment_result, "Payment result should contain paymentProof"
        assert payment_result["status"] == "confirmed", "Payment should be confirmed"

        print("   ✓ Payment submitted successfully:")
        print(f"     - Payment ID: {payment_result['paymentId']}")
        print(f"     - TX Hash: {payment_result['txHash']}")
        print(f"     - Status: {payment_result['status']}")

        # Test 4: Test payment verification with mock facilitator
        print("\n✅ Test 4: Testing payment verification with mock facilitator")
        verify_result = await mock_facilitator.verify_payment(payment_result["paymentId"])

        assert verify_result is not None, "Verification result should not be None"
        assert verify_result["status"] == "confirmed", "Payment should be confirmed"
        assert verify_result["verified"] == True, "Payment should be marked as verified"

        print("   ✓ Payment verified successfully:")
        print(f"     - Status: {verify_result['status']}")
        print(f"     - Verified: {verify_result['verified']}")

        # Test 5: Test EIP-712 signature generation integration
        print("\n✅ Test 5: Testing EIP-712 signature generation integration")
        signature_result = await service._generate_eip712_signature(
            service_url="https://api.example.com/v1/data",
            amount=0.10,
            token="USDC",
            description="Market data subscription"
        )

        assert signature_result["success"] == True, "Signature generation should succeed"
        assert "signature" in signature_result, "Result should contain signature"
        assert "signer" in signature_result, "Result should contain signer"

        signature = signature_result["signature"]
        assert "domain" in signature, "Signature should contain domain"
        assert "types" in signature, "Signature should contain types"
        assert "message" in signature, "Signature should contain message"
        assert "signature" in signature, "Signature should contain signature"

        print("   ✓ EIP-712 signature generated successfully:")
        print(f"     - Signer: {signature['signerAddress']}")
        print(f"     - Domain: {signature['domain']['name']} v{signature['domain']['version']}")
        print(f"     - Service: {signature['message']['serviceUrl']}")

        # Test 6: Test retry logic configuration
        print("\n✅ Test 6: Testing retry logic configuration")
        assert service.retry_attempts == 3, "Default retry attempts should be 3"
        assert service.retry_delay == 1.0, "Default retry delay should be 1.0s"
        print(f"   ✓ Retry configuration: {service.retry_attempts} attempts, {service.retry_delay}s delay")

        # Test 7: Test payment required header parsing
        print("\n✅ Test 7: Testing Payment-Required header parsing")
        test_header = "x402; amount=0.10; token=USDC"
        parsed = service._parse_payment_required_header(test_header)

        assert "x402" in parsed, "Should parse x402 protocol"
        assert parsed["amount"] == "0.10", "Should parse amount correctly"
        assert parsed["token"] == "USDC", "Should parse token correctly"

        print(f"   ✓ Header parsed successfully: {parsed}")

        print("\n🎉 All x402 facilitator integration tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


async def test_facilitator_submission_flow():
    """Test the complete facilitator submission flow."""
    print("\n🔄 Testing Complete Facilitator Submission Flow")
    print("=" * 60)

    try:
        from src.services.x402_service import X402PaymentService
        from src.x402.mock_facilitator import get_mock_facilitator

        # Create service and mock facilitator
        service = X402PaymentService()
        mock_facilitator = get_mock_facilitator()

        # Test complete submission flow
        print("✅ Testing complete submission flow with mock facilitator")

        # This simulates the _submit_to_facilitator method
        result = await service._submit_to_facilitator(
            service_url="https://api.example.com/v1/data",
            amount=0.10,
            token="USDC",
            signature={
                "domain": {"name": "PaygentPayment", "version": "1.0", "chainId": 338},
                "types": {"Payment": []},
                "message": {
                    "serviceUrl": "https://api.example.com/v1/data",
                    "amount": 100000,
                    "token": "USDC",
                    "description": "",
                    "timestamp": 1640995200,
                    "nonce": 1,
                    "walletAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
                },
                "signature": "0x88794c3c7ac29e7c535d482821b8f15c5a53f57e98f5b8a6a76f39d2a795242261b",
                "signerAddress": "0xFCAd0B19bB29D4674531d6f115237E16AfCE377c"
            },
            description="Market data subscription"
        )

        assert result["success"] == True, "Facilitator submission should succeed"
        assert "payment_id" in result, "Result should contain payment_id"
        assert "tx_hash" in result, "Result should contain tx_hash"
        assert "payment_proof" in result, "Result should contain payment_proof"

        print("   ✓ Complete submission flow successful:")
        print(f"     - Payment ID: {result['payment_id']}")
        print(f"     - TX Hash: {result['tx_hash']}")
        print(f"     - Payment Proof: {result['payment_proof'][:20]}...")

        return True

    except Exception as e:
        print(f"\n❌ Submission flow test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    print("🚀 Starting x402 Facilitator Integration Tests")
    print("=" * 60)

    # Run synchronous tests
    success1 = asyncio.run(test_x402_facilitator_integration())

    # Run async submission flow test
    success2 = asyncio.run(test_facilitator_submission_flow())

    if success1 and success2:
        print("\n" + "=" * 60)
        print("🎯 Feature 370: x402 payment facilitator integration - TEST PASSED")
        print("✅ All tests completed successfully")
        print("✅ Mock facilitator integration working correctly")
        print("✅ Payment submission and verification flow tested")
        print("✅ Ready for QA verification")
    else:
        print("\n" + "=" * 60)
        print("❌ Feature 370: x402 payment facilitator integration - TEST FAILED")
        print("❌ Implementation needs fixes")
        sys.exit(1)

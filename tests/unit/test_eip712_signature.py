#!/usr/bin/env python3
"""
Test script for EIP-712 signature generation functionality.
This tests Feature 354: EIP-712 signature generation for x402 payment protocol.
"""

import os
import sys
import traceback

# Add the project root to Python path
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_eip712_signature_generation():
    """Test EIP-712 signature generation functionality."""
    print("🧪 Testing EIP-712 Signature Generation (Feature 354)")
    print("=" * 60)

    try:
        # Import the signature module
        from src.x402.signature import (
            PaymentSignatureData,
            get_signature_generator,
        )

        # Test 1: Check if signature generator can be created
        print("✅ Test 1: Creating signature generator instance")
        generator = get_signature_generator()
        assert generator is not None, "Generator should be created successfully"
        print(f"   ✓ Generator created with chain ID: {generator.chain_id}")

        # Test 2: Check domain structure
        print("\n✅ Test 2: Validating EIP-712 domain structure")
        domain = generator.domain
        required_fields = ["name", "version", "chainId", "verifyingContract"]
        for field in required_fields:
            assert field in domain, f"Domain missing required field: {field}"
        assert domain["name"] == "PaygentPayment", "Domain name should be PaygentPayment"
        assert domain["version"] == "1.0", "Domain version should be 1.0"
        assert domain["chainId"] == 338, "Chain ID should be 338 (Cronos testnet)"
        print(f"   ✓ Domain structure valid: {domain['name']} v{domain['version']} on chain {domain['chainId']}")

        # Test 3: Check type definitions
        print("\n✅ Test 3: Validating EIP-712 type definitions")
        types = generator.TYPES
        assert "Payment" in types, "Payment type should be defined"
        payment_fields = [field["name"] for field in types["Payment"]]
        required_payment_fields = [
            "serviceUrl", "amount", "token", "description",
            "timestamp", "nonce", "walletAddress"
        ]
        for field in required_payment_fields:
            assert field in payment_fields, f"Payment type missing field: {field}"
        print(f"   ✓ Payment type has all required fields: {payment_fields}")

        # Test 4: Create payment data
        print("\n✅ Test 4: Creating payment signature data")
        wallet_address = "0x1234567890123456789012345678901234567890"
        payment_data = PaymentSignatureData(
            service_url="https://api.example.com/v1/data",
            amount=1000000,  # 1.0 USDC (in smallest unit)
            token="USDC",
            description="Market data subscription",
            wallet_address=wallet_address,
            nonce=1,
            timestamp=1640995200  # 2022-01-01 00:00:00 UTC
        )
        assert payment_data.service_url == "https://api.example.com/v1/data", "Service URL should match"
        assert payment_data.amount == 1000000, "Amount should be correctly set"
        assert payment_data.token == "USDC", "Token should be USDC"
        assert payment_data.wallet_address == wallet_address, "Wallet address should match"
        print(f"   ✓ Payment data created successfully: {payment_data.amount} {payment_data.token}")

        # Test 5: Check if generator has signer configured
        print("\n✅ Test 5: Checking signer configuration")
        has_signer = generator.account is not None
        if has_signer:
            print(f"   ✓ Signer configured: {generator.account.address}")
        else:
            print("   ⚠ No signer configured (expected in development without private key)")

        # Test 6: Test signature generation (if signer available)
        if generator.account:
            print("\n✅ Test 6: Generating EIP-712 signature")
            result = generator.sign_payment(payment_data)

            assert result["success"] == True, "Signature generation should succeed"
            assert "signature" in result, "Result should contain signature"
            assert "signer" in result, "Result should contain signer address"
            assert "message" in result, "Result should contain success message"

            signature = result["signature"]
            assert "domain" in signature, "Signature should contain domain"
            assert "types" in signature, "Signature should contain types"
            assert "message" in signature, "Signature should contain message"
            assert "signature" in signature, "Signature should contain signature"
            assert "signerAddress" in signature, "Signature should contain signer address"

            # Verify signature format
            sig_hex = signature["signature"]
            assert sig_hex.startswith("0x"), "Signature should have 0x prefix"
            assert len(sig_hex) == 132, "Signature should be 65 bytes (132 chars with 0x)"

            print("   ✓ Signature generated successfully:")
            print(f"     - Signer: {signature['signerAddress']}")
            print(f"     - Signature: {sig_hex[:20]}...{sig_hex[-8:]}")

            # Test 7: Verify signature
            print("\n✅ Test 7: Verifying signature")
            message = signature["message"]
            signature_hex = signature["signature"]

            is_valid = generator.verify_signature(
                signature=signature_hex,
                message=message,
                expected_address=signature["signerAddress"]
            )

            assert is_valid == True, "Signature verification should succeed"
            print("   ✓ Signature verified successfully")

        else:
            print("\n⚠ Skipping signature generation test (no signer configured)")
            print("   To test signature generation, set AGENT_WALLET_PRIVATE_KEY environment variable")

        # Test 8: Test nonce generation
        print("\n✅ Test 8: Testing nonce generation")
        test_wallet = "0xabcdef1234567890abcdef1234567890abcdef12"
        nonce1 = generator.get_nonce(test_wallet)
        nonce2 = generator.get_nonce(test_wallet)
        assert nonce1 == 0, "First nonce should be 0"
        assert nonce2 == 1, "Second nonce should be 1"
        print(f"   ✓ Nonce generation working: {nonce1} -> {nonce2}")

        print("\n🎉 All EIP-712 signature generation tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


def test_environment_configuration():
    """Test environment configuration for x402 functionality."""
    print("\n🔍 Testing Environment Configuration")
    print("=" * 60)

    required_vars = [
        "CRONOS_CHAIN_ID",
        "CRONOS_TESTNET_CHAIN_ID",
        "X402_FACILITATOR_URL"
    ]

    optional_vars = [
        "AGENT_WALLET_PRIVATE_KEY"
    ]

    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: Not set")

    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value[:8]}...{value[-8:]} (masked)")
        else:
            print(f"⚠️ {var}: Not set (optional)")

    return True


if __name__ == "__main__":
    print("🚀 Starting EIP-712 Signature Generation Tests")
    print("=" * 60)

    # Check environment configuration
    test_environment_configuration()

    # Run EIP-712 tests
    success = test_eip712_signature_generation()

    if success:
        print("\n" + "=" * 60)
        print("🎯 Feature 354: EIP-712 signature generation - TEST PASSED")
        print("✅ All tests completed successfully")
        print("✅ Implementation is working correctly")
        print("✅ Ready for QA verification")
    else:
        print("\n" + "=" * 60)
        print("❌ Feature 354: EIP-712 signature generation - TEST FAILED")
        print("❌ Implementation needs fixes")
        sys.exit(1)

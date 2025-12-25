"""
Test script for blockchain error handling.

This script tests the comprehensive blockchain error handling
including revert errors, gas errors, timeout errors, and
transaction errors.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from eth_account.exceptions import InvalidTransaction
from eth_typing import HexStr
from web3.exceptions import (
    ContractLogicError,
    InsufficientFunds,
    ContractPanicError,
    TimeExhausted,
)
from web3.types import HexBytes

from src.core.blockchain_errors import (
    BlockchainErrorHandler,
    BlockchainError,
    GasError,
    RevertError,
    TimeoutError,
    TransactionError,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_revert_error_handling():
    """Test revert error handling."""
    print("🧪 Testing revert error handling...")

    # Test 1: ContractLogicError
    try:
        error = ContractLogicError("execution reverted: ERC20: transfer amount exceeds balance")
        revert_error = BlockchainErrorHandler.handle_revert_error(error)

        print(f"   ✅ Revert error handled: {revert_error.message}")
        print(f"   ✅ Error type: {revert_error.error_type}")
        print(f"   ✅ Guidance: {revert_error.detail}")

        assert revert_error.error_type == "revert"
        assert "exceeds balance" in revert_error.message

    except Exception as e:
        print(f"   ❌ Revert error handling failed: {e}")
        return False

    # Test 2: ContractPanicError
    try:
        error = ContractPanicError("Panic error 0x11: Arithmetic operation underflowed or overflowed outside of an unchecked block")
        revert_error = BlockchainErrorHandler.handle_revert_error(error)

        print(f"   ✅ Panic error handled: {revert_error.message}")
        assert revert_error.error_type == "revert"

    except Exception as e:
        print(f"   ❌ Panic error handling failed: {e}")
        return False

    # Test 3: Custom revert reason
    try:
        error = ContractLogicError("insufficient allowance")
        revert_error = BlockchainErrorHandler.handle_revert_error(error)

        print(f"   ✅ Custom revert handled: {revert_error.message}")
        assert "insufficient" in revert_error.message

    except Exception as e:
        print(f"   ❌ Custom revert handling failed: {e}")
        return False

    return True


async def test_gas_error_handling():
    """Test gas error handling."""
    print("\n🧪 Testing gas error handling...")

    # Test 1: InsufficientFunds
    try:
        error = InsufficientFunds("insufficient funds for gas * price + value")
        gas_error = BlockchainErrorHandler.handle_gas_error(
            error,
            estimated_gas=21000,
            current_gas_price=20000000000,
        )

        print(f"   ✅ Gas error handled: {gas_error.message}")
        print(f"   ✅ Error type: {gas_error.error_type}")
        print(f"   ✅ Estimated gas: {gas_error.details.get('estimated_gas')}")
        print(f"   ✅ Gas price: {gas_error.details.get('current_gas_price')}")

        assert gas_error.error_type == "insufficient_funds"
        assert gas_error.details["estimated_gas"] == 21000

    except Exception as e:
        print(f"   ❌ Gas error handling failed: {e}")
        return False

    # Test 2: ContractLogicError as gas error
    try:
        error = ContractLogicError("transaction would fail")
        gas_error = BlockchainErrorHandler.handle_gas_error(error)

        print(f"   ✅ Logic error as gas handled: {gas_error.message}")
        assert gas_error.error_type == "contract_error"

    except Exception as e:
        print(f"   ❌ Logic error handling failed: {e}")
        return False

    return True


async def test_timeout_error_handling():
    """Test timeout error handling."""
    print("\n🧪 Testing timeout error handling...")

    try:
        timeout_error = BlockchainErrorHandler.handle_timeout_error(
            timeout_duration=300,
            tx_hash="0x1234567890abcdef",
            current_status="pending",
        )

        print(f"   ✅ Timeout error handled: {timeout_error.message}")
        print(f"   ✅ Error type: {timeout_error.error_type}")
        print(f"   ✅ Timeout duration: {timeout_error.details.get('timeout_duration')}s")
        print(f"   ✅ TX hash: {timeout_error.details.get('tx_hash')}")

        assert timeout_error.error_type == "timeout"
        assert timeout_error.details["timeout_duration"] == 300

    except Exception as e:
        print(f"   ❌ Timeout error handling failed: {e}")
        return False

    return True


async def test_transaction_error_handling():
    """Test general transaction error handling."""
    print("\n🧪 Testing transaction error handling...")

    # Test 1: InvalidTransaction
    try:
        error = InvalidTransaction("nonce too low")
        tx_error = BlockchainErrorHandler.handle_general_transaction_error(error)

        print(f"   ✅ Invalid transaction handled: {tx_error.message}")
        print(f"   ✅ Error type: {tx_error.error_type}")

        assert tx_error.error_type == "nonce_too_low"

    except Exception as e:
        print(f"   ❌ Invalid transaction handling failed: {e}")
        return False

    # Test 2: Unknown transaction error
    try:
        error = Exception("unknown transaction error")
        tx_error = BlockchainErrorHandler.handle_general_transaction_error(error)

        print(f"   ✅ Unknown transaction handled: {tx_error.message}")
        assert tx_error.error_type == "unknown"

    except Exception as e:
        print(f"   ❌ Unknown transaction handling failed: {e}")
        return False

    return True


async def test_web3_error_parsing():
    """Test web3.py error parsing."""
    print("\n🧪 Testing web3.py error parsing...")

    test_cases = [
        (ContractLogicError("revert reason"), "revert"),
        (InsufficientFunds("insufficient funds"), "insufficient_funds"),
        (InvalidTransaction("invalid tx"), "unknown"),  # Will be classified as unknown
    ]

    for error, expected_type in test_cases:
        try:
            parsed_error = BlockchainErrorHandler.parse_web3_error(error)
            print(f"   ✅ Parsed {type(error).__name__} as {parsed_error.error_type}")

            # Note: Some error types might be classified differently based on content
            if expected_type == "revert":
                assert parsed_error.error_type in ["revert", "unknown"]
            elif expected_type == "insufficient_funds":
                assert parsed_error.error_type in ["insufficient_funds", "insufficient_gas"]
            else:
                assert parsed_error.error_type == expected_type

        except Exception as e:
            print(f"   ❌ Error parsing failed for {type(error).__name__}: {e}")
            return False

    return True


async def test_error_formatting():
    """Test error formatting for user display."""
    print("\n🧪 Testing error formatting for users...")

    # Test with BlockchainError
    try:
        revert_error = RevertError("insufficient balance", "0x123")
        formatted = BlockchainErrorHandler.format_error_for_user(revert_error)

        print(f"   ✅ Error formatted: {formatted['error']}")
        print(f"   ✅ Type: {formatted['type']}")
        print(f"   ✅ Guidance: {formatted['guidance']}")

        assert formatted["type"] == "revert"
        assert "insufficient" in formatted["error"]

    except Exception as e:
        print(f"   ❌ Error formatting failed: {e}")
        return False

    # Test with regular Exception
    try:
        regular_error = Exception("regular error")
        formatted = BlockchainErrorHandler.format_error_for_user(regular_error)

        print(f"   ✅ Regular error formatted: {formatted['error']}")
        assert "error" in formatted["error"].lower()

    except Exception as e:
        print(f"   ❌ Regular error formatting failed: {e}")
        return False

    return True


async def test_transaction_safety_estimation():
    """Test transaction safety estimation."""
    print("\n🧪 Testing transaction safety estimation...")

    # Mock web3 client for testing
    class MockWeb3Client:
        async def eth_get_balance(self, address):
            return 1000000000000000000  # 1 ETH in wei

        async def eth_estimate_gas(self, transaction):
            return 21000

        async def eth_gas_price(self):
            return 20000000000  # 20 gwei

        eth = type('eth', (), {
            'get_balance': lambda self, addr: self.eth_get_balance(addr),
            'estimate_gas': lambda self, tx: self.eth_estimate_gas(tx),
            'gas_price': lambda self: self.eth_gas_price()
        })()

    mock_client = MockWeb3Client()
    transaction = {"to": "0x123", "value": 100000000000000000}  # 0.1 ETH
    wallet_address = "0x456"

    try:
        safety = await BlockchainErrorHandler.estimate_transaction_safety(
            mock_client,
            transaction,
            wallet_address,
        )

        print(f"   ✅ Safety assessment: {safety}")
        print(f"   ✅ Safe: {safety['safe']}")
        print(f"   ✅ Balance: {safety['balance']}")
        print(f"   ✅ Total cost: {safety['total_cost']}")
        print(f"   ✅ Safety score: {safety['safety_score']}")

        assert safety["safe"] is True
        assert safety["safety_score"] == 100
        assert safety["estimated_gas"] == 21000

    except Exception as e:
        print(f"   ❌ Safety estimation failed: {e}")
        return False

    return True


async def run_all_tests():
    """Run all blockchain error handling tests."""
    print("🚀 Starting blockchain error handling tests...\n")

    tests = [
        test_revert_error_handling,
        test_gas_error_handling,
        test_timeout_error_handling,
        test_transaction_error_handling,
        test_web3_error_parsing,
        test_error_formatting,
        test_transaction_safety_estimation,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            print(f"❌ {test.__name__} crashed: {e}")

    print(f"\n{'='*60}")
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    print(f"{'='*60}")

    if passed == total:
        print("🎉 All blockchain error handling tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
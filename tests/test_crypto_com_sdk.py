"""Test Crypto.com AI Agent SDK integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.crypto_com_sdk import (
    CryptoComAgentSDK,
    CryptoComAgentSDKError,
    get_crypto_com_sdk,
    create_crypto_com_sdk,
)


def test_crypto_com_sdk_initialization():
    """Test Crypto.com Agent SDK initialization."""
    # Test with API key from settings
    sdk = CryptoComAgentSDK()

    assert sdk.api_key is not None
    assert sdk.base_url == "https://api.crypto.com/ai-agent"
    assert sdk.wallet_address is not None


def test_crypto_com_sdk_initialization_with_api_key():
    """Test Crypto.com Agent SDK initialization with custom API key."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    assert sdk.api_key == "test-api-key"
    assert sdk.base_url == "https://api.crypto.com/ai-agent"


def test_crypto_com_sdk_initialization_without_api_key():
    """Test Crypto.com Agent SDK initialization without API key."""
    with patch('src.services.crypto_com_sdk.settings.crypto_com_api_key', None):
        with pytest.raises(CryptoComAgentSDKError, match="Crypto.com API key is required"):
            CryptoComAgentSDK()


@pytest.mark.asyncio
async def test_check_balance():
    """Test balance checking functionality."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.check_balance(["CRO", "USDC"])

    assert "CRO" in result
    assert "USDC" in result
    assert result["CRO"]["token"] == "CRO"
    assert result["USDC"]["token"] == "USDC"
    assert "balance" in result["CRO"]
    assert "usd_value" in result["CRO"]


@pytest.mark.asyncio
async def test_check_balance_default_tokens():
    """Test balance checking with default tokens."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.check_balance()

    assert "CRO" in result
    assert "USDC" in result


@pytest.mark.asyncio
async def test_transfer():
    """Test token transfer functionality."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.transfer(
        recipient_address="0x1234567890abcdef",
        amount=10.0,
        token="CRO",
        description="Test transfer"
    )

    assert result["success"] is True
    assert result["amount"] == 10.0
    assert result["token"] == "CRO"
    assert result["recipient"] == "0x1234567890abcdef"
    assert result["status"] == "completed"
    assert "tx_hash" in result


@pytest.mark.asyncio
async def test_transfer_validation():
    """Test transfer validation."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    # Test missing recipient
    with pytest.raises(CryptoComAgentSDKError, match="Recipient address is required"):
        await sdk.transfer(
            recipient_address="",
            amount=10.0,
            token="CRO"
        )

    # Test invalid amount
    with pytest.raises(CryptoComAgentSDKError, match="Transfer amount must be positive"):
        await sdk.transfer(
            recipient_address="0x1234567890abcdef",
            amount=-10.0,
            token="CRO"
        )

    # Test missing token
    with pytest.raises(CryptoComAgentSDKError, match="Token symbol is required"):
        await sdk.transfer(
            recipient_address="0x1234567890abcdef",
            amount=10.0,
            token=""
        )


@pytest.mark.asyncio
async def test_get_transaction_history():
    """Test transaction history retrieval."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.get_transaction_history(limit=10)

    assert isinstance(result, list)
    assert len(result) == 10

    # Check transaction structure
    tx = result[0]
    assert "tx_hash" in tx
    assert "amount" in tx
    assert "token" in tx
    assert "type" in tx
    assert "status" in tx
    assert "timestamp" in tx


@pytest.mark.asyncio
async def test_get_transaction_history_with_token_filter():
    """Test transaction history with token filter."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.get_transaction_history(limit=5, token="CRO")

    assert isinstance(result, list)
    assert len(result) == 5


@pytest.mark.asyncio
async def test_check_spending_limit():
    """Test spending limit checking."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.check_spending_limit("USDC")

    assert "token" in result
    assert "daily_limit" in result
    assert "daily_spent" in result
    assert "remaining" in result
    assert "spending_percentage" in result
    assert "status" in result


@pytest.mark.asyncio
async def test_set_spending_limit():
    """Test spending limit setting."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.set_spending_limit(daily_limit=500.0, token="USDC")

    assert result["success"] is True
    assert result["token"] == "USDC"
    assert result["new_limit"] == 500.0
    assert result["status"] == "limit_updated"


@pytest.mark.asyncio
async def test_set_spending_limit_validation():
    """Test spending limit setting validation."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    with pytest.raises(CryptoComAgentSDKError, match="Daily limit must be positive"):
        await sdk.set_spending_limit(daily_limit=-100.0)


@pytest.mark.asyncio
async def test_get_wallet_info():
    """Test wallet information retrieval."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.get_wallet_info()

    assert "wallet_address" in result
    assert "network" in result
    assert "total_usd_value" in result
    assert "tokens_supported" in result
    assert "features" in result
    assert "status" in result


@pytest.mark.asyncio
async def test_health_check():
    """Test health check functionality."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.health_check()

    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_crypto_com_sdk_error_handling():
    """Test error handling in Crypto.com Agent SDK."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    # Mock an error in balance check
    with patch('src.services.crypto_com_sdk.aiohttp', side_effect=Exception("Network error")):
        with pytest.raises(CryptoComAgentSDKError):
            await sdk.check_balance(["CRO"])


def test_get_crypto_com_sdk_singleton():
    """Test that get_crypto_com_sdk returns singleton instance."""
    sdk1 = get_crypto_com_sdk()
    sdk2 = get_crypto_com_sdk()

    assert sdk1 is sdk2


def test_create_crypto_com_sdk():
    """Test creating new Crypto.com Agent SDK instance."""
    sdk = create_crypto_com_sdk(api_key="test-api-key")

    assert isinstance(sdk, CryptoComAgentSDK)
    assert sdk.api_key == "test-api-key"


@pytest.mark.asyncio
async def test_transfer_with_description():
    """Test transfer with description."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.transfer(
        recipient_address="0x1234567890abcdef",
        amount=5.0,
        token="USDC",
        description="Payment for services"
    )

    assert result["description"] == "Payment for services"


@pytest.mark.asyncio
async def test_check_spending_limit_default_token():
    """Test spending limit check with default token."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.check_spending_limit()

    assert result["token"] == "USDC"  # Default token


@pytest.mark.asyncio
async def test_wallet_features():
    """Test wallet features in wallet info."""
    sdk = CryptoComAgentSDK(api_key="test-api-key")

    result = await sdk.get_wallet_info()

    features = result["features"]
    assert features["spending_limits"] is True
    assert features["transaction_history"] is True
    assert features["real_time_balances"] is True
    assert features["transfer_approval"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
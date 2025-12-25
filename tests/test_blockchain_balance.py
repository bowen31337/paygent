"""Test blockchain balance checking using web3.py.

Tests that the wallet service can check actual blockchain balances
and falls back to mock data on failure.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_check_balance_with_web3():
    """Test checking balance using web3.py."""
    # Mock database
    mock_db = AsyncMock()

    from src.services.wallet_service import WalletService

    service = WalletService(mock_db)

    # Mock web3 connection
    with patch('src.services.wallet_service.Web3') as mock_web3:
        # Setup mocks
        mock_w3_instance = MagicMock()
        mock_web3.return_value = mock_w3_instance
        mock_w3_instance.is_connected.return_value = True
        mock_w3_instance.eth.get_balance.return_value = 1000000000000000000000  # 1000 CRO
        mock_w3_instance.from_wei.return_value = 1000.0

        # Mock ERC20 contract
        mock_contract = MagicMock()
        mock_contract.functions.balanceOf.return_value.call.return_value = 100000000  # 100 USDC (6 decimals)
        mock_contract.functions.decimals.return_value.call.return_value = 6
        mock_w3_instance.eth.contract.return_value = mock_contract
        mock_w3_instance.to_checksum_address.side_effect = lambda x: x

        # Check balances
        result = await service.check_balance(tokens=["CRO", "USDC"])

        assert result["success"] is True
        assert len(result["balances"]) == 2
        assert result["balances"][0]["token_symbol"] in ["CRO", "USDC"]
        assert result["balances"][0]["balance"] >= 0


@pytest.mark.asyncio
async def test_check_balance_fallback_on_web3_failure():
    """Test that check_balance falls back to mock when web3 fails."""
    mock_db = AsyncMock()
    from src.services.wallet_service import WalletService

    service = WalletService(mock_db)

    # Mock web3 connection failure
    with patch('src.services.wallet_service.Web3') as mock_web3:
        mock_w3_instance = MagicMock()
        mock_web3.return_value = mock_w3_instance
        mock_w3_instance.is_connected.return_value = False

        # Should fall back to mock balances
        result = await service.check_balance(tokens=["CRO", "USDC"])

        assert result["success"] is True
        assert len(result["balances"]) == 2
        # Mock balances should be present
        assert any(b["balance"] > 0 for b in result["balances"])


@pytest.mark.asyncio
async def test_check_balance_handles_exceptions():
    """Test that check_balance handles exceptions gracefully."""
    mock_db = AsyncMock()
    from src.services.wallet_service import WalletService

    service = WalletService(mock_db)

    # Mock web3 to raise exception
    with patch('src.services.wallet_service.Web3', side_effect=Exception("Connection error")):
        # Should fall back to mock balances
        result = await service.check_balance(tokens=["USDC"])

        assert result["success"] is True
        assert len(result["balances"]) == 1


@pytest.mark.asyncio
async def test_get_native_token_balance():
    """Test checking native CRO balance."""
    mock_db = AsyncMock()
    from src.services.wallet_service import WalletService

    service = WalletService(mock_db, wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")

    # Mock web3 for native token balance
    with patch('src.services.wallet_service.Web3') as mock_web3:
        mock_w3_instance = MagicMock()
        mock_web3.return_value = mock_w3_instance
        mock_w3_instance.is_connected.return_value = True
        mock_w3_instance.eth.get_balance.return_value = 50000000000000000000  # 50 CRO
        mock_w3_instance.from_wei.return_value = 50.0
        mock_w3_instance.to_checksum_address.side_effect = lambda x: x

        result = await service.check_balance(tokens=["CRO"])

        assert result["success"] is True
        assert result["balances"][0]["token_symbol"] == "CRO"
        assert result["balances"][0]["balance"] == 50.0


@pytest.mark.asyncio
async def test_get_erc20_token_balance():
    """Test checking ERC20 token balance."""
    mock_db = AsyncMock()
    from src.services.wallet_service import WalletService

    service = WalletService(mock_db, wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")

    # Mock web3 for ERC20 token
    with patch('src.services.wallet_service.Web3') as mock_web3:
        mock_w3_instance = MagicMock()
        mock_web3.return_value = mock_w3_instance
        mock_w3_instance.is_connected.return_value = True
        mock_w3_instance.to_checksum_address.side_effect = lambda x: x

        # Mock contract
        mock_contract = MagicMock()
        mock_contract.functions.balanceOf.return_value.call.return_value = 50000000  # 50 USDC
        mock_contract.functions.decimals.return_value.call.return_value = 6
        mock_w3_instance.eth.contract.return_value = mock_contract

        result = await service.check_balance(tokens=["USDC"])

        assert result["success"] is True
        assert result["balances"][0]["token_symbol"] == "USDC"
        assert result["balances"][0]["balance"] == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

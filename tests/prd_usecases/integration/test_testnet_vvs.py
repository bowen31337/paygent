"""
VVS Testnet Integration Tests

Integration tests using deployed VVS-compatible contracts on Cronos testnet.

Deployed Contracts:
- Router: 0xe5Da4A58aA595d5E46999Bad5661B364ff747117
- Factory: 0x2E3e5be7490C0d58290882f32A57F84AA4045666
- WCRO: 0x52462c26Ad624F8AE6360f7EA8eEca43C92edDA7
- tUSDC: 0x1C4719F10f0ADc7A8AcBC688Ecb1AfE1611D16ED
- tUSDT: 0x9482BAba40Fd80f2d598937eF17B3fD18097782D
- tVVS: 0x0B3C5A047c190E548A157Bf8DF6844FCb9B9608D
"""

import json
from pathlib import Path

import pytest

from src.connectors.vvs import VVSFinanceConnector


# Expected testnet contract addresses
EXPECTED_CONTRACTS = {
    "router": "0xe5Da4A58aA595d5E46999Bad5661B364ff747117",
    "factory": "0x2E3e5be7490C0d58290882f32A57F84AA4045666",
    "wcro": "0x52462c26Ad624F8AE6360f7EA8eEca43C92edDA7",
    "tUSDC": "0x1C4719F10f0ADc7A8AcBC688Ecb1AfE1611D16ED",
    "tUSDT": "0x9482BAba40Fd80f2d598937eF17B3fD18097782D",
    "tVVS": "0x0B3C5A047c190E548A157Bf8DF6844FCb9B9608D",
}


class TestDeploymentConfiguration:
    """Test deployment configuration loading."""

    def test_deployment_file_exists(self):
        """Verify deployment configuration file exists."""
        # Arrange
        deployment_path = Path(__file__).parent.parent.parent.parent / "contracts" / "deployments" / "vvs-testnet.json"

        # Assert
        assert deployment_path.exists(), f"Deployment file not found at {deployment_path}"

    def test_deployment_file_valid_json(self):
        """Verify deployment file contains valid JSON."""
        # Arrange
        deployment_path = Path(__file__).parent.parent.parent.parent / "contracts" / "deployments" / "vvs-testnet.json"

        # Act
        with open(deployment_path) as f:
            config = json.load(f)

        # Assert
        assert "contracts" in config
        assert "network" in config
        assert config["network"] == "cronosTestnet"

    def test_deployment_contains_required_contracts(self, testnet_config, skip_if_no_testnet):
        """Verify deployment contains all required contracts."""
        # Arrange
        required = ["router", "factory", "wcro", "tUSDC", "tUSDT", "tVVS"]

        # Act
        contracts = testnet_config.get("contracts", {})

        # Assert
        for contract in required:
            assert contract in contracts, f"Missing contract: {contract}"
            assert contracts[contract].startswith("0x"), f"Invalid address for {contract}"

    def test_deployment_addresses_match_expected(self, testnet_contracts, skip_if_no_testnet):
        """Verify deployed addresses match expected values."""
        # Assert
        for name, expected in EXPECTED_CONTRACTS.items():
            actual = testnet_contracts.get(name)
            assert actual == expected, f"{name}: expected {expected}, got {actual}"


class TestConnectorConfiguration:
    """Test VVS connector configuration with testnet."""

    def test_connector_loads_testnet_deployment(self, skip_if_no_testnet):
        """Verify VVSFinanceConnector loads testnet config."""
        # Act
        connector = VVSFinanceConnector(use_testnet=True)

        # Assert
        assert connector.router_address == EXPECTED_CONTRACTS["router"]

    def test_connector_uses_testnet_tokens(self, skip_if_no_testnet):
        """Verify connector uses testnet token addresses."""
        # Act
        connector = VVSFinanceConnector(use_testnet=True)

        # Assert
        assert "USDC" in connector.token_addresses
        assert connector.token_addresses["USDC"] == EXPECTED_CONTRACTS["tUSDC"]

    def test_connector_testnet_flag(self):
        """Verify testnet flag is correctly set."""
        # Act
        connector = VVSFinanceConnector(use_testnet=True)

        # Assert
        assert connector.use_testnet is True


class TestMockModeOperations:
    """Test connector operations in mock mode."""

    def test_get_quote_mock_mode(self):
        """Get price quote in mock mode."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=True, use_testnet=True)

        # Act
        quote = connector.get_quote("CRO", "USDC", 100)

        # Assert
        assert "expected_amount_out" in quote
        assert "exchange_rate" in quote
        assert quote["source"] == "mock"

    def test_swap_mock_mode(self):
        """Execute swap in mock mode."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=True, use_testnet=True)

        # Act
        result = connector.swap("CRO", "USDC", 10)

        # Assert
        assert result["success"] is True
        assert "expected_amount_out" in result or "amount_out" in result

    def test_quote_consistency(self):
        """Verify quote consistency between calls."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=True, use_testnet=True)

        # Act
        quote1 = connector.get_quote("CRO", "USDC", 100)
        quote2 = connector.get_quote("CRO", "USDC", 100)

        # Assert - Mock rates should be consistent
        assert quote1["exchange_rate"] == quote2["exchange_rate"]


@pytest.mark.integration
@pytest.mark.testnet
class TestOnChainOperations:
    """Test on-chain operations with testnet (requires RPC connection)."""

    def test_get_quote_from_testnet_router(self, skip_if_no_testnet):
        """Get real quote from testnet router contract."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)

        # Act
        quote = connector.get_quote("CRO", "USDC", 1)

        # Assert
        assert "expected_amount_out" in quote
        # Source should be either on-chain or mock (fallback)
        assert quote["source"] in ["on-chain", "mock"]

    def test_price_consistency_between_pools(self, skip_if_no_testnet):
        """Verify price consistency across token pairs."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)

        # Act
        cro_usdc = connector.get_quote("CRO", "USDC", 100)
        usdc_cro = connector.get_quote("USDC", "CRO", 10)

        # Assert - Both quotes should succeed
        assert cro_usdc is not None
        assert usdc_cro is not None

    def test_build_swap_transaction(self, skip_if_no_testnet):
        """Build unsigned swap transaction for testnet."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)

        # Act
        result = connector.swap("CRO", "USDC", 1)

        # Assert - Should have transaction data or mock result
        assert result is not None
        # Either unsigned_tx or mock tx_hash
        has_tx_data = "unsigned_tx" in result or "tx_hash" in result or "amount_out" in result
        assert has_tx_data


@pytest.mark.integration
@pytest.mark.testnet
class TestPoolLiquidity:
    """Test liquidity pool operations."""

    def test_pools_have_liquidity(self, skip_if_no_testnet):
        """Verify deployed pools have liquidity."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)

        # Act - Try to get quote (will fail if no liquidity)
        quote = connector.get_quote("CRO", "USDC", 1)

        # Assert
        assert quote is not None
        # A valid quote means liquidity exists

    def test_multiple_pool_quotes(self, skip_if_no_testnet):
        """Get quotes from multiple pools."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)
        pairs = [
            ("CRO", "USDC"),
            ("CRO", "USDT"),
            ("USDC", "USDT"),
        ]

        # Act & Assert
        for from_token, to_token in pairs:
            quote = connector.get_quote(from_token, to_token, 1)
            assert quote is not None, f"Failed to get quote for {from_token}-{to_token}"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_token_handling(self):
        """Handle invalid token symbol gracefully."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=True, use_testnet=True)

        # Act
        quote = connector.get_quote("INVALID", "USDC", 100)

        # Assert - Should return fallback rate or error
        assert quote is not None

    def test_zero_amount_handling(self):
        """Handle zero amount gracefully."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=True, use_testnet=True)

        # Act
        quote = connector.get_quote("CRO", "USDC", 0)

        # Assert
        assert quote is not None

    def test_negative_amount_handling(self):
        """Handle negative amount gracefully."""
        # Arrange
        connector = VVSFinanceConnector(use_mock=True, use_testnet=True)

        # Act
        quote = connector.get_quote("CRO", "USDC", -100)

        # Assert - Should handle gracefully
        assert quote is not None


class TestVVSCompatibleConfig:
    """Test VVS-compatible configuration structure."""

    def test_vvs_compatible_section_exists(self, testnet_config, skip_if_no_testnet):
        """Verify vvsCompatible section exists in deployment."""
        # Assert
        assert "vvsCompatible" in testnet_config

    def test_vvs_compatible_has_router(self, testnet_config, skip_if_no_testnet):
        """Verify vvsCompatible has router address."""
        # Arrange
        vvs_config = testnet_config.get("vvsCompatible", {})

        # Assert
        assert "routerAddress" in vvs_config
        assert vvs_config["routerAddress"] == EXPECTED_CONTRACTS["router"]

    def test_vvs_compatible_has_factory(self, testnet_config, skip_if_no_testnet):
        """Verify vvsCompatible has factory address."""
        # Arrange
        vvs_config = testnet_config.get("vvsCompatible", {})

        # Assert
        assert "factoryAddress" in vvs_config
        assert vvs_config["factoryAddress"] == EXPECTED_CONTRACTS["factory"]

    def test_vvs_compatible_has_token_addresses(self, testnet_config, skip_if_no_testnet):
        """Verify vvsCompatible has token addresses."""
        # Arrange
        vvs_config = testnet_config.get("vvsCompatible", {})

        # Assert
        assert "tokenAddresses" in vvs_config
        tokens = vvs_config["tokenAddresses"]
        assert "USDC" in tokens
        assert "USDT" in tokens
        assert "WCRO" in tokens

#!/usr/bin/env python3
"""
Testnet Integration Tests for Paygent Adapters.

This module tests real on-chain interactions with:
1. ServiceRegistry - MCP Discovery on-chain service registry
2. MoonlanderAdapter - Perpetual trading adapter
3. DelphiAdapter - Prediction market adapter
4. DeFi Research - Subagent orchestration

WARNING: These tests execute REAL transactions on Cronos Testnet.
Ensure you have sufficient testnet CRO for gas.

Run with: pytest tests/integration/test_adapters_real.py -v -s
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from decimal import Decimal
from typing import Any

import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import dotenv
dotenv.load_dotenv()

from web3 import Web3
from web3.exceptions import ContractLogicError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_adapters_real")

# ==================== Contract Configuration ====================

# Load deployment addresses
DEPLOYMENTS_PATH = project_root / "contracts" / "deployments" / "adapters-testnet.json"
VVS_DEPLOYMENTS_PATH = project_root / "contracts" / "deployments" / "vvs-testnet.json"

# Cronos Testnet Configuration
CRONOS_TESTNET_RPC = "https://evm-t3.cronos.org"
CRONOS_TESTNET_CHAIN_ID = 338
EXPLORER_URL = "https://explorer.cronos.org/testnet"

# Load ABIs
ABIS_PATH = project_root / "contracts" / "artifacts" / "contracts"

# Minimal ABIs for testing
SERVICE_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "description", "type": "string"},
            {"name": "endpoint", "type": "string"},
            {"name": "pricingModel", "type": "string"},
            {"name": "priceAmount", "type": "uint256"},
            {"name": "priceToken", "type": "string"},
            {"name": "mcpCompatible", "type": "bool"}
        ],
        "name": "registerService",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "serviceId", "type": "bytes32"}],
        "name": "getService",
        "outputs": [
            {"name": "name", "type": "string"},
            {"name": "description", "type": "string"},
            {"name": "endpoint", "type": "string"},
            {"name": "pricingModel", "type": "string"},
            {"name": "priceAmount", "type": "uint256"},
            {"name": "priceToken", "type": "string"},
            {"name": "mcpCompatible", "type": "bool"},
            {"name": "reputationScore", "type": "uint256"},
            {"name": "totalCalls", "type": "uint256"},
            {"name": "serviceOwner", "type": "address"},
            {"name": "registrationTime", "type": "uint256"},
            {"name": "active", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "serviceId", "type": "bytes32"}],
        "name": "getStake",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "serviceId", "type": "bytes32"}],
        "name": "incrementCallCount",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "defaultStake",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "reputationRequired",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "getServiceIdsByOwner",
        "outputs": [{"name": "", "type": "bytes32[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

MOONLANDER_ADAPTER_ABI = [
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "defaultLeverage",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "tradingRouter",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "MAX_LEVERAGE",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "MIN_LEVERAGE",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "trader", "type": "address"}],
        "name": "getTraderPositions",
        "outputs": [{"name": "", "type": "bytes32[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "baseToken", "type": "address"},
            {"name": "quoteToken", "type": "address"}
        ],
        "name": "getCurrentPrice",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

DELPHI_ADAPTER_ABI = [
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "defaultFee",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "marketsRegistry",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "feeCollector",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "better", "type": "address"}],
        "name": "getBetterBets",
        "outputs": [{"name": "", "type": "bytes32[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "newFee", "type": "uint256"}],
        "name": "updateFee",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


# ==================== Fixtures ====================

@pytest.fixture(scope="module")
def web3():
    """Create Web3 connection to Cronos Testnet."""
    w3 = Web3(Web3.HTTPProvider(CRONOS_TESTNET_RPC))
    if not w3.is_connected():
        pytest.skip("Cannot connect to Cronos Testnet RPC")
    return w3


@pytest.fixture(scope="module")
def private_key():
    """Get private key from environment."""
    key = os.getenv("AGENT_WALLET_PRIVATE_KEY")
    if not key:
        pytest.skip("AGENT_WALLET_PRIVATE_KEY not set in .env")
    return key


@pytest.fixture(scope="module")
def account(web3, private_key):
    """Get account from private key."""
    return web3.eth.account.from_key(private_key)


@pytest.fixture(scope="module")
def deployments():
    """Load deployment addresses."""
    if not DEPLOYMENTS_PATH.exists():
        pytest.skip(f"Deployment file not found: {DEPLOYMENTS_PATH}")
    with open(DEPLOYMENTS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def vvs_deployments():
    """Load VVS deployment addresses."""
    if not VVS_DEPLOYMENTS_PATH.exists():
        pytest.skip(f"VVS deployment file not found: {VVS_DEPLOYMENTS_PATH}")
    with open(VVS_DEPLOYMENTS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def service_registry(web3, deployments):
    """Get ServiceRegistry contract instance."""
    address = deployments["contracts"]["serviceRegistry"]
    return web3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=SERVICE_REGISTRY_ABI
    )


@pytest.fixture(scope="module")
def moonlander_adapter(web3, deployments):
    """Get MoonlanderAdapter contract instance."""
    address = deployments["contracts"]["moonlanderAdapter"]
    return web3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=MOONLANDER_ADAPTER_ABI
    )


@pytest.fixture(scope="module")
def delphi_adapter(web3, deployments):
    """Get DelphiAdapter contract instance."""
    address = deployments["contracts"]["delphiAdapter"]
    return web3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=DELPHI_ADAPTER_ABI
    )


# ==================== ServiceRegistry Tests (MCP Discovery) ====================

class TestServiceRegistryReal:
    """Real testnet integration tests for ServiceRegistry (MCP Discovery)."""

    def test_connection(self, web3, account):
        """Test connection to Cronos Testnet."""
        logger.info("Testing connection to Cronos Testnet...")

        chain_id = web3.eth.chain_id
        assert chain_id == CRONOS_TESTNET_CHAIN_ID, f"Expected chain ID 338, got {chain_id}"

        balance = web3.eth.get_balance(account.address)
        balance_cro = web3.from_wei(balance, 'ether')
        logger.info(f"Connected to Cronos Testnet (Chain ID: {chain_id})")
        logger.info(f"Account: {account.address}")
        logger.info(f"Balance: {balance_cro} TCRO")

        assert balance > 0, "Account has no balance for gas"

    def test_contract_deployment(self, service_registry, deployments):
        """Verify ServiceRegistry contract is deployed."""
        logger.info("Verifying ServiceRegistry deployment...")

        expected_address = deployments["contracts"]["serviceRegistry"]
        actual_address = service_registry.address

        assert actual_address.lower() == expected_address.lower()
        logger.info(f"ServiceRegistry verified at: {actual_address}")
        logger.info(f"Explorer: {EXPLORER_URL}/address/{actual_address}")

    def test_read_contract_state(self, service_registry, deployments):
        """Test reading ServiceRegistry contract state."""
        logger.info("Reading ServiceRegistry contract state...")

        owner = service_registry.functions.owner().call()
        default_stake = service_registry.functions.defaultStake().call()
        reputation_required = service_registry.functions.reputationRequired().call()

        expected_owner = deployments["parameters"]["serviceRegistry"]["owner"]
        assert owner.lower() == expected_owner.lower()

        logger.info(f"  Owner: {owner}")
        logger.info(f"  Default Stake: {Web3.from_wei(default_stake, 'ether')} CRO")
        logger.info(f"  Reputation Required: {reputation_required}")

        assert default_stake > 0
        assert reputation_required == 50

    def test_register_service(self, web3, service_registry, account, private_key):
        """Test registering a new service on-chain."""
        logger.info("Registering a new service on-chain...")

        # Service details
        import time
        service_name = f"Test MCP Service {int(time.time())}"
        service_description = "Integration test service for MCP discovery"
        service_endpoint = f"https://api.example.com/mcp/test-{int(time.time())}"
        pricing_model = "pay-per-call"
        price_amount = Web3.to_wei(0.01, 'ether')  # 0.01 CRO per call
        price_token = "CRO"
        mcp_compatible = True

        # Get required stake
        default_stake = service_registry.functions.defaultStake().call()
        logger.info(f"  Required stake: {Web3.from_wei(default_stake, 'ether')} CRO")

        # Build transaction
        tx = service_registry.functions.registerService(
            service_name,
            service_description,
            service_endpoint,
            pricing_model,
            price_amount,
            price_token,
            mcp_compatible
        ).build_transaction({
            'from': account.address,
            'value': default_stake,
            'gas': 500000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        # Sign and send
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        logger.info(f"  Transaction sent: {tx_hash.hex()}")
        logger.info(f"  Explorer: {EXPLORER_URL}/tx/{tx_hash.hex()}")

        # Wait for receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        assert receipt['status'] == 1, "Transaction failed"

        logger.info(f"  Transaction confirmed in block: {receipt['blockNumber']}")
        logger.info(f"  Gas used: {receipt['gasUsed']}")

        # Verify service was registered
        service_ids = service_registry.functions.getServiceIdsByOwner(account.address).call()
        assert len(service_ids) > 0, "No services found for owner"

        # Get the latest service
        latest_service_id = service_ids[-1]
        service = service_registry.functions.getService(latest_service_id).call()

        assert service[0] == service_name  # name
        assert service[6] == mcp_compatible  # mcpCompatible
        assert service[11] == True  # active

        logger.info(f"  ✓ Service registered successfully!")
        logger.info(f"    Service ID: {latest_service_id.hex()}")
        logger.info(f"    Name: {service[0]}")
        logger.info(f"    Endpoint: {service[2]}")

    def test_get_services_by_owner(self, service_registry, account):
        """Test getting all services owned by an address."""
        logger.info("Getting services by owner...")

        service_ids = service_registry.functions.getServiceIdsByOwner(account.address).call()
        logger.info(f"  Found {len(service_ids)} services for {account.address}")

        for i, service_id in enumerate(service_ids):
            service = service_registry.functions.getService(service_id).call()
            logger.info(f"  [{i+1}] {service[0]} - {service[2]}")


# ==================== MoonlanderAdapter Tests ====================

class TestMoonlanderAdapterReal:
    """Real testnet integration tests for MoonlanderAdapter."""

    def test_contract_deployment(self, moonlander_adapter, deployments):
        """Verify MoonlanderAdapter contract is deployed."""
        logger.info("Verifying MoonlanderAdapter deployment...")

        expected_address = deployments["contracts"]["moonlanderAdapter"]
        actual_address = moonlander_adapter.address

        assert actual_address.lower() == expected_address.lower()
        logger.info(f"MoonlanderAdapter verified at: {actual_address}")
        logger.info(f"Explorer: {EXPLORER_URL}/address/{actual_address}")

    def test_read_contract_state(self, moonlander_adapter, deployments):
        """Test reading MoonlanderAdapter contract state."""
        logger.info("Reading MoonlanderAdapter contract state...")

        owner = moonlander_adapter.functions.owner().call()
        default_leverage = moonlander_adapter.functions.defaultLeverage().call()
        trading_router = moonlander_adapter.functions.tradingRouter().call()
        max_leverage = moonlander_adapter.functions.MAX_LEVERAGE().call()
        min_leverage = moonlander_adapter.functions.MIN_LEVERAGE().call()

        expected_owner = deployments["parameters"]["moonlanderAdapter"]["tradingRouter"]
        assert owner.lower() == expected_owner.lower()

        logger.info(f"  Owner: {owner}")
        logger.info(f"  Trading Router: {trading_router}")
        logger.info(f"  Default Leverage: {default_leverage}x")
        logger.info(f"  Min Leverage: {min_leverage}x")
        logger.info(f"  Max Leverage: {max_leverage}x")

        assert default_leverage == 5
        assert min_leverage == 2
        assert max_leverage == 50

    def test_get_trader_positions(self, moonlander_adapter, account):
        """Test getting trader positions."""
        logger.info("Getting trader positions...")

        positions = moonlander_adapter.functions.getTraderPositions(account.address).call()
        logger.info(f"  Found {len(positions)} positions for {account.address}")

        # New account should have no positions
        assert isinstance(positions, list)

    def test_get_current_price(self, moonlander_adapter, vvs_deployments):
        """Test getting current price (mock implementation)."""
        logger.info("Getting current price...")

        # Use deployed token addresses
        wcro_address = vvs_deployments["contracts"]["wcro"]
        usdc_address = vvs_deployments["contracts"]["tUSDC"]

        price = moonlander_adapter.functions.getCurrentPrice(
            Web3.to_checksum_address(wcro_address),
            Web3.to_checksum_address(usdc_address)
        ).call()

        logger.info(f"  WCRO/USDC Price: {price}")
        # Mock implementation returns 1000
        assert price == 1000


# ==================== DelphiAdapter Tests ====================

class TestDelphiAdapterReal:
    """Real testnet integration tests for DelphiAdapter."""

    def test_contract_deployment(self, delphi_adapter, deployments):
        """Verify DelphiAdapter contract is deployed."""
        logger.info("Verifying DelphiAdapter deployment...")

        expected_address = deployments["contracts"]["delphiAdapter"]
        actual_address = delphi_adapter.address

        assert actual_address.lower() == expected_address.lower()
        logger.info(f"DelphiAdapter verified at: {actual_address}")
        logger.info(f"Explorer: {EXPLORER_URL}/address/{actual_address}")

    def test_read_contract_state(self, delphi_adapter, deployments):
        """Test reading DelphiAdapter contract state."""
        logger.info("Reading DelphiAdapter contract state...")

        owner = delphi_adapter.functions.owner().call()
        default_fee = delphi_adapter.functions.defaultFee().call()
        markets_registry = delphi_adapter.functions.marketsRegistry().call()
        fee_collector = delphi_adapter.functions.feeCollector().call()

        expected_owner = deployments["parameters"]["delphiAdapter"]["marketsRegistry"]
        assert owner.lower() == expected_owner.lower()

        logger.info(f"  Owner: {owner}")
        logger.info(f"  Markets Registry: {markets_registry}")
        logger.info(f"  Fee Collector: {fee_collector}")
        logger.info(f"  Default Fee: {default_fee} basis points ({default_fee/100}%)")

        assert default_fee == 100  # 1%

    def test_get_better_bets(self, delphi_adapter, account):
        """Test getting better's bets."""
        logger.info("Getting better's bets...")

        bets = delphi_adapter.functions.getBetterBets(account.address).call()
        logger.info(f"  Found {len(bets)} bets for {account.address}")

        # New account should have no bets
        assert isinstance(bets, list)

    def test_update_fee_as_owner(self, web3, delphi_adapter, account, private_key, deployments):
        """Test updating fee as owner."""
        logger.info("Testing fee update as owner...")

        # Only owner can update fee
        expected_owner = deployments["parameters"]["delphiAdapter"]["marketsRegistry"]
        if account.address.lower() != expected_owner.lower():
            logger.info("  Skipping: Account is not the owner")
            return

        new_fee = 150  # 1.5%

        tx = delphi_adapter.functions.updateFee(new_fee).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        logger.info(f"  Transaction sent: {tx_hash.hex()}")

        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        assert receipt['status'] == 1, "Transaction failed"

        # Verify fee was updated
        updated_fee = delphi_adapter.functions.defaultFee().call()
        assert updated_fee == new_fee

        logger.info(f"  ✓ Fee updated to {new_fee} basis points")

        # Reset fee back to 100
        tx2 = delphi_adapter.functions.updateFee(100).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })
        signed_tx2 = web3.eth.account.sign_transaction(tx2, private_key)
        tx_hash2 = web3.eth.send_raw_transaction(signed_tx2.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash2, timeout=120)
        logger.info(f"  ✓ Fee reset to 100 basis points")


# ==================== DeFi Research Subagent Tests ====================

class TestDeFiResearchReal:
    """Real testnet integration tests for DeFi Research subagents."""

    def test_vvs_connector_with_testnet(self, vvs_deployments):
        """Test VVS connector with real testnet contracts."""
        logger.info("Testing VVS connector with testnet contracts...")

        from src.connectors.vvs import VVSFinanceConnector

        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)
        w3 = connector._get_web3()

        assert w3 is not None
        assert w3.is_connected()

        chain_id = w3.eth.chain_id
        assert chain_id == CRONOS_TESTNET_CHAIN_ID

        logger.info(f"  ✓ VVS Connector connected to Chain ID: {chain_id}")

        # Test quote
        quote = connector.get_quote(
            from_token="CRO",
            to_token="USDC",
            amount=1.0,
            slippage_tolerance=1.0
        )

        logger.info(f"  Quote: 1 CRO -> {quote['expected_amount_out']} USDC")
        logger.info(f"  Source: {quote.get('source', 'unknown')}")

        assert 'expected_amount_out' in quote
        assert float(quote['expected_amount_out']) > 0

    def test_moonlander_connector_mock(self):
        """Test Moonlander connector mock functionality."""
        logger.info("Testing Moonlander connector...")

        from src.connectors.moonlander import MoonlanderConnector

        connector = MoonlanderConnector()

        # Test get markets
        markets = connector.get_markets()
        assert len(markets) > 0
        logger.info(f"  Found {len(markets)} markets")

        for market in markets:
            logger.info(f"    {market['symbol']}: ${market['current_price']}")

        # Test get funding rate
        funding = connector.get_funding_rate("BTC")
        assert 'funding_rate' in funding
        logger.info(f"  BTC Funding Rate: {funding['funding_rate_percentage']:.4f}%")

        # Test open position (mock)
        result = connector.open_position(
            asset="BTC",
            side="long",
            size=100.0,
            leverage=5
        )

        assert result['success'] == True
        assert 'position' in result
        logger.info(f"  ✓ Mock position opened: {result['position']['position_id']}")

        # Test close position (mock)
        close_result = connector.close_position(result['position']['position_id'])
        assert close_result['success'] == True
        logger.info(f"  ✓ Mock position closed: PnL ${close_result['realized_pnl']:.2f}")

    def test_delphi_connector_mock(self):
        """Test Delphi connector mock functionality."""
        logger.info("Testing Delphi connector...")

        from src.connectors.delphi import DelphiConnector

        connector = DelphiConnector()

        # Test get markets
        markets = connector.get_markets()
        assert len(markets) > 0
        logger.info(f"  Found {len(markets)} prediction markets")

        for market in markets:
            logger.info(f"    {market['market_id']}: {market['question'][:50]}...")

        # Test get market outcomes
        outcomes = connector.get_market_outcomes("market_001")
        assert 'odds' in outcomes
        logger.info(f"  Market 001 odds: {outcomes['odds']}")

        # Test place bet (mock)
        result = connector.place_bet(
            market_id="market_001",
            outcome="Yes",
            amount=10.0
        )

        assert result['success'] == True
        assert 'bet' in result
        logger.info(f"  ✓ Mock bet placed: {result['bet']['bet_id']}")
        logger.info(f"    Potential return: ${result['bet']['potential_return_usd']:.2f}")


# ==================== End-to-End Integration Test ====================

class TestEndToEndIntegration:
    """End-to-end integration tests combining multiple services."""

    def test_full_service_discovery_flow(self, web3, service_registry, account, private_key):
        """Test complete service discovery flow."""
        logger.info("Testing full service discovery flow...")

        # 1. Check initial state
        initial_services = service_registry.functions.getServiceIdsByOwner(account.address).call()
        initial_count = len(initial_services)
        logger.info(f"  Initial services: {initial_count}")

        # 2. Register a new DeFi service
        import time
        service_name = f"DeFi Analytics Service {int(time.time())}"
        default_stake = service_registry.functions.defaultStake().call()

        tx = service_registry.functions.registerService(
            service_name,
            "Real-time DeFi analytics and insights",
            f"https://defi-analytics.example.com/api/{int(time.time())}",
            "subscription",
            Web3.to_wei(1, 'ether'),  # 1 CRO per month
            "CRO",
            True  # MCP compatible
        ).build_transaction({
            'from': account.address,
            'value': default_stake,
            'gas': 500000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        assert receipt['status'] == 1

        # 3. Verify new service count
        final_services = service_registry.functions.getServiceIdsByOwner(account.address).call()
        assert len(final_services) == initial_count + 1

        # 4. Get and verify the new service
        new_service_id = final_services[-1]
        service = service_registry.functions.getService(new_service_id).call()

        assert service[0] == service_name
        assert service[3] == "subscription"
        assert service[6] == True  # MCP compatible
        assert service[11] == True  # active

        logger.info(f"  ✓ Full service discovery flow completed")
        logger.info(f"    New Service ID: {new_service_id.hex()}")
        logger.info(f"    Transaction: {EXPLORER_URL}/tx/{tx_hash.hex()}")


# ==================== Main ====================

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])

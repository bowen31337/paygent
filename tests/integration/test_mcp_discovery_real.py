#!/usr/bin/env python3
"""
MCP Discovery Testnet Integration Tests.

This module tests real on-chain interactions for MCP Discovery:
1. ServiceRegistry on-chain service registration
2. Querying the registry for market data services
3. Service discovery workflows
4. MCP-compatible service filtering

WARNING: These tests execute REAL transactions on Cronos Testnet.
Ensure you have sufficient testnet CRO for gas.

Run with: pytest tests/integration/test_mcp_discovery_real.py -v -s
"""

import json
import logging
import os
import sys
import time
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_mcp_discovery_real")

# ==================== Configuration ====================

CRONOS_TESTNET_RPC = "https://evm-t3.cronos.org"
CRONOS_TESTNET_CHAIN_ID = 338
EXPLORER_URL = "https://explorer.cronos.org/testnet"

ADAPTERS_DEPLOYMENTS_PATH = project_root / "contracts" / "deployments" / "adapters-testnet.json"

# Full ServiceRegistry ABI
SERVICE_REGISTRY_ABI = [
    # Write functions
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
        "inputs": [
            {"name": "serviceId", "type": "bytes32"},
            {"name": "description", "type": "string"},
            {"name": "priceAmount", "type": "uint256"},
            {"name": "priceToken", "type": "string"}
        ],
        "name": "updateService",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "serviceId", "type": "bytes32"}],
        "name": "deactivateService",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "serviceId", "type": "bytes32"}],
        "name": "activateService",
        "outputs": [],
        "stateMutability": "nonpayable",
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
        "inputs": [{"name": "serviceId", "type": "bytes32"}, {"name": "scoreChange", "type": "int256"}],
        "name": "updateReputation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "serviceId", "type": "bytes32"}],
        "name": "depositStake",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "serviceId", "type": "bytes32"}, {"name": "amount", "type": "uint256"}],
        "name": "withdrawStake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Read functions
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
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "getServiceIdsByOwner",
        "outputs": [{"name": "", "type": "bytes32[]"}],
        "stateMutability": "view",
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
    # Events
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "serviceId", "type": "bytes32"},
            {"indexed": False, "name": "name", "type": "string"},
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": False, "name": "stake", "type": "uint256"}
        ],
        "name": "ServiceRegistered",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "serviceId", "type": "bytes32"},
            {"indexed": False, "name": "description", "type": "string"}
        ],
        "name": "ServiceUpdated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "serviceId", "type": "bytes32"}
        ],
        "name": "ServiceDeactivated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "serviceId", "type": "bytes32"},
            {"indexed": False, "name": "newScore", "type": "uint256"}
        ],
        "name": "ReputationUpdated",
        "type": "event"
    }
]


# ==================== Market Data Service Definitions ====================

MARKET_DATA_SERVICES = [
    {
        "name": "Crypto.com Market Data MCP",
        "description": "Real-time cryptocurrency prices and market data via MCP protocol. Supports BTC, ETH, CRO, and 100+ trading pairs.",
        "endpoint": "https://mcp.crypto.com/market-data/v1",
        "pricing_model": "pay-per-call",
        "price_amount": Web3.to_wei(0.001, 'ether'),  # 0.001 CRO per call
        "price_token": "CRO",
        "mcp_compatible": True,
    },
    {
        "name": "DeFi Analytics Service",
        "description": "On-chain DeFi analytics for Cronos ecosystem. TVL, APY, and protocol metrics.",
        "endpoint": "https://api.defi-analytics.cronos.org/v1",
        "pricing_model": "subscription",
        "price_amount": Web3.to_wei(10, 'ether'),  # 10 CRO per month
        "price_token": "CRO",
        "mcp_compatible": True,
    },
    {
        "name": "VVS Finance Price Oracle",
        "description": "DEX price feeds from VVS Finance liquidity pools. TWAP and spot prices.",
        "endpoint": "https://oracle.vvs.finance/api/v1",
        "pricing_model": "pay-per-call",
        "price_amount": Web3.to_wei(0.0005, 'ether'),  # 0.0005 CRO per call
        "price_token": "CRO",
        "mcp_compatible": True,
    },
    {
        "name": "Cronos Block Explorer API",
        "description": "Block and transaction data from Cronos blockchain. REST API with historical data.",
        "endpoint": "https://api.cronoscan.com/api",
        "pricing_model": "metered",
        "price_amount": Web3.to_wei(0.01, 'ether'),  # 0.01 CRO per 1000 calls
        "price_token": "CRO",
        "mcp_compatible": False,  # Not MCP compatible
    },
    {
        "name": "NFT Metadata Service",
        "description": "NFT metadata and collection analytics for Cronos NFT marketplace.",
        "endpoint": "https://nft-api.cronos.org/metadata/v1",
        "pricing_model": "pay-per-call",
        "price_amount": Web3.to_wei(0.002, 'ether'),  # 0.002 CRO per call
        "price_token": "CRO",
        "mcp_compatible": False,
    },
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
    """Load adapter deployment addresses."""
    if not ADAPTERS_DEPLOYMENTS_PATH.exists():
        pytest.skip(f"Deployment file not found: {ADAPTERS_DEPLOYMENTS_PATH}")
    with open(ADAPTERS_DEPLOYMENTS_PATH) as f:
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
def registered_services(web3, service_registry, account, private_key, deployments):
    """Register market data services and return their IDs."""
    logger.info("=" * 60)
    logger.info("Registering Market Data Services")
    logger.info("=" * 60)

    default_stake = service_registry.functions.defaultStake().call()
    logger.info(f"Default stake required: {Web3.from_wei(default_stake, 'ether')} CRO")

    registered = []

    for i, svc in enumerate(MARKET_DATA_SERVICES):
        logger.info(f"\n[{i+1}/{len(MARKET_DATA_SERVICES)}] Registering: {svc['name']}")

        # Add timestamp to make endpoint unique
        unique_endpoint = f"{svc['endpoint']}?ts={int(time.time())}_{i}"

        try:
            tx = service_registry.functions.registerService(
                svc['name'],
                svc['description'],
                unique_endpoint,
                svc['pricing_model'],
                svc['price_amount'],
                svc['price_token'],
                svc['mcp_compatible']
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

            if receipt['status'] == 1:
                # Get service ID from logs
                service_ids = service_registry.functions.getServiceIdsByOwner(account.address).call()
                service_id = service_ids[-1]  # Latest registered

                registered.append({
                    'id': service_id,
                    'name': svc['name'],
                    'mcp_compatible': svc['mcp_compatible'],
                    'pricing_model': svc['pricing_model'],
                    'tx_hash': tx_hash.hex()
                })

                logger.info(f"   ✓ Registered: {service_id.hex()[:16]}...")
                logger.info(f"   TX: {EXPLORER_URL}/tx/{tx_hash.hex()}")
            else:
                logger.warning(f"   ✗ Registration failed")

        except Exception as e:
            logger.warning(f"   ✗ Error: {e}")

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Registered {len(registered)} services")
    logger.info("=" * 60)

    return registered


# ==================== MCP Discovery Tests ====================

class TestMCPDiscoveryBasics:
    """Basic MCP Discovery functionality tests."""

    def test_registry_connection(self, service_registry, deployments):
        """Test connection to ServiceRegistry contract."""
        logger.info("Testing ServiceRegistry connection...")

        expected_address = deployments["contracts"]["serviceRegistry"]
        assert service_registry.address.lower() == expected_address.lower()

        owner = service_registry.functions.owner().call()
        logger.info(f"  Registry Address: {service_registry.address}")
        logger.info(f"  Owner: {owner}")
        logger.info(f"  Explorer: {EXPLORER_URL}/address/{service_registry.address}")

    def test_registry_config(self, service_registry):
        """Test registry configuration parameters."""
        logger.info("Reading registry configuration...")

        default_stake = service_registry.functions.defaultStake().call()
        reputation_required = service_registry.functions.reputationRequired().call()

        logger.info(f"  Default Stake: {Web3.from_wei(default_stake, 'ether')} CRO")
        logger.info(f"  Reputation Required: {reputation_required}")

        assert default_stake > 0
        assert reputation_required == 50


class TestServiceRegistration:
    """Service registration tests."""

    def test_register_market_data_services(self, registered_services):
        """Test registering market data services."""
        logger.info("Verifying registered services...")

        assert len(registered_services) > 0
        logger.info(f"  Total services registered: {len(registered_services)}")

        for svc in registered_services:
            logger.info(f"  - {svc['name']}: {svc['id'].hex()[:16]}...")

    def test_query_registered_services(self, service_registry, registered_services):
        """Test querying registered services."""
        logger.info("Querying registered services...")

        for svc in registered_services:
            service_data = service_registry.functions.getService(svc['id']).call()

            name = service_data[0]
            description = service_data[1]
            endpoint = service_data[2]
            mcp_compatible = service_data[6]
            reputation = service_data[7]
            active = service_data[11]

            logger.info(f"\n  Service: {name}")
            logger.info(f"    ID: {svc['id'].hex()[:16]}...")
            logger.info(f"    MCP Compatible: {mcp_compatible}")
            logger.info(f"    Reputation: {reputation}")
            logger.info(f"    Active: {active}")

            assert name == svc['name']
            assert mcp_compatible == svc['mcp_compatible']
            assert active == True


class TestMCPServiceDiscovery:
    """MCP-specific service discovery tests."""

    def test_filter_mcp_compatible_services(self, service_registry, registered_services):
        """Test filtering MCP-compatible services."""
        logger.info("Filtering MCP-compatible services...")

        mcp_services = []
        non_mcp_services = []

        for svc in registered_services:
            service_data = service_registry.functions.getService(svc['id']).call()
            mcp_compatible = service_data[6]

            if mcp_compatible:
                mcp_services.append(svc)
            else:
                non_mcp_services.append(svc)

        logger.info(f"  MCP-Compatible: {len(mcp_services)}")
        for svc in mcp_services:
            logger.info(f"    ✓ {svc['name']}")

        logger.info(f"  Non-MCP: {len(non_mcp_services)}")
        for svc in non_mcp_services:
            logger.info(f"    - {svc['name']}")

        # We registered 3 MCP and 2 non-MCP services
        assert len(mcp_services) >= 3
        assert len(non_mcp_services) >= 2

    def test_query_market_data_services(self, service_registry, registered_services):
        """Test querying market data services by endpoint pattern."""
        logger.info("Querying market data services...")

        market_data_services = []

        for svc in registered_services:
            service_data = service_registry.functions.getService(svc['id']).call()
            endpoint = service_data[2]
            description = service_data[1]

            # Filter by market data related keywords
            if 'market' in description.lower() or 'price' in description.lower() or 'oracle' in description.lower():
                market_data_services.append({
                    'id': svc['id'],
                    'name': service_data[0],
                    'endpoint': endpoint,
                    'description': description[:100] + '...',
                })

        logger.info(f"  Found {len(market_data_services)} market data services:")
        for svc in market_data_services:
            logger.info(f"    - {svc['name']}")
            logger.info(f"      Endpoint: {svc['endpoint'][:50]}...")

        assert len(market_data_services) >= 2

    def test_query_services_by_pricing_model(self, service_registry, registered_services):
        """Test querying services by pricing model."""
        logger.info("Querying services by pricing model...")

        pricing_groups = {
            'pay-per-call': [],
            'subscription': [],
            'metered': [],
        }

        for svc in registered_services:
            service_data = service_registry.functions.getService(svc['id']).call()
            pricing_model = service_data[3]

            if pricing_model in pricing_groups:
                pricing_groups[pricing_model].append({
                    'name': service_data[0],
                    'price': Web3.from_wei(service_data[4], 'ether'),
                    'token': service_data[5],
                })

        for model, services in pricing_groups.items():
            logger.info(f"\n  {model.upper()} ({len(services)} services):")
            for svc in services:
                logger.info(f"    - {svc['name']}: {svc['price']} {svc['token']}")


class TestServiceLifecycle:
    """Service lifecycle management tests."""

    def test_update_service(self, web3, service_registry, account, private_key, registered_services):
        """Test updating a service."""
        if not registered_services:
            pytest.skip("No services registered")

        logger.info("Testing service update...")

        service_id = registered_services[0]['id']
        new_description = f"Updated description at {int(time.time())}"
        new_price = Web3.to_wei(0.005, 'ether')

        tx = service_registry.functions.updateService(
            service_id,
            new_description,
            new_price,
            "CRO"
        ).build_transaction({
            'from': account.address,
            'gas': 200000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        assert receipt['status'] == 1

        # Verify update
        service_data = service_registry.functions.getService(service_id).call()
        assert service_data[1] == new_description
        assert service_data[4] == new_price

        logger.info(f"  ✓ Service updated")
        logger.info(f"    New Description: {new_description}")
        logger.info(f"    New Price: {Web3.from_wei(new_price, 'ether')} CRO")
        logger.info(f"    TX: {EXPLORER_URL}/tx/{tx_hash.hex()}")

    def test_increment_call_count(self, web3, service_registry, account, private_key, registered_services):
        """Test incrementing service call count."""
        if not registered_services:
            pytest.skip("No services registered")

        logger.info("Testing call count increment...")

        service_id = registered_services[0]['id']

        # Get initial count
        service_data = service_registry.functions.getService(service_id).call()
        initial_calls = service_data[8]

        tx = service_registry.functions.incrementCallCount(service_id).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        assert receipt['status'] == 1

        # Verify increment
        service_data = service_registry.functions.getService(service_id).call()
        new_calls = service_data[8]

        assert new_calls == initial_calls + 1

        logger.info(f"  ✓ Call count incremented: {initial_calls} -> {new_calls}")

    def test_deactivate_and_reactivate_service(self, web3, service_registry, account, private_key, registered_services):
        """Test deactivating and reactivating a service."""
        if not registered_services:
            pytest.skip("No services registered")

        logger.info("Testing service deactivation/reactivation...")

        # Use the last service to avoid affecting other tests
        service_id = registered_services[-1]['id']

        # Deactivate
        tx1 = service_registry.functions.deactivateService(service_id).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        signed_tx1 = web3.eth.account.sign_transaction(tx1, private_key)
        tx_hash1 = web3.eth.send_raw_transaction(signed_tx1.raw_transaction)
        receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash1, timeout=120)
        assert receipt1['status'] == 1

        # Verify deactivation
        service_data = service_registry.functions.getService(service_id).call()
        assert service_data[11] == False  # active = False
        logger.info(f"  ✓ Service deactivated")

        # Reactivate
        tx2 = service_registry.functions.activateService(service_id).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        signed_tx2 = web3.eth.account.sign_transaction(tx2, private_key)
        tx_hash2 = web3.eth.send_raw_transaction(signed_tx2.raw_transaction)
        receipt2 = web3.eth.wait_for_transaction_receipt(tx_hash2, timeout=120)
        assert receipt2['status'] == 1

        # Verify reactivation
        service_data = service_registry.functions.getService(service_id).call()
        assert service_data[11] == True  # active = True
        logger.info(f"  ✓ Service reactivated")

    def test_update_reputation(self, web3, service_registry, account, private_key, registered_services):
        """Test updating service reputation (owner only)."""
        if not registered_services:
            pytest.skip("No services registered")

        logger.info("Testing reputation update...")

        service_id = registered_services[0]['id']

        # Get initial reputation
        service_data = service_registry.functions.getService(service_id).call()
        initial_reputation = service_data[7]

        # Increase reputation by 10
        tx = service_registry.functions.updateReputation(service_id, 10).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        assert receipt['status'] == 1

        # Verify reputation update
        service_data = service_registry.functions.getService(service_id).call()
        new_reputation = service_data[7]

        assert new_reputation == initial_reputation + 10
        logger.info(f"  ✓ Reputation updated: {initial_reputation} -> {new_reputation}")


class TestMCPDiscoveryWorkflow:
    """End-to-end MCP discovery workflow tests."""

    def test_full_discovery_workflow(self, web3, service_registry, account, registered_services):
        """Test complete MCP service discovery workflow."""
        logger.info("=" * 60)
        logger.info("MCP Discovery Workflow Test")
        logger.info("=" * 60)

        # Step 1: Discover all services
        logger.info("\n1. Discovering all registered services...")
        all_services = service_registry.functions.getServiceIdsByOwner(account.address).call()
        logger.info(f"   Found {len(all_services)} services registered by {account.address[:10]}...")

        # Step 2: Filter MCP-compatible services
        logger.info("\n2. Filtering MCP-compatible services...")
        mcp_services = []
        for service_id in all_services:
            service_data = service_registry.functions.getService(service_id).call()
            if service_data[6]:  # mcp_compatible
                mcp_services.append({
                    'id': service_id,
                    'name': service_data[0],
                    'endpoint': service_data[2],
                    'pricing': f"{Web3.from_wei(service_data[4], 'ether')} {service_data[5]}",
                    'reputation': service_data[7],
                })

        logger.info(f"   Found {len(mcp_services)} MCP-compatible services")

        # Step 3: Rank by reputation
        logger.info("\n3. Ranking by reputation...")
        mcp_services.sort(key=lambda x: x['reputation'], reverse=True)

        for i, svc in enumerate(mcp_services[:5]):
            logger.info(f"   [{i+1}] {svc['name']}")
            logger.info(f"       Reputation: {svc['reputation']}")
            logger.info(f"       Pricing: {svc['pricing']}")

        # Step 4: Select best service
        logger.info("\n4. Selecting best service for market data...")
        if mcp_services:
            best_service = mcp_services[0]
            logger.info(f"   Selected: {best_service['name']}")
            logger.info(f"   Endpoint: {best_service['endpoint'][:50]}...")
            logger.info(f"   Price: {best_service['pricing']}")

        # Step 5: Verify service details
        logger.info("\n5. Verifying service details...")
        if mcp_services:
            service_data = service_registry.functions.getService(best_service['id']).call()
            stake = service_registry.functions.getStake(best_service['id']).call()

            logger.info(f"   Name: {service_data[0]}")
            logger.info(f"   Owner: {service_data[9]}")
            logger.info(f"   Registered: {service_data[10]} (unix timestamp)")
            logger.info(f"   Stake: {Web3.from_wei(stake, 'ether')} CRO")
            logger.info(f"   Active: {service_data[11]}")

        logger.info("\n" + "=" * 60)
        logger.info("MCP Discovery Workflow Complete!")
        logger.info("=" * 60)

    def test_market_data_service_selection(self, service_registry, registered_services):
        """Test selecting the best market data service."""
        logger.info("Testing market data service selection...")

        candidates = []

        for svc in registered_services:
            service_data = service_registry.functions.getService(svc['id']).call()

            # Only consider MCP-compatible, active services
            if service_data[6] and service_data[11]:
                description = service_data[1].lower()

                # Score based on relevance
                score = service_data[7]  # Base: reputation
                if 'market' in description:
                    score += 20
                if 'price' in description:
                    score += 15
                if 'real-time' in description:
                    score += 10
                if 'mcp' in description:
                    score += 10

                candidates.append({
                    'id': svc['id'],
                    'name': service_data[0],
                    'score': score,
                    'price': Web3.from_wei(service_data[4], 'ether'),
                })

        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"  Market data service candidates (ranked):")
        for i, c in enumerate(candidates[:3]):
            logger.info(f"    [{i+1}] {c['name']} (score: {c['score']}, price: {c['price']} CRO)")

        if candidates:
            logger.info(f"\n  ✓ Best choice: {candidates[0]['name']}")


# ==================== Main ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

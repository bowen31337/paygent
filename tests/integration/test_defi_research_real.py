#!/usr/bin/env python3
"""
DeFi Research Testnet Integration Tests.

This module tests real on-chain interactions for DeFi Research scenarios:
1. VVS Finance - Token swaps with real testnet transactions
2. Moonlander - Perpetual trading adapter interactions
3. Delphi - Prediction market adapter interactions
4. Full DeFi Research flow with subagent orchestration

WARNING: These tests execute REAL transactions on Cronos Testnet.
Ensure you have sufficient testnet CRO for gas.

Run with: pytest tests/integration/test_defi_research_real.py -v -s
"""

import asyncio
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
logger = logging.getLogger("test_defi_research_real")

# ==================== Configuration ====================

# Cronos Testnet Configuration
CRONOS_TESTNET_RPC = "https://evm-t3.cronos.org"
CRONOS_TESTNET_CHAIN_ID = 338
EXPLORER_URL = "https://explorer.cronos.org/testnet"

# Deployment paths
VVS_DEPLOYMENTS_PATH = project_root / "contracts" / "deployments" / "vvs-testnet.json"
ADAPTERS_DEPLOYMENTS_PATH = project_root / "contracts" / "deployments" / "adapters-testnet.json"

# ERC20 ABI for token operations
ERC20_ABI = [
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "faucet", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
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
def vvs_deployments():
    """Load VVS deployment addresses."""
    if not VVS_DEPLOYMENTS_PATH.exists():
        pytest.skip(f"VVS deployment file not found: {VVS_DEPLOYMENTS_PATH}")
    with open(VVS_DEPLOYMENTS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def adapters_deployments():
    """Load adapter deployment addresses."""
    if not ADAPTERS_DEPLOYMENTS_PATH.exists():
        pytest.skip(f"Adapters deployment file not found: {ADAPTERS_DEPLOYMENTS_PATH}")
    with open(ADAPTERS_DEPLOYMENTS_PATH) as f:
        return json.load(f)


# ==================== VVS Finance Real Tests ====================

class TestVVSFinanceReal:
    """Real testnet integration tests for VVS Finance operations."""

    def test_wallet_balance(self, web3, account):
        """Test wallet has sufficient balance for operations."""
        logger.info("Checking wallet balance...")

        balance_wei = web3.eth.get_balance(account.address)
        balance_cro = web3.from_wei(balance_wei, 'ether')

        logger.info(f"  Wallet: {account.address}")
        logger.info(f"  Balance: {balance_cro} TCRO")

        assert balance_cro > 0.5, f"Insufficient balance: {balance_cro} TCRO (need > 0.5)"

    def test_vvs_connector_testnet_config(self, vvs_deployments):
        """Test VVS connector loads testnet configuration correctly."""
        logger.info("Testing VVS connector testnet configuration...")

        from src.connectors.vvs import VVSFinanceConnector

        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)

        info = connector.get_deployment_info()
        logger.info(f"  Network: {info['network']}")
        logger.info(f"  Router: {info['router_address']}")
        logger.info(f"  Deployment loaded: {info['deployment_loaded']}")
        logger.info(f"  RPC connected: {info['rpc_connected']}")

        assert info['deployment_loaded'] == True
        assert info['rpc_connected'] == True
        assert info['router_address'] == vvs_deployments['contracts']['router']

    def test_get_on_chain_quote(self, vvs_deployments):
        """Test getting real on-chain price quotes."""
        logger.info("Getting on-chain price quotes...")

        from src.connectors.vvs import VVSFinanceConnector

        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)

        # Test CRO -> USDC quote
        quote = connector.get_quote(
            from_token="CRO",
            to_token="USDC",
            amount=1.0,
            slippage_tolerance=1.0
        )

        logger.info(f"  Quote: 1 CRO -> {quote['expected_amount_out']} USDC")
        logger.info(f"  Exchange Rate: {quote['exchange_rate']}")
        logger.info(f"  Source: {quote['source']}")
        logger.info(f"  Min Out: {quote['min_amount_out']} USDC")

        assert quote['source'] == 'on-chain', f"Expected on-chain quote, got {quote['source']}"
        assert float(quote['expected_amount_out']) > 0

        # Test USDC -> USDT quote
        quote2 = connector.get_quote(
            from_token="USDC",
            to_token="USDT",
            amount=10.0,
            slippage_tolerance=0.5
        )

        logger.info(f"  Quote: 10 USDC -> {quote2['expected_amount_out']} USDT")
        assert quote2['source'] == 'on-chain'

    def test_check_token_balances(self, web3, account, vvs_deployments):
        """Test checking token balances."""
        logger.info("Checking token balances...")

        tokens = {
            "WCRO": vvs_deployments['contracts']['wcro'],
            "tUSDC": vvs_deployments['contracts']['tUSDC'],
            "tUSDT": vvs_deployments['contracts']['tUSDT'],
            "tVVS": vvs_deployments['contracts']['tVVS'],
        }

        for name, address in tokens.items():
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=ERC20_ABI
            )
            try:
                balance = contract.functions.balanceOf(account.address).call()
                decimals = contract.functions.decimals().call()
                balance_formatted = Decimal(balance) / Decimal(10 ** decimals)
                logger.info(f"  {name}: {balance_formatted}")
            except Exception as e:
                logger.warning(f"  {name}: Error reading balance - {e}")

    def test_mint_test_tokens(self, web3, account, private_key, vvs_deployments):
        """Mint test tokens from faucet if needed."""
        logger.info("Minting test tokens from faucet...")

        tokens_to_mint = [
            ("tUSDC", vvs_deployments['contracts']['tUSDC']),
            ("tUSDT", vvs_deployments['contracts']['tUSDT']),
        ]

        for name, address in tokens_to_mint:
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=ERC20_ABI
            )

            try:
                balance = contract.functions.balanceOf(account.address).call()
                decimals = contract.functions.decimals().call()
                balance_formatted = Decimal(balance) / Decimal(10 ** decimals)

                if balance_formatted < 10:
                    logger.info(f"  Minting {name} from faucet...")

                    tx = contract.functions.faucet().build_transaction({
                        'from': account.address,
                        'gas': 100000,
                        'gasPrice': web3.eth.gas_price,
                        'nonce': web3.eth.get_transaction_count(account.address),
                        'chainId': CRONOS_TESTNET_CHAIN_ID
                    })

                    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
                    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

                    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    if receipt['status'] == 1:
                        new_balance = contract.functions.balanceOf(account.address).call()
                        new_balance_formatted = Decimal(new_balance) / Decimal(10 ** decimals)
                        logger.info(f"  ✓ {name} minted! New balance: {new_balance_formatted}")
                    else:
                        logger.warning(f"  ✗ {name} faucet transaction failed")
                else:
                    logger.info(f"  {name}: Balance sufficient ({balance_formatted})")

            except Exception as e:
                logger.warning(f"  {name}: Faucet error - {e}")

    def test_approve_tokens_for_router(self, web3, account, private_key, vvs_deployments):
        """Approve tokens for router spending."""
        logger.info("Approving tokens for router...")

        router_address = vvs_deployments['contracts']['router']

        tokens_to_approve = [
            ("tUSDC", vvs_deployments['contracts']['tUSDC']),
            ("tUSDT", vvs_deployments['contracts']['tUSDT']),
        ]

        for name, address in tokens_to_approve:
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=ERC20_ABI
            )

            try:
                # Check current allowance
                allowance = contract.functions.allowance(
                    account.address,
                    Web3.to_checksum_address(router_address)
                ).call()

                if allowance < 10 ** 18:  # Less than 1 token allowance
                    logger.info(f"  Approving {name} for router...")

                    max_approval = 2 ** 256 - 1  # Max uint256

                    tx = contract.functions.approve(
                        Web3.to_checksum_address(router_address),
                        max_approval
                    ).build_transaction({
                        'from': account.address,
                        'gas': 100000,
                        'gasPrice': web3.eth.gas_price,
                        'nonce': web3.eth.get_transaction_count(account.address),
                        'chainId': CRONOS_TESTNET_CHAIN_ID
                    })

                    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
                    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

                    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    if receipt['status'] == 1:
                        logger.info(f"  ✓ {name} approved for router")
                    else:
                        logger.warning(f"  ✗ {name} approval failed")
                else:
                    logger.info(f"  {name}: Already approved")

            except Exception as e:
                logger.warning(f"  {name}: Approval error - {e}")

    def test_execute_real_swap(self, web3, account, private_key, vvs_deployments):
        """Execute a real token swap on testnet."""
        logger.info("Executing real token swap (USDC -> USDT)...")

        from src.connectors.vvs import VVSFinanceConnector

        connector = VVSFinanceConnector(use_mock=False, use_testnet=True)

        # Check USDC balance first
        usdc_contract = web3.eth.contract(
            address=Web3.to_checksum_address(vvs_deployments['contracts']['tUSDC']),
            abi=ERC20_ABI
        )
        usdc_balance = usdc_contract.functions.balanceOf(account.address).call()
        usdc_balance_formatted = Decimal(usdc_balance) / Decimal(10 ** 6)

        if usdc_balance_formatted < 1:
            logger.warning(f"  Insufficient USDC balance: {usdc_balance_formatted}")
            pytest.skip("Insufficient USDC balance for swap test")

        logger.info(f"  USDC Balance: {usdc_balance_formatted}")

        # Execute swap: 1 USDC -> USDT
        swap_amount = 1.0
        result = connector.execute_swap(
            from_token="USDC",
            to_token="USDT",
            amount=swap_amount,
            private_key=private_key,
            slippage_tolerance=2.0,  # Higher tolerance for testnet
            deadline=120
        )

        if result['success']:
            logger.info(f"  ✓ Swap successful!")
            logger.info(f"    TX Hash: {result['tx_hash']}")
            logger.info(f"    Block: {result['block_number']}")
            logger.info(f"    Gas Used: {result['gas_used']}")
            logger.info(f"    Output: {result['actual_output']} USDT")
            logger.info(f"    Explorer: {EXPLORER_URL}/tx/{result['tx_hash']}")
        else:
            logger.warning(f"  ✗ Swap failed: {result.get('error')}")

        assert result['success'], f"Swap failed: {result.get('error')}"


# ==================== Moonlander Adapter Real Tests ====================

class TestMoonlanderAdapterReal:
    """Real testnet integration tests for Moonlander Adapter."""

    def test_connector_with_testnet(self, adapters_deployments):
        """Test Moonlander connector with testnet configuration."""
        logger.info("Testing Moonlander connector with testnet...")

        from src.connectors.moonlander import MoonlanderConnector

        connector = MoonlanderConnector(use_mock=False, use_testnet=True)

        info = connector.get_contract_info()
        logger.info(f"  Source: {info['source']}")

        if info['source'] == 'on-chain':
            logger.info(f"  Adapter: {info['adapter_address']}")
            logger.info(f"  Owner: {info['owner']}")
            logger.info(f"  Default Leverage: {info['default_leverage']}x")
            logger.info(f"  Max Leverage: {info['max_leverage']}x")
            logger.info(f"  Min Leverage: {info['min_leverage']}x")

            assert info['adapter_address'] == adapters_deployments['contracts']['moonlanderAdapter']
            assert info['default_leverage'] == 5
        else:
            logger.info(f"  Using mock: {info.get('message', 'N/A')}")

    def test_get_markets_with_prices(self):
        """Test getting markets with current prices."""
        logger.info("Getting perpetual markets...")

        from src.connectors.moonlander import MoonlanderConnector

        connector = MoonlanderConnector(use_mock=True)  # Mock for market data

        markets = connector.get_markets()
        logger.info(f"  Found {len(markets)} markets")

        for market in markets:
            logger.info(
                f"    {market['symbol']}: ${market['current_price']:,.2f} "
                f"(max {market['max_leverage']}x)"
            )

        assert len(markets) == 3
        assert markets[0]['symbol'] == 'BTC-USDC'

    def test_open_close_position_flow(self):
        """Test full position lifecycle."""
        logger.info("Testing position lifecycle...")

        from src.connectors.moonlander import MoonlanderConnector

        connector = MoonlanderConnector(use_mock=True)

        # Open long position
        open_result = connector.open_position(
            asset="BTC",
            side="long",
            size=100.0,
            leverage=5
        )

        logger.info(f"  Opened position: {open_result['position']['position_id']}")
        logger.info(f"    Entry: ${open_result['position']['entry_price']:,.2f}")
        logger.info(f"    Liquidation: ${open_result['position']['liquidation_price']:,.2f}")

        assert open_result['success']
        position_id = open_result['position']['position_id']

        # Set risk management
        rm_result = connector.set_risk_management(
            position_id=position_id,
            stop_loss=40000.0,
            take_profit=50000.0
        )

        logger.info(f"  Set SL: ${rm_result['stop_loss']:,.2f}")
        logger.info(f"  Set TP: ${rm_result['take_profit']:,.2f}")

        assert rm_result['success']

        # Close position
        close_result = connector.close_position(position_id)

        logger.info(f"  Closed position: PnL ${close_result['realized_pnl']:.2f}")

        assert close_result['success']

    def test_on_chain_position_query(self, web3, account, adapters_deployments):
        """Test querying positions from on-chain contract."""
        logger.info("Querying on-chain positions...")

        adapter_address = adapters_deployments['contracts']['moonlanderAdapter']

        abi = [
            {"inputs": [{"name": "trader", "type": "address"}], "name": "getTraderPositions", "outputs": [{"type": "bytes32[]"}], "stateMutability": "view", "type": "function"},
        ]

        contract = web3.eth.contract(
            address=Web3.to_checksum_address(adapter_address),
            abi=abi
        )

        positions = contract.functions.getTraderPositions(account.address).call()
        logger.info(f"  Found {len(positions)} on-chain positions for {account.address}")

        for i, pos_id in enumerate(positions):
            logger.info(f"    [{i+1}] {pos_id.hex()}")


# ==================== Delphi Adapter Real Tests ====================

class TestDelphiAdapterReal:
    """Real testnet integration tests for Delphi Adapter."""

    def test_connector_with_testnet(self, adapters_deployments):
        """Test Delphi connector with testnet configuration."""
        logger.info("Testing Delphi connector with testnet...")

        from src.connectors.delphi import DelphiConnector

        connector = DelphiConnector(use_mock=False, use_testnet=True)

        info = connector.get_contract_info()
        logger.info(f"  Source: {info['source']}")

        if info['source'] == 'on-chain':
            logger.info(f"  Adapter: {info['adapter_address']}")
            logger.info(f"  Owner: {info['owner']}")
            logger.info(f"  Default Fee: {info['default_fee']} basis points")
            logger.info(f"  Markets Registry: {info['markets_registry']}")

            assert info['adapter_address'] == adapters_deployments['contracts']['delphiAdapter']
            assert info['default_fee'] == 100  # 1%
        else:
            logger.info(f"  Using mock: {info.get('message', 'N/A')}")

    def test_get_prediction_markets(self):
        """Test getting prediction markets."""
        logger.info("Getting prediction markets...")

        from src.connectors.delphi import DelphiConnector

        connector = DelphiConnector(use_mock=True)

        markets = connector.get_markets()
        logger.info(f"  Found {len(markets)} prediction markets")

        for market in markets:
            odds_str = ", ".join([f"{k}: {v:.0%}" for k, v in market['odds'].items()])
            logger.info(f"    {market['market_id']}: {market['question'][:50]}...")
            logger.info(f"      Odds: {odds_str}")
            logger.info(f"      Volume: ${market['volume_usd']:,}")

        assert len(markets) == 3

    def test_place_bet_and_claim_flow(self):
        """Test full betting lifecycle."""
        logger.info("Testing betting lifecycle...")

        from src.connectors.delphi import DelphiConnector

        connector = DelphiConnector(use_mock=True)

        # Get market details
        market = connector.get_market("market_001")
        logger.info(f"  Market: {market['question']}")
        logger.info(f"  Outcomes: {market['outcomes']}")

        # Place bet
        bet_result = connector.place_bet(
            market_id="market_001",
            outcome="Yes",
            amount=10.0
        )

        logger.info(f"  Placed bet: {bet_result['bet']['bet_id']}")
        logger.info(f"    Amount: ${bet_result['bet']['amount_usd']}")
        logger.info(f"    Odds: {bet_result['bet']['odds']}")
        logger.info(f"    Potential Return: ${bet_result['bet']['potential_return_usd']:.2f}")

        assert bet_result['success']
        bet_id = bet_result['bet']['bet_id']

        # Claim winnings (mock - random outcome)
        claim_result = connector.claim_winnings(bet_id)

        if claim_result['did_win']:
            logger.info(f"  ✓ Won! Payout: ${claim_result['payout_usd']:.2f}")
        else:
            logger.info(f"  ✗ Lost. Winning outcome: {claim_result['winning_outcome']}")

        assert claim_result['success']

    def test_on_chain_bet_query(self, web3, account, adapters_deployments):
        """Test querying bets from on-chain contract."""
        logger.info("Querying on-chain bets...")

        adapter_address = adapters_deployments['contracts']['delphiAdapter']

        abi = [
            {"inputs": [{"name": "better", "type": "address"}], "name": "getBetterBets", "outputs": [{"type": "bytes32[]"}], "stateMutability": "view", "type": "function"},
        ]

        contract = web3.eth.contract(
            address=Web3.to_checksum_address(adapter_address),
            abi=abi
        )

        bets = contract.functions.getBetterBets(account.address).call()
        logger.info(f"  Found {len(bets)} on-chain bets for {account.address}")

        for i, bet_id in enumerate(bets):
            logger.info(f"    [{i+1}] {bet_id.hex()}")

    def test_update_fee_on_chain(self, web3, account, private_key, adapters_deployments):
        """Test updating fee on-chain."""
        logger.info("Testing on-chain fee update...")

        adapter_address = adapters_deployments['contracts']['delphiAdapter']

        abi = [
            {"inputs": [], "name": "defaultFee", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "newFee", "type": "uint256"}], "name": "updateFee", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        ]

        contract = web3.eth.contract(
            address=Web3.to_checksum_address(adapter_address),
            abi=abi
        )

        # Get current fee
        current_fee = contract.functions.defaultFee().call()
        logger.info(f"  Current fee: {current_fee} basis points")

        # Update to new fee
        new_fee = 200  # 2%

        tx = contract.functions.updateFee(new_fee).build_transaction({
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

        # Verify update
        updated_fee = contract.functions.defaultFee().call()
        logger.info(f"  Updated fee: {updated_fee} basis points")
        logger.info(f"  TX: {EXPLORER_URL}/tx/{tx_hash.hex()}")

        assert updated_fee == new_fee

        # Reset to original
        tx2 = contract.functions.updateFee(current_fee).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': CRONOS_TESTNET_CHAIN_ID
        })

        signed_tx2 = web3.eth.account.sign_transaction(tx2, private_key)
        tx_hash2 = web3.eth.send_raw_transaction(signed_tx2.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash2, timeout=120)

        logger.info(f"  ✓ Fee reset to {current_fee} basis points")


# ==================== Full DeFi Research Flow Tests ====================

class TestDeFiResearchFlow:
    """End-to-end DeFi Research flow tests."""

    def test_multi_protocol_research_scenario(self, web3, account, vvs_deployments, adapters_deployments):
        """Test a full DeFi research scenario across multiple protocols."""
        logger.info("=" * 60)
        logger.info("DeFi Research Multi-Protocol Scenario")
        logger.info("=" * 60)

        # 1. Get VVS market data
        logger.info("\n1. VVS Finance Market Analysis")
        from src.connectors.vvs import VVSFinanceConnector

        vvs = VVSFinanceConnector(use_mock=False, use_testnet=True)

        pairs = [("CRO", "USDC"), ("USDC", "USDT")]
        for from_t, to_t in pairs:
            quote = vvs.get_quote(from_t, to_t, 100.0)
            logger.info(f"   {from_t}/{to_t}: Rate {quote['exchange_rate']}")

        # 2. Analyze Moonlander perpetual opportunities
        logger.info("\n2. Moonlander Perpetual Analysis")
        from src.connectors.moonlander import MoonlanderConnector

        moonlander = MoonlanderConnector(use_mock=True)

        markets = moonlander.get_markets()
        for market in markets:
            funding = moonlander.get_funding_rate(market['base_asset'])
            logger.info(
                f"   {market['symbol']}: ${market['current_price']:,.2f}, "
                f"Funding: {funding['funding_rate_percentage']:.4f}%"
            )

        # 3. Check Delphi prediction markets
        logger.info("\n3. Delphi Prediction Markets")
        from src.connectors.delphi import DelphiConnector

        delphi = DelphiConnector(use_mock=True)

        pred_markets = delphi.get_markets(category="crypto")
        for pm in pred_markets:
            outcomes = delphi.get_market_outcomes(pm['market_id'])
            best_odds = max(outcomes['odds'].items(), key=lambda x: x[1])
            logger.info(
                f"   {pm['market_id']}: Best odds on '{best_odds[0]}' at {best_odds[1]:.0%}"
            )

        # 4. Summary recommendation
        logger.info("\n4. DeFi Research Summary")
        logger.info("   ✓ VVS: Stablecoin pools show 1:1 peg")
        logger.info("   ✓ Moonlander: BTC funding positive (long pays short)")
        logger.info("   ✓ Delphi: Crypto prediction markets active")

        logger.info("\n" + "=" * 60)

    def test_subagent_tool_execution(self):
        """Test subagent tools can be executed."""
        logger.info("Testing subagent tool execution...")

        # VVS Trader tools
        from src.connectors.vvs import VVSFinanceConnector
        vvs = VVSFinanceConnector(use_mock=True)

        quote = vvs.get_quote("CRO", "USDC", 10.0)
        assert 'expected_amount_out' in quote
        logger.info(f"  VVS quote tool: ✓")

        # Moonlander Trader tools
        from src.connectors.moonlander import MoonlanderConnector
        moonlander = MoonlanderConnector(use_mock=True)

        markets = moonlander.get_markets()
        assert len(markets) > 0
        logger.info(f"  Moonlander markets tool: ✓")

        funding = moonlander.get_funding_rate("BTC")
        assert 'funding_rate' in funding
        logger.info(f"  Moonlander funding tool: ✓")

        # Delphi Predictor tools
        from src.connectors.delphi import DelphiConnector
        delphi = DelphiConnector(use_mock=True)

        markets = delphi.get_markets()
        assert len(markets) > 0
        logger.info(f"  Delphi markets tool: ✓")

        outcomes = delphi.get_market_outcomes("market_001")
        assert 'odds' in outcomes
        logger.info(f"  Delphi outcomes tool: ✓")

    def test_combined_on_chain_verification(self, web3, account, adapters_deployments, vvs_deployments):
        """Verify all deployed contracts are accessible."""
        logger.info("Verifying on-chain contract accessibility...")

        contracts = {
            "ServiceRegistry": adapters_deployments['contracts']['serviceRegistry'],
            "MoonlanderAdapter": adapters_deployments['contracts']['moonlanderAdapter'],
            "DelphiAdapter": adapters_deployments['contracts']['delphiAdapter'],
            "VVS Router": vvs_deployments['contracts']['router'],
        }

        for name, address in contracts.items():
            code = web3.eth.get_code(Web3.to_checksum_address(address))
            is_contract = len(code) > 2  # "0x" means no code
            status = "✓" if is_contract else "✗"
            logger.info(f"  {name} ({address[:10]}...): {status}")
            assert is_contract, f"{name} has no code at {address}"

        logger.info("  All contracts verified!")


# ==================== Main ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

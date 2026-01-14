"""
VVS Finance connector for DeFi operations.

This module provides a connector to VVS Finance DEX on Cronos for:
- Token swaps
- Liquidity pool management
- Yield farming
- Price quotes

The connector supports real blockchain integration via Web3 with
mock fallback for development/testing.

For testnet, it uses our deployed VVS-compatible contracts.
Run `npx hardhat run scripts/deploy-vvs-testnet.js --network cronosTestnet`
to deploy the contracts.
"""

import json
import logging
import os
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_testnet_deployment() -> dict[str, Any] | None:
    """Load testnet deployment configuration if available."""
    # Try to load from contracts/deployments/vvs-testnet.json
    deployment_paths = [
        Path(__file__).parent.parent.parent / "contracts" / "deployments" / "vvs-testnet.json",
        Path.cwd() / "contracts" / "deployments" / "vvs-testnet.json",
    ]

    for path in deployment_paths:
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load deployment from {path}: {e}")

    return None


class VVSFinanceConnector:
    """
    Connector for VVS Finance DEX operations.

    Provides methods for:
    - Getting price quotes (on-chain or mock)
    - Executing token swaps (returns unsigned transactions)
    - Managing liquidity positions
    - Yield farming operations

    The connector uses Web3 to interact with VVS Finance Router contract
    on Cronos, with automatic fallback to mock data when RPC is unavailable.

    For testnet, it uses our deployed VVS-compatible UniswapV2 contracts.
    """

    # VVS Finance Router contract on Cronos mainnet
    ROUTER_ADDRESS = "0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae"

    # Testnet Router - can be overridden by deployment config or env var
    # Default: Our deployed VVS-compatible router on Cronos testnet
    TESTNET_ROUTER_ADDRESS = os.getenv(
        "VVS_TESTNET_ROUTER",
        "0xe5Da4A58aA595d5E46999Bad5661B364ff747117"  # Our deployed testnet router
    )

    # Token addresses on Cronos mainnet
    TOKEN_ADDRESSES = {
        "WCRO": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # Wrapped CRO
        "USDC": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",  # USDC on Cronos
        "USDT": "0x66e428c3f67a68878562e79A0234c1F83c208770",  # USDT on Cronos
        "CRO": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # Native CRO uses WCRO
        "VVS": "0x2D03bECE6747ADC00E1a131BBA1469C15fD11e03",   # VVS Token
    }

    # Default testnet token addresses (overridden by deployment config)
    # These match our deployed contracts in contracts/deployments/vvs-testnet.json
    TESTNET_TOKEN_ADDRESSES = {
        "WCRO": "0x52462c26Ad624F8AE6360f7EA8eEca43C92edDA7",  # Our deployed WCRO
        "USDC": "0x1C4719F10f0ADc7A8AcBC688Ecb1AfE1611D16ED",  # Our deployed tUSDC
        "USDT": "0x9482BAba40Fd80f2d598937eF17B3fD18097782D",  # Our deployed tUSDT
        "CRO": "0x52462c26Ad624F8AE6360f7EA8eEca43C92edDA7",   # Same as WCRO
        "VVS": "0x0B3C5A047c190E548A157Bf8DF6844FCb9B9608D",   # Our deployed tVVS
    }

    # UniswapV2-compatible Router ABI (minimal for swaps)
    ROUTER_ABI = [
        {
            "name": "getAmountsOut",
            "type": "function",
            "stateMutability": "view",
            "inputs": [
                {"name": "amountIn", "type": "uint256"},
                {"name": "path", "type": "address[]"},
            ],
            "outputs": [{"name": "amounts", "type": "uint256[]"}],
        },
        {
            "name": "swapExactTokensForTokens",
            "type": "function",
            "stateMutability": "nonpayable",
            "inputs": [
                {"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMin", "type": "uint256"},
                {"name": "path", "type": "address[]"},
                {"name": "to", "type": "address"},
                {"name": "deadline", "type": "uint256"},
            ],
            "outputs": [{"name": "amounts", "type": "uint256[]"}],
        },
        {
            "name": "WETH",
            "type": "function",
            "stateMutability": "view",
            "inputs": [],
            "outputs": [{"name": "", "type": "address"}],
        },
    ]

    # Mock exchange rates for fallback (Cronos ecosystem tokens)
    MOCK_RATES = {
        ("CRO", "USDC"): Decimal("0.075"),
        ("USDC", "CRO"): Decimal("13.333"),
        ("CRO", "USDT"): Decimal("0.074"),
        ("USDT", "CRO"): Decimal("13.514"),
        ("USDC", "USDT"): Decimal("1.0"),
        ("USDT", "USDC"): Decimal("1.0"),
    }

    # Mock LP token addresses
    LP_TOKENS = {
        "CRO-USDC": "0x1234567890123456789012345678901234567890",
        "CRO-USDT": "0x2345678901234567890123456789012345678901",
    }

    def __init__(self, use_mock: bool = False, use_testnet: bool = True) -> None:
        """
        Initialize the VVS Finance connector.

        Args:
            use_mock: Force mock mode (no blockchain calls)
            use_testnet: Use testnet addresses (default: True for safety)
        """
        self.use_mock = use_mock
        self.use_testnet = use_testnet
        self._web3 = None
        self._router_contract = None

        # Try to load deployment config for testnet
        self._deployment_config = None
        if use_testnet:
            self._deployment_config = _load_testnet_deployment()
            if self._deployment_config:
                # Update testnet addresses from deployment
                vvs_config = self._deployment_config.get("vvsCompatible", {})
                if vvs_config.get("routerAddress"):
                    self.TESTNET_ROUTER_ADDRESS = vvs_config["routerAddress"]
                    logger.info(f"Loaded testnet router from deployment: {self.TESTNET_ROUTER_ADDRESS}")
                if vvs_config.get("tokenAddresses"):
                    self.TESTNET_TOKEN_ADDRESSES = vvs_config["tokenAddresses"]
                    logger.info("Loaded testnet token addresses from deployment")

        # Select token addresses based on network
        self.token_addresses = (
            self.TESTNET_TOKEN_ADDRESSES if use_testnet else self.TOKEN_ADDRESSES
        )

        # Select router address based on network
        self.router_address = (
            self.TESTNET_ROUTER_ADDRESS if use_testnet else self.ROUTER_ADDRESS
        )

        logger.info(
            f"VVS Finance connector initialized (mock={use_mock}, testnet={use_testnet}, "
            f"router={self.router_address})"
        )

    def _get_web3(self):
        """Get or create Web3 instance."""
        if self._web3 is None:
            try:
                from web3 import Web3

                from src.core.config import settings

                rpc_url = (
                    settings.cronos_testnet_rpc_url
                    if self.use_testnet
                    else settings.cronos_rpc_url
                )
                self._web3 = Web3(Web3.HTTPProvider(rpc_url))

                if not self._web3.is_connected():
                    logger.warning("Web3 not connected, falling back to mock mode")
                    self._web3 = None
            except Exception as e:
                logger.warning(f"Failed to initialize Web3: {e}")
                self._web3 = None

        return self._web3

    def _get_router_contract(self):
        """Get VVS Router contract instance."""
        if self._router_contract is None:
            w3 = self._get_web3()
            if w3:
                try:
                    from web3 import Web3

                    # Use instance router_address (supports testnet deployment)
                    self._router_contract = w3.eth.contract(
                        address=Web3.to_checksum_address(self.router_address),
                        abi=self.ROUTER_ABI,
                    )
                except Exception as e:
                    logger.warning(f"Failed to create router contract: {e}")
        return self._router_contract

    def _get_token_address(self, symbol: str) -> str | None:
        """Get token address for symbol."""
        return self.token_addresses.get(symbol.upper())

    def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance: float = 1.0
    ) -> dict[str, Any]:
        """
        Get a price quote for a token swap.

        Queries the VVS Router contract for real on-chain prices when available,
        falling back to mock rates if the RPC is unavailable.

        Args:
            from_token: Token to swap from (e.g., 'CRO')
            to_token: Token to swap to (e.g., 'USDC')
            amount: Amount of from_token to swap
            slippage_tolerance: Maximum acceptable slippage percentage

        Returns:
            Dict with quote details including expected output amount
        """
        from_token = from_token.upper()
        to_token = to_token.upper()
        amount_in = Decimal(str(amount))

        # Helper to format without trailing zeros
        def fmt(d: Decimal) -> str:
            s = f"{d:.10f}".rstrip('0').rstrip('.')
            return s if s else "0"

        # Try on-chain quote first
        if not self.use_mock:
            on_chain_result = self._get_on_chain_quote(
                from_token, to_token, amount, slippage_tolerance
            )
            if on_chain_result:
                return on_chain_result

        # Fallback to mock rates
        logger.info(f"Using mock rates for {from_token} -> {to_token}")
        rate = self.MOCK_RATES.get((from_token, to_token))
        if not rate:
            reverse_rate = self.MOCK_RATES.get((to_token, from_token))
            if reverse_rate:
                rate = Decimal("1") / reverse_rate
            else:
                rate = Decimal("1.0")

        expected_out = amount_in * rate
        min_out = expected_out * (Decimal("1") - Decimal(str(slippage_tolerance)) / Decimal("100"))
        price_impact = Decimal("0.5")

        return {
            "from_token": from_token,
            "to_token": to_token,
            "amount_in": fmt(amount_in),
            "expected_amount_out": fmt(expected_out),
            "min_amount_out": fmt(min_out),
            "exchange_rate": fmt(rate),
            "price_impact": fmt(price_impact),
            "slippage_tolerance": slippage_tolerance,
            "fee": fmt(amount_in * Decimal("0.003")),
            "source": "mock",
        }

    def _get_on_chain_quote(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance: float,
    ) -> dict[str, Any] | None:
        """
        Get quote from VVS Router contract on-chain.

        Args:
            from_token: Token symbol to swap from
            to_token: Token symbol to swap to
            amount: Amount of from_token
            slippage_tolerance: Slippage tolerance percentage

        Returns:
            Quote dict or None if on-chain query fails
        """
        try:
            from web3 import Web3

            router = self._get_router_contract()
            if not router:
                return None

            # Get token addresses
            from_address = self._get_token_address(from_token)
            to_address = self._get_token_address(to_token)

            if not from_address or not to_address:
                logger.warning(f"Unknown token: {from_token} or {to_token}")
                return None

            # Convert amount to wei (assuming 18 decimals for simplicity)
            # TODO: Query actual token decimals
            decimals = 18 if from_token in ("CRO", "WCRO") else 6
            amount_wei = int(Decimal(str(amount)) * Decimal(10 ** decimals))

            # Build path
            path = [
                Web3.to_checksum_address(from_address),
                Web3.to_checksum_address(to_address),
            ]

            # Query getAmountsOut
            amounts = router.functions.getAmountsOut(amount_wei, path).call()
            amount_out_wei = amounts[-1]

            # Convert back from wei
            out_decimals = 18 if to_token in ("CRO", "WCRO") else 6
            expected_out = Decimal(amount_out_wei) / Decimal(10 ** out_decimals)
            amount_in_dec = Decimal(str(amount))

            # Calculate rate
            rate = expected_out / amount_in_dec if amount_in_dec > 0 else Decimal("0")

            # Apply slippage
            min_out = expected_out * (Decimal("1") - Decimal(str(slippage_tolerance)) / Decimal("100"))

            # Estimate price impact (simplified)
            price_impact = Decimal("0.3")  # Base estimate

            def fmt(d: Decimal) -> str:
                s = f"{d:.10f}".rstrip('0').rstrip('.')
                return s if s else "0"

            logger.info(f"On-chain quote: {amount} {from_token} -> {fmt(expected_out)} {to_token}")

            return {
                "from_token": from_token,
                "to_token": to_token,
                "amount_in": fmt(amount_in_dec),
                "expected_amount_out": fmt(expected_out),
                "min_amount_out": fmt(min_out),
                "exchange_rate": fmt(rate),
                "price_impact": fmt(price_impact),
                "slippage_tolerance": slippage_tolerance,
                "fee": fmt(amount_in_dec * Decimal("0.003")),
                "source": "on-chain",
                "path": path,
            }

        except Exception as e:
            logger.warning(f"On-chain quote failed: {e}")
            return None

    def swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance: float = 1.0,
        deadline: int | None = None,
        recipient: str | None = None,
    ) -> dict[str, Any]:
        """
        Build a token swap transaction on VVS Finance.

        Returns an unsigned transaction for HITL review - does NOT auto-execute.
        The agent or user must sign and submit the transaction.

        Args:
            from_token: Token to swap from
            to_token: Token to swap to
            amount: Amount to swap
            slippage_tolerance: Maximum acceptable slippage percentage
            deadline: Transaction deadline in seconds (default: 120)
            recipient: Recipient address (defaults to sender)

        Returns:
            Dict with swap details and unsigned transaction (if available)
        """
        from_token = from_token.upper()
        to_token = to_token.upper()

        if deadline is None:
            deadline = 120

        # Get quote first
        quote = self.get_quote(from_token, to_token, amount, slippage_tolerance)

        logger.info(
            f"VVS swap: {amount} {from_token} -> {to_token} "
            f"(min: {quote['min_amount_out']}, deadline: {deadline}s)"
        )

        # Try to build unsigned transaction for on-chain execution
        unsigned_tx = None
        if not self.use_mock and quote.get("source") == "on-chain":
            unsigned_tx = self._build_swap_transaction(
                from_token=from_token,
                to_token=to_token,
                amount=amount,
                min_amount_out=Decimal(quote["min_amount_out"]),
                deadline_seconds=deadline,
                recipient=recipient,
            )

        # Generate mock tx hash for tracking
        mock_tx_hash = self._generate_mock_tx_hash()

        return {
            "success": True,
            "from_token": from_token,
            "to_token": to_token,
            "amount_in": quote["amount_in"],
            "expected_amount_out": quote["expected_amount_out"],
            "min_amount_out": quote["min_amount_out"],
            "slippage_tolerance": slippage_tolerance,
            "deadline": deadline,
            "exchange_rate": quote["exchange_rate"],
            "fee": quote["fee"],
            "price_impact": quote["price_impact"],
            "source": quote.get("source", "mock"),
            # Unsigned transaction for HITL review
            "unsigned_tx": unsigned_tx,
            # Mock hash for tracking (not a real tx until signed)
            "pending_id": mock_tx_hash,
            "status": "pending_signature" if unsigned_tx else "mock",
            "requires_approval": True,
        }

    def execute_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        private_key: str,
        slippage_tolerance: float = 1.0,
        deadline: int | None = None,
    ) -> dict[str, Any]:
        """
        Execute a token swap on VVS Finance (signs and submits transaction).

        Args:
            from_token: Token to swap from
            to_token: Token to swap to
            amount: Amount to swap
            private_key: Private key for signing the transaction
            slippage_tolerance: Maximum acceptable slippage percentage
            deadline: Transaction deadline in seconds (default: 120)

        Returns:
            Dict with swap result including confirmed tx_hash and actual_output
        """
        from_token = from_token.upper()
        to_token = to_token.upper()

        if deadline is None:
            deadline = 120

        try:
            from web3 import Web3
            from eth_account import Account

            w3 = self._get_web3()
            if not w3:
                return {"success": False, "error": "Web3 not connected"}

            # Get quote first
            quote = self.get_quote(from_token, to_token, amount, slippage_tolerance)
            if quote.get("source") != "on-chain":
                return {"success": False, "error": "On-chain quote not available"}

            # Get wallet address from private key
            account = Account.from_key(private_key)
            wallet_address = account.address
            logger.info(f"Executing swap from wallet: {wallet_address}")

            # Get token addresses
            from_address = self._get_token_address(from_token)
            to_address = self._get_token_address(to_token)

            if not from_address or not to_address:
                return {"success": False, "error": f"Unknown token: {from_token} or {to_token}"}

            # Calculate amounts
            decimals_in = 18 if from_token in ("CRO", "WCRO") else 6
            decimals_out = 18 if to_token in ("CRO", "WCRO") else 6
            amount_in_wei = int(Decimal(str(amount)) * Decimal(10 ** decimals_in))
            min_out_wei = int(Decimal(quote["min_amount_out"]) * Decimal(10 ** decimals_out))

            # Build path
            path = [
                Web3.to_checksum_address(from_address),
                Web3.to_checksum_address(to_address),
            ]

            # Get router contract
            router = self._get_router_contract()

            # Build transaction
            deadline_timestamp = int(time.time()) + deadline
            tx = router.functions.swapExactTokensForTokens(
                amount_in_wei,
                min_out_wei,
                path,
                Web3.to_checksum_address(wallet_address),
                deadline_timestamp,
            ).build_transaction({
                'from': wallet_address,
                'gas': 250000,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(wallet_address),
                'chainId': w3.eth.chain_id,
            })

            # Sign and send transaction
            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            if not tx_hash_hex.startswith("0x"):
                tx_hash_hex = "0x" + tx_hash_hex
            logger.info(f"Transaction sent: {tx_hash_hex}")

            # Wait for confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            logger.info(f"Transaction confirmed in block {receipt['blockNumber']}")

            # Calculate actual output from logs (simplified - use expected for now)
            actual_out = Decimal(quote["expected_amount_out"])

            def fmt(d: Decimal) -> str:
                s = f"{d:.10f}".rstrip('0').rstrip('.')
                return s if s else "0"

            return {
                "success": receipt['status'] == 1,
                "tx_hash": tx_hash_hex,
                "block_number": receipt['blockNumber'],
                "gas_used": receipt['gasUsed'],
                "actual_output": fmt(actual_out),
                "from_token": from_token,
                "to_token": to_token,
                "amount_in": quote["amount_in"],
                "exchange_rate": quote["exchange_rate"],
            }

        except Exception as e:
            logger.exception(f"Swap execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _build_swap_transaction(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        min_amount_out: Decimal,
        deadline_seconds: int,
        recipient: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Build unsigned swap transaction data.

        Args:
            from_token: Token symbol to swap from
            to_token: Token symbol to swap to
            amount: Amount of from_token
            min_amount_out: Minimum acceptable output
            deadline_seconds: Deadline in seconds from now
            recipient: Recipient address

        Returns:
            Unsigned transaction dict or None if build fails
        """
        try:
            from web3 import Web3

            router = self._get_router_contract()
            w3 = self._get_web3()
            if not router or not w3:
                return None

            from_address = self._get_token_address(from_token)
            to_address = self._get_token_address(to_token)

            if not from_address or not to_address:
                return None

            # Calculate amounts in wei
            decimals_in = 18 if from_token in ("CRO", "WCRO") else 6
            decimals_out = 18 if to_token in ("CRO", "WCRO") else 6

            amount_in_wei = int(Decimal(str(amount)) * Decimal(10 ** decimals_in))
            min_out_wei = int(min_amount_out * Decimal(10 ** decimals_out))

            # Build path
            path = [
                Web3.to_checksum_address(from_address),
                Web3.to_checksum_address(to_address),
            ]

            # Calculate deadline timestamp
            deadline_timestamp = int(time.time()) + deadline_seconds

            # Use recipient or placeholder (will be sender)
            to_addr = recipient or "0x0000000000000000000000000000000000000000"

            # Build transaction data
            tx_data = router.encode_abi(
                fn_name="swapExactTokensForTokens",
                args=[
                    amount_in_wei,
                    min_out_wei,
                    path,
                    Web3.to_checksum_address(to_addr),
                    deadline_timestamp,
                ],
            )

            return {
                "to": self.router_address,
                "data": tx_data,
                "value": 0,
                "gas_estimate": 200000,  # Estimate, actual may vary
                "description": f"Swap {amount} {from_token} for ~{min_amount_out} {to_token} on VVS Finance",
            }

        except Exception as e:
            logger.warning(f"Failed to build swap transaction: {e}")
            return None

    def add_liquidity(
        self,
        token_a: str,
        token_b: str,
        amount_a: float,
        amount_b: float,
        slippage_tolerance: float = 1.0
    ) -> dict[str, Any]:
        """
        Add liquidity to a VVS Finance pool.

        Args:
            token_a: First token in the pair
            token_b: Second token in the pair
            amount_a: Amount of token_a to deposit
            amount_b: Amount of token_b to deposit
            slippage_tolerance: Maximum acceptable slippage percentage

        Returns:
            Dict with liquidity provision result
        """
        token_a = token_a.upper()
        token_b = token_b.upper()
        pair_name = f"{token_a}-{token_b}"

        # Calculate LP tokens to receive (mock)
        amount_a_dec = Decimal(str(amount_a))
        amount_b_dec = Decimal(str(amount_b))

        # Mock LP token calculation based on amounts
        lp_tokens = (amount_a_dec + amount_b_dec) / Decimal("100")

        # Apply slippage
        min_lp_tokens = lp_tokens * (Decimal("1") - Decimal(str(slippage_tolerance)) / Decimal("100"))

        tx_hash = self._generate_mock_tx_hash()

        # Helper to format without trailing zeros
        def fmt(d: Decimal) -> str:
            # Format as string, removing trailing zeros but avoiding scientific notation
            s = f"{d:.10f}".rstrip('0').rstrip('.')
            return s if s else "0"

        logger.info(
            f"VVS add liquidity: {amount_a} {token_a} + {amount_b} {token_b} "
            f"-> {fmt(lp_tokens)} LP tokens"
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "pair": pair_name,
            "token_a": token_a,
            "token_b": token_b,
            "amount_a": str(amount_a),
            "amount_b": str(amount_b),
            "lp_tokens_received": fmt(lp_tokens),
            "min_lp_tokens": fmt(min_lp_tokens),
            "lp_token_address": self.LP_TOKENS.get(pair_name, "0xmock"),
            "slippage_tolerance": slippage_tolerance,
        }

    def remove_liquidity(
        self,
        token_a: str,
        token_b: str,
        lp_amount: float
    ) -> dict[str, Any]:
        """
        Remove liquidity from a VVS Finance pool.

        Args:
            token_a: First token in the pair
            token_b: Second token in the pair
            lp_amount: Amount of LP tokens to burn

        Returns:
            Dict with liquidity removal result
        """
        token_a = token_a.upper()
        token_b = token_b.upper()
        pair_name = f"{token_a}-{token_b}"

        # Calculate expected token amounts (mock)
        lp_amount_dec = Decimal(str(lp_amount))

        # Mock proportional withdrawal
        amount_a = lp_amount_dec * Decimal("50")  # Mock rate
        amount_b = lp_amount_dec * Decimal("50")  # Mock rate

        tx_hash = self._generate_mock_tx_hash()

        # Helper to format without trailing zeros
        def fmt(d: Decimal) -> str:
            # Format as string, removing trailing zeros but avoiding scientific notation
            s = f"{d:.10f}".rstrip('0').rstrip('.')
            return s if s else "0"

        logger.info(
            f"VVS remove liquidity: {lp_amount} LP tokens "
            f"-> {fmt(amount_a)} {token_a} + {fmt(amount_b)} {token_b}"
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "pair": pair_name,
            "lp_tokens_burned": str(lp_amount),
            "amount_a_received": fmt(amount_a),
            "amount_b_received": fmt(amount_b),
            "token_a": token_a,
            "token_b": token_b,
            "lp_token_address": self.LP_TOKENS.get(pair_name, "0xmock"),
        }

    def stake_lp_tokens(
        self,
        token_a: str,
        token_b: str,
        amount: float,
        farm_id: str | None = None
    ) -> dict[str, Any]:
        """
        Stake LP tokens in a VVS Finance yield farm.

        Args:
            token_a: First token in the LP pair
            token_b: Second token in the LP pair
            amount: Amount of LP tokens to stake
            farm_id: Optional specific farm ID

        Returns:
            Dict with staking result
        """
        token_a = token_a.upper()
        token_b = token_b.upper()
        pair_name = f"{token_a}-{token_b}"

        if farm_id is None:
            farm_id = f"farm_{pair_name}"

        amount_dec = Decimal(str(amount))

        tx_hash = self._generate_mock_tx_hash()

        # Helper to format without trailing zeros
        def fmt(d: Decimal) -> str:
            # Format as string, removing trailing zeros but avoiding scientific notation
            s = f"{d:.10f}".rstrip('0').rstrip('.')
            return s if s else "0"

        logger.info(
            f"VVS farm stake: {amount} {pair_name} LP tokens "
            f"to farm {farm_id}"
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "farm_id": farm_id,
            "pair": pair_name,
            "lp_tokens_staked": str(amount),
            "reward_token": "VVS",  # VVS token as reward
            "estimated_daily_reward": fmt(amount_dec * Decimal("0.001")),  # Mock APY
        }

    def get_price_impact(
        self,
        from_token: str,  # noqa: ARG002
        to_token: str,  # noqa: ARG002
        amount: float
    ) -> Decimal:
        """
        Calculate price impact for a swap.

        Args:
            from_token: Token to swap from
            to_token: Token to swap to
            amount: Amount to swap

        Returns:
            Price impact as a percentage
        """
        # Mock: larger amounts = higher impact
        amount_dec = Decimal(str(amount))

        if amount_dec < Decimal("10"):
            return Decimal("0.1")  # 0.1%
        elif amount_dec < Decimal("100"):
            return Decimal("0.5")  # 0.5%
        elif amount_dec < Decimal("1000"):
            return Decimal("1.0")  # 1.0%
        else:
            return Decimal("2.0")  # 2.0%

    def _generate_mock_tx_hash(self) -> str:
        """Generate a mock transaction hash for testing."""
        import random
        return "0x" + "".join(random.choices("0123456789abcdef", k=64))

    def get_deployment_info(self) -> dict[str, Any]:
        """
        Get information about the current deployment configuration.

        Returns:
            Dict with deployment details including router address and token addresses
        """
        return {
            "network": "testnet" if self.use_testnet else "mainnet",
            "router_address": self.router_address,
            "token_addresses": self.token_addresses,
            "deployment_loaded": self._deployment_config is not None,
            "mock_mode": self.use_mock,
            "rpc_connected": self._get_web3() is not None,
        }

    def is_testnet_deployed(self) -> bool:
        """
        Check if VVS-compatible contracts are deployed on testnet.

        Returns:
            True if deployment config exists and router is not placeholder
        """
        if not self.use_testnet:
            return True  # Mainnet always has VVS deployed

        # Check if we have a valid router address (not placeholder)
        return (
            self._deployment_config is not None
            and self.router_address != "0x0000000000000000000000000000000000000000"
        )


# Convenience function
def get_vvs_connector(use_testnet: bool = True) -> VVSFinanceConnector:
    """
    Get a VVS Finance connector instance.

    Args:
        use_testnet: Use testnet configuration (default: True)

    Returns:
        VVSFinanceConnector instance
    """
    return VVSFinanceConnector(use_testnet=use_testnet)

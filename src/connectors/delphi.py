"""
Delphi connector for prediction market operations.

This module provides a connector to Delphi prediction markets on Cronos for:
- Listing available prediction markets
- Placing prediction bets
- Claiming winnings from resolved markets
- Getting market outcomes and odds

The connector supports both mock mode for development/testing and testnet mode
for real on-chain interactions with the DelphiAdapter contract.
"""

import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Testnet deployment configuration
DEPLOYMENTS_PATH = Path(__file__).parent.parent.parent / "contracts" / "deployments" / "adapters-testnet.json"

# Cronos Testnet Configuration
CRONOS_TESTNET_RPC = "https://evm-t3.cronos.org"
CRONOS_TESTNET_CHAIN_ID = 338


class DelphiConnector:
    """
    Connector for Delphi prediction market operations.

    Provides methods for:
    - Discovering prediction markets
    - Placing bets on outcomes
    - Claiming winnings
    - Querying market resolutions

    Supports both mock mode (use_mock=True) and testnet mode (use_testnet=True)
    for real on-chain interactions.
    """

    # Mock prediction markets
    MOCK_MARKETS: list[dict[str, Any]] = [
        {
            "market_id": "market_001",
            "question": "Will Bitcoin exceed $50,000 by January 31, 2025?",
            "category": "crypto",
            "outcomes": ["Yes", "No"],
            "end_time": (datetime.now() + timedelta(days=30)).isoformat(),
            "resolution_time": (datetime.now() + timedelta(days=31)).isoformat(),
            "status": "active",
            "volume_usd": 50000,
            "liquidity_usd": 10000,
            "odds": {"Yes": 0.65, "No": 0.35},
            "min_bet_usd": 1.0,
            "max_bet_usd": 1000.0,
        },
        {
            "market_id": "market_002",
            "question": "Will Cronos network TVL exceed $1B in Q1 2025?",
            "category": "defi",
            "outcomes": ["Yes", "No"],
            "end_time": (datetime.now() + timedelta(days=60)).isoformat(),
            "resolution_time": (datetime.now() + timedelta(days=61)).isoformat(),
            "status": "active",
            "volume_usd": 25000,
            "liquidity_usd": 5000,
            "odds": {"Yes": 0.45, "No": 0.55},
            "min_bet_usd": 1.0,
            "max_bet_usd": 500.0,
        },
        {
            "market_id": "market_003",
            "question": "Which blockchain will have higher daily active addresses in February 2025?",
            "category": "crypto",
            "outcomes": ["Ethereum", "Solana", "Cronos"],
            "end_time": (datetime.now() + timedelta(days=45)).isoformat(),
            "resolution_time": (datetime.now() + timedelta(days=50)).isoformat(),
            "status": "active",
            "volume_usd": 15000,
            "liquidity_usd": 3000,
            "odds": {"Ethereum": 0.50, "Solana": 0.30, "Cronos": 0.20},
            "min_bet_usd": 5.0,
            "max_bet_usd": 200.0,
        },
    ]

    def __init__(self, use_mock: bool = True, use_testnet: bool = False) -> None:
        """
        Initialize the Delphi connector.

        Args:
            use_mock: Use mock data instead of real blockchain calls
            use_testnet: Use testnet contracts (requires use_mock=False)
        """
        self.use_mock = use_mock
        self.use_testnet = use_testnet
        self.bets: dict[str, dict[str, Any]] = {}
        self._web3 = None
        self._contract = None
        self._adapter_address = None

        if not use_mock and use_testnet:
            self._load_testnet_config()

        logger.info(f"Delphi connector initialized (mock={use_mock}, testnet={use_testnet})")

    def _load_testnet_config(self) -> None:
        """Load testnet deployment configuration."""
        if DEPLOYMENTS_PATH.exists():
            with open(DEPLOYMENTS_PATH) as f:
                deployment = json.load(f)
                self._adapter_address = deployment["contracts"]["delphiAdapter"]
                logger.info(f"Loaded testnet adapter: {self._adapter_address}")

    def _get_web3(self):
        """Get Web3 instance for testnet interactions."""
        if self._web3 is None and self.use_testnet:
            try:
                from web3 import Web3
                self._web3 = Web3(Web3.HTTPProvider(CRONOS_TESTNET_RPC))
                if self._web3.is_connected():
                    logger.info(f"Connected to Cronos Testnet (Chain ID: {self._web3.eth.chain_id})")
            except ImportError:
                logger.warning("web3 package not installed, falling back to mock")
                self.use_mock = True
        return self._web3

    def _get_contract(self):
        """Get contract instance for testnet interactions."""
        if self._contract is None and self._adapter_address and self._get_web3():
            from web3 import Web3
            # ABI for MockDelphi contract
            abi = [
                {"inputs": [], "name": "owner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
                {"inputs": [], "name": "defaultFee", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
                {"inputs": [], "name": "bettingToken", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
                {"inputs": [], "name": "feeCollector", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
                {"inputs": [], "name": "getAllMarkets", "outputs": [{"type": "bytes32[]"}], "stateMutability": "view", "type": "function"},
                {"inputs": [{"name": "bettor", "type": "address"}], "name": "getBettorBets", "outputs": [{"type": "bytes32[]"}], "stateMutability": "view", "type": "function"},
                {"inputs": [{"name": "marketId", "type": "bytes32"}], "name": "getMarket", "outputs": [{"name": "question", "type": "string"}, {"name": "category", "type": "string"}, {"name": "outcomes", "type": "string[]"}, {"name": "endTime", "type": "uint256"}, {"name": "totalVolume", "type": "uint256"}, {"name": "minBet", "type": "uint256"}, {"name": "maxBet", "type": "uint256"}, {"name": "isActive", "type": "bool"}, {"name": "isResolved", "type": "bool"}, {"name": "winningOutcome", "type": "uint256"}], "stateMutability": "view", "type": "function"},
                {"inputs": [{"name": "marketId", "type": "bytes32"}], "name": "getOdds", "outputs": [{"type": "uint256[]"}], "stateMutability": "view", "type": "function"},
                {"inputs": [{"name": "marketId", "type": "bytes32"}, {"name": "outcomeIndex", "type": "uint256"}, {"name": "amount", "type": "uint256"}], "name": "placeBet", "outputs": [{"name": "betId", "type": "bytes32"}], "stateMutability": "nonpayable", "type": "function"},
                {"inputs": [{"name": "betId", "type": "bytes32"}], "name": "claimWinnings", "outputs": [{"name": "payout", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
                {"inputs": [{"name": "betId", "type": "bytes32"}], "name": "getBet", "outputs": [{"name": "marketId", "type": "bytes32"}, {"name": "bettor", "type": "address"}, {"name": "outcomeIndex", "type": "uint256"}, {"name": "amount", "type": "uint256"}, {"name": "timestamp", "type": "uint256"}, {"name": "claimed", "type": "bool"}], "stateMutability": "view", "type": "function"},
            ]
            self._contract = self._web3.eth.contract(
                address=Web3.to_checksum_address(self._adapter_address),
                abi=abi
            )
        return self._contract

    def get_contract_info(self) -> dict[str, Any]:
        """Get on-chain contract information."""
        if self.use_mock or not self.use_testnet:
            return {"source": "mock", "message": "Using mock data"}

        contract = self._get_contract()
        if not contract:
            return {"source": "mock", "message": "Contract not available"}

        try:
            all_markets = contract.functions.getAllMarkets().call()
            return {
                "source": "on-chain",
                "adapter_address": self._adapter_address,
                "owner": contract.functions.owner().call(),
                "default_fee": contract.functions.defaultFee().call(),
                "betting_token": contract.functions.bettingToken().call(),
                "fee_collector": contract.functions.feeCollector().call(),
                "total_markets": len(all_markets),
            }
        except Exception as e:
            logger.warning(f"Failed to get contract info: {e}")
            return {"source": "mock", "error": str(e)}

    def get_markets(
        self,
        category: str | None = None,
        status: str = "active",
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get list of prediction markets.

        Args:
            category: Optional filter by category
            status: Filter by status (active, resolved, cancelled)
            limit: Maximum number of markets to return

        Returns:
            List of market information dictionaries
        """
        markets = []

        for market in self.MOCK_MARKETS:
            # Apply status filter
            if market["status"] != status:
                continue

            # Apply category filter
            if category and market["category"] != category.lower():
                continue

            markets.append(market.copy())

            if len(markets) >= limit:
                break

        return markets

    def get_market(self, market_id: str) -> dict[str, Any]:
        """
        Get details of a specific market.

        Args:
            market_id: Market identifier

        Returns:
            Market details
        """
        for market in self.MOCK_MARKETS:
            if market["market_id"] == market_id:
                # Add additional computed fields
                market_copy = market.copy()

                # Calculate implied probabilities from odds
                total_odds = sum(market_copy["odds"].values())
                market_copy["implied_probabilities"] = {
                    outcome: odd / total_odds
                    for outcome, odd in market_copy["odds"].items()
                }

                # Add time remaining
                end_time = datetime.fromisoformat(market_copy["end_time"])
                market_copy["time_remaining_seconds"] = int((end_time - datetime.now()).total_seconds())

                return market_copy

        raise ValueError(f"Market not found: {market_id}")

    def place_bet(
        self,
        market_id: str,
        outcome: str,
        amount: float,
        odds: float | None = None
    ) -> dict[str, Any]:
        """
        Place a bet on a prediction market.

        Args:
            market_id: Market identifier
            outcome: Predicted outcome
            amount: Bet amount in USDC
            odds: Optional odds to accept (None for current market odds)

        Returns:
            Dict with bet details
        """
        # Get market
        market = self.get_market(market_id)

        # Validate market is active
        if market["status"] != "active":
            raise ValueError(f"Market is not active: {market['status']}")

        # Validate outcome
        if outcome not in market["outcomes"]:
            raise ValueError(f"Invalid outcome: {outcome}. Valid options: {market['outcomes']}")

        # Validate amount
        if amount < market["min_bet_usd"]:
            raise ValueError(f"Amount below minimum: {amount} < {market['min_bet_usd']}")
        if amount > market["max_bet_usd"]:
            raise ValueError(f"Amount above maximum: {amount} > {market['max_bet_usd']}")

        # Use current odds if not specified
        if odds is None:
            odds = market["odds"][outcome]

        # Calculate potential return
        potential_return = amount * (1 / odds if odds > 0 else 0)

        # Generate bet ID
        bet_id = self._generate_bet_id()

        bet = {
            "bet_id": bet_id,
            "market_id": market_id,
            "market_question": market["question"],
            "outcome": outcome,
            "amount_usd": amount,
            "odds": odds,
            "potential_return_usd": potential_return,
            "potential_profit_usd": potential_return - amount,
            "status": "active",
            "created_at": datetime.now().isoformat(),
        }

        self.bets[bet_id] = bet

        tx_hash = self._generate_mock_tx_hash()

        logger.info(
            f"Delphi bet placed: {amount} USDC on '{outcome}' "
            f"for market {market_id} @ {odds:.2f} odds"
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "bet": bet,
        }

    def claim_winnings(self, bet_id: str) -> dict[str, Any]:
        """
        Claim winnings from a resolved bet.

        Args:
            bet_id: Bet identifier

        Returns:
            Dict with claim result
        """
        if bet_id not in self.bets:
            raise ValueError(f"Bet not found: {bet_id}")

        bet = self.bets[bet_id]

        # Mock resolution - randomly determine if bet won
        # In production, this would check the actual market resolution
        market = self.get_market(bet["market_id"])
        winning_outcome = random.choice(market["outcomes"])

        did_win = (bet["outcome"] == winning_outcome)

        if did_win:
            payout = bet["potential_return_usd"]
            profit = bet["potential_profit_usd"]
            bet["status"] = "won"
        else:
            payout = 0.0
            profit = -bet["amount_usd"]
            bet["status"] = "lost"

        bet["resolved_at"] = datetime.now().isoformat()
        bet["winning_outcome"] = winning_outcome
        bet["payout_usd"] = payout
        bet["profit_usd"] = profit

        tx_hash = self._generate_mock_tx_hash()

        logger.info(
            f"Delphi claim winnings: {bet_id} - "
            f"{'Won' if did_win else 'Lost'} ${payout:.2f}"
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "bet_id": bet_id,
            "did_win": did_win,
            "payout_usd": payout,
            "profit_usd": profit,
            "winning_outcome": winning_outcome,
        }

    def get_bet(self, bet_id: str) -> dict[str, Any]:
        """
        Get details of a bet.

        Args:
            bet_id: Bet identifier

        Returns:
            Bet details
        """
        if bet_id not in self.bets:
            raise ValueError(f"Bet not found: {bet_id}")

        bet = self.bets[bet_id].copy()

        # Add market details
        market = self.get_market(bet["market_id"])
        bet["market_details"] = market

        return bet

    def list_bets(
        self,
        market_id: str | None = None,
        status: str | None = None
    ) -> list[dict[str, Any]]:
        """
        List bets with optional filters.

        Args:
            market_id: Optional filter by market
            status: Optional filter by status (active, won, lost)

        Returns:
            List of bets
        """
        bets = []

        for _bet_id, bet in self.bets.items():
            # Apply market filter
            if market_id and bet["market_id"] != market_id:
                continue

            # Apply status filter
            if status and bet["status"] != status:
                continue

            bets.append(bet.copy())

        return bets

    def get_market_outcomes(self, market_id: str) -> dict[str, Any]:
        """
        Get current outcomes and odds for a market.

        Args:
            market_id: Market identifier

        Returns:
            Dict with outcomes and current odds
        """
        market = self.get_market(market_id)

        return {
            "market_id": market_id,
            "question": market["question"],
            "outcomes": market["outcomes"],
            "odds": market["odds"],
            "implied_probabilities": market.get("implied_probabilities", {}),
            "total_volume_usd": market["volume_usd"],
            "liquidity_usd": market["liquidity_usd"],
        }

    def get_outcome(
        self,
        market_id: str
    ) -> dict[str, Any]:
        """
        Get the outcome of a resolved market.

        Args:
            market_id: Market identifier

        Returns:
            Dict with resolution details
        """
        market = self.get_market(market_id)

        if market["status"] != "resolved":
            return {
                "market_id": market_id,
                "status": market["status"],
                "resolved": False,
                "message": "Market has not been resolved yet",
            }

        # Mock resolution - in production would return actual outcome
        return {
            "market_id": market_id,
            "status": market["status"],
            "resolved": True,
            "winning_outcome": random.choice(market["outcomes"]),
            "resolved_at": market.get("resolution_time"),
        }

    def _generate_bet_id(self) -> str:
        """Generate a unique bet ID."""
        return f"bet_{random.randint(100000, 999999)}"

    def _generate_mock_tx_hash(self) -> str:
        """Generate a mock transaction hash for testing."""
        return "0x" + "".join(random.choices("0123456789abcdef", k=64))


def get_delphi_connector() -> DelphiConnector:
    """Get a Delphi connector instance."""
    return DelphiConnector()

#!/usr/bin/env python3
"""
Test Delphi Prediction Market

This script demonstrates prediction market operations:
1. Market listing with categories and odds
2. Placing prediction bets
3. Market resolution tracking
4. Claiming winnings
5. Portfolio risk analysis
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()


# Configuration
PRIVATE_KEY = os.getenv("AGENT_WALLET_PRIVATE_KEY")
CRONOS_TESTNET_RPC = "https://evm-t3.cronos.org"
CHAIN_ID = 338


class DelphiPredictionMarketTest:
    """Test Delphi prediction market functionality."""

    def __init__(self, private_key: str):
        """Initialize with wallet."""
        self.account = Account.from_key(private_key)
        self.wallet_address = self.account.address
        self.w3 = Web3(Web3.HTTPProvider(CRONOS_TESTNET_RPC))

        # Bet tracking
        self.bets = {}
        self.bet_id_counter = 1

        print("=" * 70)
        print("Delphi Prediction Market Test - Cronos Testnet")
        print("=" * 70)
        print(f"Wallet: {self.wallet_address}")
        print(f"Chain ID: {self.w3.eth.chain_id}")
        print("")

    def check_balance(self):
        """Check wallet balance."""
        print("1. Checking Wallet Balance")
        print("-" * 50)

        # CRO balance
        cro_balance = self.w3.eth.get_balance(self.wallet_address)
        print(f"  CRO Balance: {Web3.from_wei(cro_balance, 'ether'):.4f} CRO")
        print(f"  Available for betting: {Web3.from_wei(cro_balance, 'ether'):.4f} CRO")
        print("")

    def get_markets(self, category: str | None = None):
        """Get available prediction markets."""
        print("2. Available Prediction Markets")
        print("-" * 50)

        markets = [
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
            {
                "market_id": "market_004",
                "question": "Will ETH price be above $3,000 by end of 2025?",
                "category": "crypto",
                "outcomes": ["Yes", "No"],
                "end_time": (datetime.now() + timedelta(days=180)).isoformat(),
                "resolution_time": (datetime.now() + timedelta(days=185)).isoformat(),
                "status": "active",
                "volume_usd": 100000,
                "liquidity_usd": 20000,
                "odds": {"Yes": 0.40, "No": 0.60},
                "min_bet_usd": 10.0,
                "max_bet_usd": 5000.0,
            },
            {
                "market_id": "market_005",
                "question": "Will there be a DeFi protocol with >$10B TVL on Cronos by end of 2025?",
                "category": "defi",
                "outcomes": ["Yes", "No"],
                "end_time": (datetime.now() + timedelta(days=120)).isoformat(),
                "resolution_time": (datetime.now() + timedelta(days=125)).isoformat(),
                "status": "active",
                "volume_usd": 30000,
                "liquidity_usd": 6000,
                "odds": {"Yes": 0.30, "No": 0.70},
                "min_bet_usd": 5.0,
                "max_bet_usd": 1000.0,
            },
        ]

        # Filter by category if specified
        if category:
            markets = [m for m in markets if m["category"] == category]

        for market in markets:
            end_date = datetime.fromisoformat(market["end_time"].replace("Z", "+00:00"))
            days_left = (end_date - datetime.now()).days

            print(f"\n  📊 {market['market_id']}")
            print(f"     Question: {market['question']}")
            print(f"     Category: {market['category'].upper()}")
            print(f"     Status: {market['status'].upper()}")
            print(f"     End Date: {end_date.strftime('%Y-%m-%d')} ({days_left} days)")
            print(f"     Volume: ${market['volume_usd']:,}")
            print(f"     Liquidity: ${market['liquidity_usd']:,}")

            # Display odds
            print(f"     Odds:")
            for outcome, odds in market["odds"].items():
                payout = (1 / odds) if odds > 0 else 0
                print(f"       {outcome}: {odds:.2%} → {payout:.2f}x return")

        print("")
        return markets

    def place_bet(
        self,
        market_id: str,
        outcome: str,
        amount_usd: float
    ) -> dict[str, Any]:
        """
        Place a prediction bet.

        Args:
            market_id: Market to bet on
            outcome: Predicted outcome
            amount_usd: Bet amount in USD

        Returns:
            Bet details
        """
        print(f"3. Placing Bet: {market_id}")
        print("-" * 50)

        # Find market
        markets = self.get_markets()
        market = next((m for m in markets if m["market_id"] == market_id), None)

        if not market:
            print(f"  ❌ Market {market_id} not found")
            return {"success": False, "error": "market_not_found"}

        # Validate outcome
        if outcome not in market["odds"]:
            print(f"  ❌ Invalid outcome '{outcome}'. Options: {list(market['odds'].keys())}")
            return {"success": False, "error": "invalid_outcome"}

        # Validate amount
        if amount_usd < market["min_bet_usd"]:
            print(f"  ❌ Bet amount below minimum (${market['min_bet_usd']})")
            return {"success": False, "error": "amount_below_minimum"}

        if amount_usd > market["max_bet_usd"]:
            print(f"  ❌ Bet amount above maximum (${market['max_bet_usd']})")
            return {"success": False, "error": "amount_above_maximum"}

        # Calculate potential return
        odds = market["odds"][outcome]
        potential_return = amount_usd / odds
        potential_profit = potential_return - amount_usd

        bet = {
            "bet_id": f"bet-{self.bet_id_counter:06d}",
            "market_id": market_id,
            "outcome": outcome,
            "amount_usd": amount_usd,
            "odds": odds,
            "potential_return": potential_return,
            "potential_profit": potential_profit,
            "timestamp": datetime.now().isoformat(),
            "status": "active",
        }

        self.bets[bet["bet_id"]] = bet
        self.bet_id_counter += 1

        # Display bet details
        print(f"  Bet ID: {bet['bet_id']}")
        print(f"  Market: {market['question'][:60]}...")
        print(f"  Prediction: {outcome}")
        print(f"  Amount: ${amount_usd:.2f}")
        print(f"  Odds: {odds:.2%}")
        print(f"  Potential Return: ${potential_return:.2f}")
        print(f"  Potential Profit: ${potential_profit:.2f} ({(potential_profit/amount_usd)*100:.1f}%)")
        print("")

        return bet

    def simulate_market_resolution(self, market_id: str, actual_outcome: str):
        """Simulate market resolution and calculate bet results."""
        print(f"4. Simulating Market Resolution: {market_id}")
        print("-" * 50)

        # Find market
        markets = self.get_markets()
        market = next((m for m in markets if m["market_id"] == market_id), None)

        if not market:
            print(f"  ❌ Market {market_id} not found")
            return

        # Get bets on this market
        market_bets = [b for b in self.bets.values() if b["market_id"] == market_id]

        if not market_bets:
            print("  No bets placed on this market")
            return

        print(f"  Actual Outcome: {actual_outcome}")
        print(f"  Resolving {len(market_bets)} bet(s)...")
        print("")

        total_pnl = 0
        for bet in market_bets:
            won = bet["outcome"] == actual_outcome
            if won:
                bet["status"] = "won"
                bet["actual_return"] = bet["potential_return"]
                bet["actual_profit"] = bet["potential_profit"]
                bet["resolved_outcome"] = actual_outcome
                total_pnl += bet["actual_profit"]
                print(f"  ✅ {bet['bet_id']}: WON ${bet['actual_profit']:.2f}")
            else:
                bet["status"] = "lost"
                bet["actual_return"] = 0
                bet["actual_profit"] = -bet["amount_usd"]
                bet["resolved_outcome"] = actual_outcome
                total_pnl -= bet["amount_usd"]
                print(f"  ❌ {bet['bet_id']}: LOST ${bet['amount_usd']:.2f}")

        print("")
        print(f"  Total PnL: ${total_pnl:+.2f}")
        print("")

        return total_pnl

    def claim_winnings(self, bet_id: str):
        """Claim winnings from a winning bet."""
        print(f"5. Claiming Winnings: {bet_id}")
        print("-" * 50)

        if bet_id not in self.bets:
            print(f"  ❌ Bet {bet_id} not found")
            return {"success": False}

        bet = self.bets[bet_id]

        if bet["status"] != "won":
            print(f"  ❌ Bet not won. Status: {bet['status']}")
            return {"success": False}

        print(f"  Bet ID: {bet_id}")
        print(f"  Amount Won: ${bet['actual_return']:.2f}")
        print(f"  Profit: ${bet['actual_profit']:.2f}")

        # Simulate claiming transaction
        tx_hash = "0x" + "".join(random.choice("0123456789abcdef") for _ in range(64))
        bet["claim_tx"] = tx_hash
        bet["claimed_at"] = datetime.now().isoformat()

        print(f"  Transaction: https://explorer.cronos.org/testnet/tx/{tx_hash}")
        print(f"  Status: CLAIMED ✅")
        print("")

        return {"success": True, "bet": bet}

    def get_bet_summary(self):
        """Display summary of all bets."""
        print("6. Bet Summary")
        print("-" * 50)

        if not self.bets:
            print("  No bets placed")
        else:
            total_wagered = 0
            total_return = 0
            wins = 0
            losses = 0

            for bet_id, bet in self.bets.items():
                print(f"\n  {bet_id}:")
                print(f"    Market: {bet['market_id']}")
                print(f"    Prediction: {bet['outcome']}")
                print(f"    Amount: ${bet['amount_usd']:.2f}")
                print(f"    Status: {bet['status'].upper()}")

                if bet["status"] == "active":
                    print(f"    Potential Return: ${bet['potential_return']:.2f}")
                    total_wagered += bet["amount_usd"]
                elif bet["status"] == "won":
                    print(f"    Profit: ${bet['actual_profit']:.2f}")
                    total_wagered += bet["amount_usd"]
                    total_return += bet['actual_return']
                    wins += 1
                elif bet["status"] == "lost":
                    total_wagered += bet["amount_usd"]
                    losses += 1

            print(f"\n  Total Wagered: ${total_wagered:.2f}")
            if total_return > 0:
                total_pnl = total_return - total_wagered
                roi = (total_pnl / total_wagered) * 100
                print(f"  Total Return: ${total_return:.2f}")
                print(f"  Total PnL: ${total_pnl:+.2f}")
                print(f"  ROI: {roi:+.2f}%")

            print(f"\n  Win Rate: {wins}/{wins + losses} ({(wins/(wins+losses)*100) if wins+losses > 0 else 0:.1f}%)")

        print("")

    def run_prediction_workflow(self):
        """Run a complete prediction market workflow."""
        print("=" * 70)
        print("DELPHI PREDICTION MARKET WORKFLOW")
        print("=" * 70)
        print("")

        # Step 1: Check balance
        self.check_balance()

        # Step 2: Get markets
        markets = self.get_markets()

        # Step 3: Place multiple bets
        print("3. Placing Strategic Bets")
        print("-" * 50)

        bet1 = self.place_bet("market_001", "Yes", 50)  # BTC > $50k
        bet2 = self.place_bet("market_002", "Yes", 25)  # Cronos TVL > $1B
        bet3 = self.place_bet("market_003", "Ethereum", 100)  # Active addresses

        # Step 4: Get bet summary
        self.get_bet_summary()

        # Step 5: Simulate market resolutions
        print("7. Simulating Market Resolutions")
        print("=" * 50)

        self.simulate_market_resolution("market_001", "Yes")  # BTC exceeded $50k
        self.simulate_market_resolution("market_002", "No")  # Cronos didn't reach $1B
        self.simulate_market_resolution("market_003", "Ethereum")  # ETH won

        # Step 6: Claim winnings
        print("8. Claiming Winnings")
        print("=" * 50)

        for bet_id, bet in self.bets.items():
            if bet["status"] == "won":
                self.claim_winnings(bet_id)

        # Step 7: Final summary
        print("9. Final Portfolio Summary")
        print("=" * 50)
        self.get_bet_summary()

        # Overall summary
        print("=" * 70)
        print("DELPHI PREDICTION MARKET WORKFLOW COMPLETE")
        print("=" * 70)
        print("  Features Demonstrated:")
        print("  ✅ Market listing with categories")
        print("  ✅ Odds calculation and display")
        print("  ✅ Bet placement with validation")
        print("  ✅ Market resolution simulation")
        print("  ✅ Winnings claim flow")
        print("  ✅ Portfolio tracking")
        print("=" * 70)


def main():
    """Main entry point."""
    private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY")
    if not private_key:
        print("ERROR: AGENT_WALLET_PRIVATE_KEY not set in .env")
        sys.exit(1)

    # Add 0x prefix if missing
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    predictor = DelphiPredictionMarketTest(private_key)

    try:
        predictor.run_prediction_workflow()
    except KeyboardInterrupt:
        print("\nTest interrupted")

    return 0


if __name__ == "__main__":
    sys.exit(main())

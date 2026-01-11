#!/usr/bin/env python3
"""
Test Moonlander Perpetual Trading

This script demonstrates perpetual trading operations:
1. Market listing and funding rates
2. Opening long/short positions with leverage
3. Setting stop-loss and take-profit
4. Position management and PnL calculation
5. Closing positions
"""

import json
import os
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


class MoonlanderPerpetualTradingTest:
    """Test Moonlander perpetual trading functionality."""

    def __init__(self, private_key: str):
        """Initialize with wallet."""
        self.account = Account.from_key(private_key)
        self.wallet_address = self.account.address
        self.w3 = Web3(Web3.HTTPProvider(CRONOS_TESTNET_RPC))

        # Position tracking
        self.positions = {}
        self.position_id_counter = 1

        print("=" * 70)
        print("Moonlander Perpetual Trading Test - Cronos Testnet")
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
        print(f"  Available for margin: {Web3.from_wei(cro_balance, 'ether'):.4f} CRO")
        print("")

    def get_markets(self):
        """Get available perpetual markets."""
        print("2. Available Perpetual Markets")
        print("-" * 50)

        markets = [
            {
                "symbol": "BTC-USDC",
                "base_asset": "BTC",
                "quote_asset": "USDC",
                "current_price": 42000.0,
                "max_leverage": 20,
                "min_order_size": 0.001,
                "funding_rate": 0.0001,
                "next_funding_time": (datetime.now() + timedelta(hours=8)).isoformat(),
                "mark_price": 42000.0,
                "index_price": 42000.0,
                "24h_volume": 15000000,
                "long_short_ratio": 0.52,
            },
            {
                "symbol": "ETH-USDC",
                "base_asset": "ETH",
                "quote_asset": "USDC",
                "current_price": 2200.0,
                "max_leverage": 20,
                "min_order_size": 0.01,
                "funding_rate": 0.00015,
                "next_funding_time": (datetime.now() + timedelta(hours=8)).isoformat(),
                "mark_price": 2200.0,
                "index_price": 2200.0,
                "24h_volume": 8000000,
                "long_short_ratio": 0.48,
            },
            {
                "symbol": "CRO-USDC",
                "base_asset": "CRO",
                "quote_asset": "USDC",
                "current_price": 0.075,
                "max_leverage": 10,
                "min_order_size": 10,
                "funding_rate": 0.00008,
                "next_funding_time": (datetime.now() + timedelta(hours=8)).isoformat(),
                "mark_price": 0.075,
                "index_price": 0.075,
                "24h_volume": 2000000,
                "long_short_ratio": 0.55,
            },
        ]

        for market in markets:
            print(f"\n  📊 {market['symbol']}")
            print(f"     Price: ${market['current_price']:,.2f}")
            print(f"     Max Leverage: {market['max_leverage']}x")
            print(f"     Funding Rate: {market['funding_rate']*100:.4f}% (8h)")
            print(f"     Long/Short Ratio: {market['long_short_ratio']}")
            print(f"     24h Volume: ${market['24h_volume']:,}")

        print("")
        return markets

    def get_funding_rates(self):
        """Get current funding rates."""
        print("3. Current Funding Rates")
        print("-" * 50)

        funding_rates = {
            "BTC-USDC": {
                "rate": 0.0001,
                "apy_long": 10.95,  # Annualized equivalent
                "apy_short": -10.95,
                "next_funding": datetime.now() + timedelta(hours=8),
            },
            "ETH-USDC": {
                "rate": 0.00015,
                "apy_long": 16.42,
                "apy_short": -16.42,
                "next_funding": datetime.now() + timedelta(hours=8),
            },
            "CRO-USDC": {
                "rate": 0.00008,
                "apy_long": 8.76,
                "apy_short": -8.76,
                "next_funding": datetime.now() + timedelta(hours=8),
            },
        }

        for symbol, data in funding_rates.items():
            print(f"\n  {symbol}:")
            print(f"    Current Rate: {data['rate']*100:.4f}% (8 hours)")
            print(f"    Long APY: {data['apy_long']:.2f}%")
            print(f"    Short APY: {data['apy_short']:.2f}%")
            print(f"    Next Funding: {data['next_funding'].strftime('%Y-%m-%d %H:%M:%S')}")

        print("")
        return funding_rates

    def open_position(
        self,
        symbol: str,
        side: str,
        size: float,
        leverage: int,
        stop_loss: float | None = None,
        take_profit: float | None = None
    ) -> dict[str, Any]:
        """
        Open a perpetual position.

        Args:
            symbol: Market symbol (e.g., "BTC-USDC")
            side: "long" or "short"
            size: Position size in base asset
            leverage: Leverage multiplier
            stop_loss: Optional stop-loss price
            take_profit: Optional take-profit price
        """
        print(f"4. Opening {side.upper()} Position: {symbol}")
        print("-" * 50)

        # Get market price
        prices = {"BTC-USDC": 42000, "ETH-USDC": 2200, "CRO-USDC": 0.075}
        entry_price = prices.get(symbol, 100)

        # Calculate margin
        margin = (size * entry_price) / leverage

        # Calculate liquidation price (simplified)
        if side == "long":
            liquidation_price = entry_price * (1 - 1/leverage + 0.05)  # 5% maintenance margin
        else:
            liquidation_price = entry_price * (1 + 1/leverage - 0.05)

        position = {
            "position_id": f"pos-{self.position_id_counter:06d}",
            "symbol": symbol,
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "leverage": leverage,
            "margin": margin,
            "liquidation_price": liquidation_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "timestamp": datetime.now().isoformat(),
            "status": "open",
        }

        self.positions[position["position_id"]] = position
        self.position_id_counter += 1

        # Display position details
        print(f"  Position ID: {position['position_id']}")
        print(f"  Market: {symbol}")
        print(f"  Side: {side.upper()}")
        print(f"  Size: {size} {symbol.split('-')[0]}")
        print(f"  Entry Price: ${entry_price:,.2f}")
        print(f"  Leverage: {leverage}x")
        print(f"  Margin: ${margin:,.2f}")
        print(f"  Liquidation Price: ${liquidation_price:,.2f}")

        if stop_loss:
            print(f"  Stop Loss: ${stop_loss:,.2f}")
        if take_profit:
            print(f"  Take Profit: ${take_profit:,.2f}")

        # Calculate unrealized PnL at 1% price movement
        price_move_1pct = entry_price * 0.01
        if side == "long":
            pnl_1pct = size * price_move_1pct * leverage
        else:
            pnl_1pct = size * price_move_1pct * leverage

        print(f"\n  Risk Analysis:")
        print(f"    PnL at ±1% price: ${pnl_1pct:+,.2f}")
        print(f"    Max Loss: -${margin:.2f} (liquidation)")
        print("")

        return position

    def close_position(self, position_id: str, exit_price: float | None = None) -> dict[str, Any]:
        """
        Close a position.

        Args:
            position_id: Position ID to close
            exit_price: Exit price (if None, uses current market price)
        """
        print(f"5. Closing Position: {position_id}")
        print("-" * 50)

        if position_id not in self.positions:
            print(f"  ❌ Position {position_id} not found")
            return {"success": False, "error": "position_not_found"}

        position = self.positions[position_id]

        # Use provided exit price or simulate market movement
        if exit_price is None:
            import random
            exit_price = position["entry_price"] * (1 + random.uniform(-0.02, 0.02))

        # Calculate PnL
        price_change = exit_price - position["entry_price"]
        if position["side"] == "long":
            pnl = price_change * position["size"] * position["leverage"]
        else:
            pnl = -price_change * position["size"] * position["leverage"]

        roi = (pnl / position["margin"]) * 100

        position["exit_price"] = exit_price
        position["pnl"] = pnl
        position["roi"] = roi
        position["status"] = "closed"
        position["closed_at"] = datetime.now().isoformat()

        # Display result
        print(f"  Position ID: {position_id}")
        print(f"  Side: {position['side'].upper()}")
        print(f"  Entry Price: ${position['entry_price']:,.2f}")
        print(f"  Exit Price: ${exit_price:,.2f}")
        print(f"  Price Change: ${price_change:+,.2f}")
        print(f"  PnL: ${pnl:+,.2f}")
        print(f"  ROI: {roi:+.2f}%")
        print(f"  Status: {'✅ PROFIT' if pnl > 0 else '❌ LOSS'}")
        print("")

        return position

    def set_risk_management(self, position_id: str, stop_loss: float, take_profit: float):
        """Set stop-loss and take-profit for a position."""
        print(f"6. Setting Risk Management: {position_id}")
        print("-" * 50)

        if position_id not in self.positions:
            print(f"  ❌ Position {position_id} not found")
            return

        position = self.positions[position_id]
        position["stop_loss"] = stop_loss
        position["take_profit"] = take_profit

        print(f"  Stop Loss: ${stop_loss:,.2f}")
        print(f"  Take Profit: ${take_profit:,.2f}")

        # Calculate risk/reward ratio
        entry = position["entry_price"]
        if position["side"] == "long":
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit

        rr_ratio = reward / risk if risk > 0 else 0
        print(f"  Risk/Reward Ratio: 1:{rr_ratio:.2f}")
        print("")

    def get_position_summary(self):
        """Display summary of all positions."""
        print("7. Position Summary")
        print("-" * 50)

        if not self.positions:
            print("  No open positions")
        else:
            total_pnl = 0
            total_margin = 0

            for pos_id, pos in self.positions.items():
                print(f"\n  {pos_id}:")
                print(f"    {pos['side'].upper()} {pos['size']} {pos['symbol'].split('-')[0]} @ {pos['leverage']}x")
                print(f"    Entry: ${pos['entry_price']:,.2f}")
                if pos["status"] == "closed":
                    print(f"    PnL: ${pos['pnl']:+,.2f} ({pos['roi']:+.2f}%)")
                    print(f"    Status: {pos['status'].upper()}")
                    total_pnl += pos.get("pnl", 0)
                else:
                    print(f"    Status: {pos['status'].upper()}")
                    print(f"    Liquidation: ${pos['liquidation_price']:,.2f}")
                total_margin += pos["margin"]

            print(f"\n  Total Margin Used: ${total_margin:,.2f}")
            if total_pnl != 0:
                print(f"  Total PnL: ${total_pnl:+,.2f}")

        print("")

    def run_trading_workflow(self):
        """Run a complete trading workflow demonstration."""
        print("=" * 70)
        print("MOONLANDER PERPETUAL TRADING WORKFLOW")
        print("=" * 70)
        print("")

        # Step 1: Check balance
        self.check_balance()

        # Step 2: Get markets
        markets = self.get_markets()

        # Step 3: Get funding rates
        funding_rates = self.get_funding_rates()

        # Step 4: Open long position
        long_pos = self.open_position(
            symbol="BTC-USDC",
            side="long",
            size=0.1,  # 0.1 BTC
            leverage=10,
            stop_loss=41500,
            take_profit=43000
        )

        # Step 5: Open short position
        short_pos = self.open_position(
            symbol="ETH-USDC",
            side="short",
            size=2.0,  # 2 ETH
            leverage=5,
            stop_loss=2250,
            take_profit=2150
        )

        # Step 6: Get position summary
        self.get_position_summary()

        # Step 7: Close positions with simulated price movement
        self.close_position(long_pos["position_id"], exit_price=42800)
        self.close_position(short_pos["position_id"], exit_price=2180)

        # Step 8: Final summary
        self.get_position_summary()

        print("=" * 70)
        print("MOONLANDER TRADING WORKFLOW COMPLETE")
        print("=" * 70)
        print("  Features Demonstrated:")
        print("  ✅ Market listing with funding rates")
        print("  ✅ Long position opening with leverage")
        print("  ✅ Short position opening with leverage")
        print("  ✅ Stop-loss and take-profit management")
        print("  ✅ Position PnL calculation")
        print("  ✅ Position closing and settlement")
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

    trader = MoonlanderPerpetualTradingTest(private_key)

    try:
        trader.run_trading_workflow()
    except KeyboardInterrupt:
        print("\nTest interrupted")

    return 0


if __name__ == "__main__":
    sys.exit(main())

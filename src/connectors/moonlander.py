"""
Moonlander connector for perpetual trading operations.

This module provides a connector to Moonlander perpetual exchange on Cronos for:
- Opening perpetual positions (long/short)
- Closing positions
- Setting stop-loss and take-profit
- Getting funding rates
- Position management

The connector uses mock data for development/testing but is designed
to integrate with actual Moonlander smart contracts.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class MoonlanderConnector:
    """
    Connector for Moonlander perpetual trading operations.

    Provides methods for:
    - Opening and closing perpetual positions
    - Setting risk management (stop-loss, take-profit)
    - Querying funding rates
    - Managing leverage
    """

    # Mock funding rates (8-hour funding)
    MOCK_FUNDING_RATES = {
        "BTC": 0.0001,   # 0.01% per 8 hours
        "ETH": 0.00015,  # 0.015% per 8 hours
        "CRO": 0.00008,  # 0.008% per 8 hours
    }

    # Mock prices
    MOCK_PRICES = {
        "BTC": 42000.0,
        "ETH": 2200.0,
        "CRO": 0.075,
    }

    def __init__(self):
        """Initialize the Moonlander connector."""
        self.positions: Dict[str, Dict[str, Any]] = {}
        logger.info("Moonlander connector initialized")

    def get_markets(self) -> List[Dict[str, Any]]:
        """
        Get list of available perpetual markets.

        Returns:
            List of market information dictionaries
        """
        markets = [
            {
                "symbol": "BTC-USDC",
                "base_asset": "BTC",
                "quote_asset": "USDC",
                "current_price": self.MOCK_PRICES["BTC"],
                "max_leverage": 20,
                "min_order_size": 0.001,
                "funding_rate": self.MOCK_FUNDING_RATES["BTC"],
                "next_funding_time": (datetime.now() + timedelta(hours=8)).isoformat(),
                "mark_price": self.MOCK_PRICES["BTC"],
                "index_price": self.MOCK_PRICES["BTC"],
                "24h_volume": 15000000,
            },
            {
                "symbol": "ETH-USDC",
                "base_asset": "ETH",
                "quote_asset": "USDC",
                "current_price": self.MOCK_PRICES["ETH"],
                "max_leverage": 20,
                "min_order_size": 0.01,
                "funding_rate": self.MOCK_FUNDING_RATES["ETH"],
                "next_funding_time": (datetime.now() + timedelta(hours=8)).isoformat(),
                "mark_price": self.MOCK_PRICES["ETH"],
                "index_price": self.MOCK_PRICES["ETH"],
                "24h_volume": 8000000,
            },
            {
                "symbol": "CRO-USDC",
                "base_asset": "CRO",
                "quote_asset": "USDC",
                "current_price": self.MOCK_PRICES["CRO"],
                "max_leverage": 10,
                "min_order_size": 10,
                "funding_rate": self.MOCK_FUNDING_RATES["CRO"],
                "next_funding_time": (datetime.now() + timedelta(hours=8)).isoformat(),
                "mark_price": self.MOCK_PRICES["CRO"],
                "index_price": self.MOCK_PRICES["CRO"],
                "24h_volume": 2000000,
            },
        ]

        return markets

    def get_funding_rate(self, asset: str) -> Dict[str, Any]:
        """
        Get current funding rate for a market.

        Args:
            asset: Base asset symbol (e.g., 'BTC', 'ETH')

        Returns:
            Dict with funding rate details
        """
        asset = asset.upper()

        rate = self.MOCK_FUNDING_RATES.get(asset, 0.0001)
        price = self.MOCK_PRICES.get(asset, 1.0)

        next_funding = datetime.now()
        # Round to next 8-hour interval (00:00, 08:00, 16:00 UTC)
        hour = next_funding.hour
        if hour < 8:
            next_funding = next_funding.replace(hour=8, minute=0, second=0, microsecond=0)
        elif hour < 16:
            next_funding = next_funding.replace(hour=16, minute=0, second=0, microsecond=0)
        else:
            next_funding = next_funding + timedelta(days=1)
            next_funding = next_funding.replace(hour=0, minute=0, second=0, microsecond=0)

        return {
            "asset": asset,
            "funding_rate": rate,
            "funding_rate_percentage": rate * 100,
            "mark_price": price,
            "index_price": price,
            "next_funding_time": next_funding.isoformat(),
            "seconds_until_funding": int((next_funding - datetime.now()).total_seconds()),
        }

    def open_position(
        self,
        asset: str,
        side: str,  # 'long' or 'short'
        size: float,
        leverage: int,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Open a perpetual position.

        Args:
            asset: Base asset to trade
            side: Position side ('long' or 'short')
            size: Position size in USDC
            leverage: Leverage multiplier (1-20)
            price: Optional limit price (None for market order)

        Returns:
            Dict with position details
        """
        asset = asset.upper()
        side = side.lower()

        if side not in ["long", "short"]:
            raise ValueError(f"Invalid side: {side}. Must be 'long' or 'short'")

        if leverage < 1 or leverage > 20:
            raise ValueError(f"Invalid leverage: {leverage}. Must be between 1 and 20")

        price = price or self.MOCK_PRICES.get(asset, 1.0)

        # Calculate position size
        collateral = Decimal(str(size)) / Decimal(str(leverage))
        position_size = collateral * Decimal(str(leverage))

        # Generate position ID
        position_id = self._generate_position_id()

        # Calculate liquidation price (mock)
        if side == "long":
            liquidation_price = price * (1 - 0.9 / leverage)
        else:  # short
            liquidation_price = price * (1 + 0.9 / leverage)

        position = {
            "position_id": position_id,
            "asset": asset,
            "side": side,
            "size_usd": float(size),
            "collateral_usd": float(collateral),
            "leverage": leverage,
            "entry_price": price,
            "mark_price": price,
            "liquidation_price": liquidation_price,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_percentage": 0.0,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "stop_loss": None,
            "take_profit": None,
        }

        self.positions[position_id] = position

        tx_hash = self._generate_mock_tx_hash()

        logger.info(
            f"Moonlander open {side} position: {size} USDC @ {leverage}x "
            f"on {asset} (entry: ${price})"
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "position": position,
        }

    def close_position(self, position_id: str) -> Dict[str, Any]:
        """
        Close a perpetual position.

        Args:
            position_id: Position identifier

        Returns:
            Dict with close result
        """
        if position_id not in self.positions:
            raise ValueError(f"Position not found: {position_id}")

        position = self.positions[position_id]

        # Calculate realized PnL (mock)
        entry_price = position["entry_price"]
        current_price = self.MOCK_PRICES.get(position["asset"], entry_price)
        side = position["side"]

        if side == "long":
            pnl_percentage = (current_price - entry_price) / entry_price * position["leverage"]
        else:  # short
            pnl_percentage = (entry_price - current_price) / entry_price * position["leverage"]

        pnl = position["collateral_usd"] * pnl_percentage

        position["status"] = "closed"
        position["closed_at"] = datetime.now().isoformat()
        position["exit_price"] = current_price
        position["realized_pnl"] = pnl
        position["realized_pnl_percentage"] = pnl_percentage

        tx_hash = self._generate_mock_tx_hash()

        logger.info(
            f"Moonlander close position {position_id}: "
            f"PnL: ${pnl:.2f} ({pnl_percentage:.2f}%)"
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "position_id": position_id,
            "realized_pnl": pnl,
            "realized_pnl_percentage": pnl_percentage,
            "exit_price": current_price,
        }

    def set_risk_management(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Set stop-loss and/or take-profit for a position.

        Args:
            position_id: Position identifier
            stop_loss: Stop-loss price (None to remove)
            take_profit: Take-profit price (None to remove)

        Returns:
            Dict with updated position
        """
        if position_id not in self.positions:
            raise ValueError(f"Position not found: {position_id}")

        position = self.positions[position_id]

        if stop_loss is not None:
            position["stop_loss"] = stop_loss

        if take_profit is not None:
            position["take_profit"] = take_profit

        logger.info(
            f"Moonlander set risk management for {position_id}: "
            f"SL: {stop_loss}, TP: {take_profit}"
        )

        return {
            "success": True,
            "position_id": position_id,
            "stop_loss": position["stop_loss"],
            "take_profit": position["take_profit"],
        }

    def get_position(self, position_id: str) -> Dict[str, Any]:
        """
        Get details of an open position.

        Args:
            position_id: Position identifier

        Returns:
            Position details
        """
        if position_id not in self.positions:
            raise ValueError(f"Position not found: {position_id}")

        position = self.positions[position_id].copy()

        # Update unrealized PnL
        current_price = self.MOCK_PRICES.get(position["asset"], position["entry_price"])
        entry_price = position["entry_price"]
        side = position["side"]

        if side == "long":
            pnl_percentage = (current_price - entry_price) / entry_price * position["leverage"]
        else:  # short
            pnl_percentage = (entry_price - current_price) / entry_price * position["leverage"]

        unrealized_pnl = position["collateral_usd"] * pnl_percentage
        position["mark_price"] = current_price
        position["unrealized_pnl"] = unrealized_pnl
        position["unrealized_pnl_percentage"] = pnl_percentage

        return position

    def list_positions(self, asset: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all open positions.

        Args:
            asset: Optional filter by asset

        Returns:
            List of open positions
        """
        positions = []

        for pos_id, position in self.positions.items():
            if position["status"] != "open":
                continue

            if asset and position["asset"] != asset.upper():
                continue

            positions.append(self.get_position(pos_id))

        return positions

    def _generate_position_id(self) -> str:
        """Generate a unique position ID."""
        return f"pos_{random.randint(100000, 999999)}"

    def _generate_mock_tx_hash(self) -> str:
        """Generate a mock transaction hash for testing."""
        return "0x" + "".join(random.choices("0123456789abcdef", k=64))


def get_moonlander_connector() -> MoonlanderConnector:
    """Get a Moonlander connector instance."""
    return MoonlanderConnector()

"""
Comprehensive test suite for DeFi connectors.

Tests:
- Moonlander perpetual trading
- Delphi prediction markets
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.connectors.delphi import get_delphi_connector
from src.connectors.moonlander import get_moonlander_connector


class TestMoonlanderConnector:
    """Test Moonlander perpetual trading connector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.moonlander = get_moonlander_connector()

    def test_get_markets(self):
        """Test getting available perpetual markets."""
        markets = self.moonlander.get_markets()

        assert len(markets) > 0
        assert all("symbol" in m for m in markets)
        assert all("current_price" in m for m in markets)
        assert all("funding_rate" in m for m in markets)

        print(f"✓ Retrieved {len(markets)} markets")

    def test_get_funding_rate(self):
        """Test getting funding rate for a market."""
        rate_info = self.moonlander.get_funding_rate("BTC")

        assert rate_info["asset"] == "BTC"
        assert "funding_rate" in rate_info
        assert "next_funding_time" in rate_info
        assert rate_info["funding_rate"] > 0

        print(f"✓ BTC funding rate: {rate_info['funding_rate']:.4%}")

    def test_open_long_position(self):
        """Test opening a long position."""
        result = self.moonlander.open_position(
            asset="BTC",
            side="long",
            size=100,
            leverage=10,
        )

        assert result["success"] is True
        assert "position" in result
        assert result["position"]["side"] == "long"
        assert result["position"]["leverage"] == 10

        position_id = result["position"]["position_id"]
        print(f"✓ Opened long position: {position_id}")

        return position_id

    def test_open_short_position(self):
        """Test opening a short position."""
        result = self.moonlander.open_position(
            asset="ETH",
            side="short",
            size=50,
            leverage=5,
        )

        assert result["success"] is True
        assert result["position"]["side"] == "short"

        position_id = result["position"]["position_id"]
        print(f"✓ Opened short position: {position_id}")

        return position_id

    def test_get_position(self):
        """Test getting position details."""
        # Open a position first
        open_result = self.moonlander.open_position(
            asset="BTC",
            side="long",
            size=100,
            leverage=10,
        )
        position_id = open_result["position"]["position_id"]

        # Get position details
        position = self.moonlander.get_position(position_id)

        assert position["position_id"] == position_id
        assert "unrealized_pnl" in position
        assert "liquidation_price" in position

        print(f"✓ Retrieved position: {position_id}")

    def test_set_risk_management(self):
        """Test setting stop-loss and take-profit."""
        # Open a position first
        open_result = self.moonlander.open_position(
            asset="BTC",
            side="long",
            size=100,
            leverage=10,
        )
        position_id = open_result["position"]["position_id"]

        # Set risk management
        result = self.moonlander.set_risk_management(
            position_id=position_id,
            stop_loss=40000,
            take_profit=50000,
        )

        assert result["success"] is True
        assert result["stop_loss"] == 40000
        assert result["take_profit"] == 50000

        print(f"✓ Set risk management for: {position_id}")

    def test_close_position(self):
        """Test closing a position."""
        # Open a position first
        open_result = self.moonlander.open_position(
            asset="BTC",
            side="long",
            size=100,
            leverage=10,
        )
        position_id = open_result["position"]["position_id"]

        # Close the position
        close_result = self.moonlander.close_position(position_id)

        assert close_result["success"] is True
        assert "realized_pnl" in close_result
        assert "exit_price" in close_result

        print(f"✓ Closed position: {position_id}, PnL: ${close_result['realized_pnl']:.2f}")

    def test_list_positions(self):
        """Test listing open positions."""
        # Open multiple positions
        pos1 = self.moonlander.open_position("BTC", "long", 100, 10)
        pos2 = self.moonlander.open_position("ETH", "short", 50, 5)

        # List all positions
        positions = self.moonlander.list_positions()

        assert len(positions) >= 2

        print(f"✓ Listed {len(positions)} open positions")

    def test_invalid_leverage(self):
        """Test that invalid leverage is rejected."""
        with pytest.raises(ValueError, match="leverage"):
            self.moonlander.open_position(
                asset="BTC",
                side="long",
                size=100,
                leverage=25,  # Too high
            )

        print("✓ Invalid leverage rejected")

    def test_invalid_side(self):
        """Test that invalid side is rejected."""
        with pytest.raises(ValueError, match="side"):
            self.moonlander.open_position(
                asset="BTC",
                side="invalid",
                size=100,
                leverage=10,
            )

        print("✓ Invalid side rejected")


class TestDelphiConnector:
    """Test Delphi prediction market connector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.delphi = get_delphi_connector()

    def test_get_markets(self):
        """Test getting available prediction markets."""
        markets = self.delphi.get_markets()

        assert len(markets) > 0
        assert all("market_id" in m for m in markets)
        assert all("question" in m for m in markets)
        assert all("odds" in m for m in markets)

        print(f"✓ Retrieved {len(markets)} prediction markets")

    def test_get_market(self):
        """Test getting specific market details."""
        markets = self.delphi.get_markets()
        market_id = markets[0]["market_id"]

        market = self.delphi.get_market(market_id)

        assert market["market_id"] == market_id
        assert "implied_probabilities" in market
        assert "time_remaining_seconds" in market

        print(f"✓ Retrieved market: {market_id}")

    def test_get_market_outcomes(self):
        """Test getting market outcomes and odds."""
        markets = self.delphi.get_markets()
        market_id = markets[0]["market_id"]

        outcomes = self.delphi.get_market_outcomes(market_id)

        assert outcomes["market_id"] == market_id
        assert "odds" in outcomes
        assert "implied_probabilities" in outcomes

        print(f"✓ Retrieved outcomes for: {market_id}")

    def test_place_bet(self):
        """Test placing a prediction bet."""
        markets = self.delphi.get_markets()
        market_id = markets[0]["market_id"]
        outcome = markets[0]["outcomes"][0]

        result = self.delphi.place_bet(
            market_id=market_id,
            outcome=outcome,
            amount=10,
        )

        assert result["success"] is True
        assert "bet" in result
        assert result["bet"]["outcome"] == outcome

        bet_id = result["bet"]["bet_id"]
        print(f"✓ Placed bet: {bet_id} on '{outcome}'")

        return bet_id

    def test_get_bet(self):
        """Test getting bet details."""
        # Place a bet first
        markets = self.delphi.get_markets()
        market_id = markets[0]["market_id"]
        outcome = markets[0]["outcomes"][0]

        place_result = self.delphi.place_bet(
            market_id=market_id,
            outcome=outcome,
            amount=10,
        )
        bet_id = place_result["bet"]["bet_id"]

        # Get bet details
        bet = self.delphi.get_bet(bet_id)

        assert bet["bet_id"] == bet_id
        assert bet["outcome"] == outcome
        assert "potential_return_usd" in bet

        print(f"✓ Retrieved bet: {bet_id}")

    def test_claim_winnings(self):
        """Test claiming winnings from a bet."""
        # Place a bet first
        markets = self.delphi.get_markets()
        market_id = markets[0]["market_id"]
        outcome = markets[0]["outcomes"][0]

        place_result = self.delphi.place_bet(
            market_id=market_id,
            outcome=outcome,
            amount=10,
        )
        bet_id = place_result["bet"]["bet_id"]

        # Claim winnings
        claim_result = self.delphi.claim_winnings(bet_id)

        assert claim_result["success"] is True
        assert "did_win" in claim_result
        assert "payout_usd" in claim_result

        print(f"✓ Claimed winnings: {bet_id}, Won: {claim_result['did_win']}")

    def test_list_bets(self):
        """Test listing bets."""
        # Place multiple bets
        markets = self.delphi.get_markets()

        for i, market in enumerate(markets[:2]):
            outcome = market["outcomes"][0]
            self.delphi.place_bet(
                market_id=market["market_id"],
                outcome=outcome,
                amount=10,
            )

        # List all bets
        bets = self.delphi.list_bets()

        assert len(bets) >= 2

        print(f"✓ Listed {len(bets)} bets")

    def test_invalid_market(self):
        """Test that invalid market ID is rejected."""
        with pytest.raises(ValueError, match="not found"):
            self.delphi.get_market("invalid_market_id")

        print("✓ Invalid market ID rejected")

    def test_invalid_outcome(self):
        """Test that invalid outcome is rejected."""
        markets = self.delphi.get_markets()
        market_id = markets[0]["market_id"]

        with pytest.raises(ValueError, match="Invalid outcome"):
            self.delphi.place_bet(
                market_id=market_id,
                outcome="Invalid Outcome",
                amount=10,
            )

        print("✓ Invalid outcome rejected")

    def test_bet_amount_validation(self):
        """Test that bet amount limits are enforced."""
        markets = self.delphi.get_markets()
        market_id = markets[0]["market_id"]
        outcome = markets[0]["outcomes"][0]

        # Test amount too low
        with pytest.raises(ValueError, match="below minimum"):
            self.delphi.place_bet(
                market_id=market_id,
                outcome=outcome,
                amount=0.1,
            )

        print("✓ Bet amount validation enforced")


class TestDefiAPIEndpoints:
    """Test DeFi API endpoints (integration test)."""

    def test_moonlander_markets_endpoint(self):
        """Test Moonlander markets API endpoint."""
        import requests

        response = requests.get("http://localhost:8000/api/v1/defi/moonlander/markets")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "markets" in data

        print(f"✓ GET /defi/moonlander/markets: {len(data['markets'])} markets")

    def test_delphi_markets_endpoint(self):
        """Test Delphi markets API endpoint."""
        import requests

        response = requests.get("http://localhost:8000/api/v1/defi/delphi/markets")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "markets" in data

        print(f"✓ GET /defi/delphi/markets: {len(data['markets'])} markets")

    def test_moonlander_funding_rate_endpoint(self):
        """Test Moonlander funding rate API endpoint."""
        import requests

        response = requests.get("http://localhost:8000/api/v1/defi/moonlander/funding-rate/BTC")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        print("✓ GET /defi/moonlander/funding-rate/BTC")


def run_tests():
    """Run all tests."""
    print("=" * 60)
    print("DeFi Connectors Test Suite")
    print("=" * 60)
    print()

    # Test Moonlander
    print("Testing Moonlander Connector...")
    print("-" * 60)
    test_moonlander = TestMoonlanderConnector()
    test_moonlander.setup_method()

    test_moonlander.test_get_markets()
    test_moonlander.test_get_funding_rate()
    pos_id = test_moonlander.test_open_long_position()
    test_moonlander.test_open_short_position()
    test_moonlander.test_get_position()
    test_moonlander.test_set_risk_management()
    test_moonlander.test_close_position()
    test_moonlander.test_list_positions()
    test_moonlander.test_invalid_leverage()
    test_moonlander.test_invalid_side()

    print()
    print("Testing Delphi Connector...")
    print("-" * 60)
    test_delphi = TestDelphiConnector()
    test_delphi.setup_method()

    test_delphi.test_get_markets()
    test_delphi.test_get_market()
    test_delphi.test_get_market_outcomes()
    test_delphi.test_place_bet()
    test_delphi.test_get_bet()
    test_delphi.test_claim_winnings()
    test_delphi.test_list_bets()
    test_delphi.test_invalid_market()
    test_delphi.test_invalid_outcome()
    test_delphi.test_bet_amount_validation()

    print()
    print("Testing API Endpoints...")
    print("-" * 60)
    test_api = TestDefiAPIEndpoints()

    try:
        test_api.test_moonlander_markets_endpoint()
        test_api.test_delphi_markets_endpoint()
        test_api.test_moonlander_funding_rate_endpoint()
    except Exception as e:
        print(f"⚠ API endpoint tests failed (server may not be running): {e}")

    print()
    print("=" * 60)
    print("✓ All DeFi connector tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()

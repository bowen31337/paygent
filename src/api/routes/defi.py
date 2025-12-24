"""
DeFi trading API routes.

Provides endpoints for:
- Moonlander perpetual trading
- Delphi prediction markets
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.connectors.moonlander import get_moonlander_connector
from src.connectors.delphi import get_delphi_connector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["defi"])

# Moonlander connector instance
moonlander = get_moonlander_connector()

# Delphi connector instance
delphi = get_delphi_connector()


# ============================================================================
# Moonlander Perpetual Trading Endpoints
# ============================================================================

class OpenPositionRequest(BaseModel):
    """Request to open a perpetual position."""
    asset: str = Field(..., description="Base asset symbol (e.g., BTC, ETH)")
    side: str = Field(..., description="Position side: 'long' or 'short'")
    size_usd: float = Field(..., gt=0, description="Position size in USDC")
    leverage: int = Field(..., ge=1, le=20, description="Leverage multiplier (1-20)")
    price: Optional[float] = Field(None, description="Limit price (None for market order)")


class SetRiskManagementRequest(BaseModel):
    """Request to set stop-loss/take-profit."""
    stop_loss: Optional[float] = Field(None, description="Stop-loss price")
    take_profit: Optional[float] = Field(None, description="Take-profit price")


@router.get("/moonlander/markets")
async def get_moonlander_markets():
    """
    Get list of available perpetual markets.

    Returns market information including:
    - Current prices
    - Funding rates
    - Available leverage
    - Volume statistics
    """
    try:
        markets = moonlander.get_markets()
        return {
            "success": True,
            "markets": markets,
            "count": len(markets),
        }
    except Exception as e:
        logger.error(f"Error getting Moonlander markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/moonlander/funding-rate/{asset}")
async def get_funding_rate(asset: str):
    """
    Get current funding rate for a market.

    Args:
        asset: Base asset symbol (e.g., BTC, ETH)

    Returns funding rate details including next funding time.
    """
    try:
        rate_info = moonlander.get_funding_rate(asset)
        return {
            "success": True,
            "data": rate_info,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting funding rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/moonlander/positions/open")
async def open_position(request: OpenPositionRequest):
    """
    Open a perpetual trading position.

    Supports both long and short positions with configurable leverage.
    """
    try:
        result = moonlander.open_position(
            asset=request.asset,
            side=request.side,
            size=request.size_usd,
            leverage=request.leverage,
            price=request.price,
        )

        return {
            "success": True,
            "position": result["position"],
            "tx_hash": result["tx_hash"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error opening position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/moonlander/positions/{position_id}/close")
async def close_position(position_id: str):
    """
    Close a perpetual position.

    Calculates and returns realized PnL.
    """
    try:
        result = moonlander.close_position(position_id)

        return {
            "success": True,
            "position_id": result["position_id"],
            "realized_pnl": result["realized_pnl"],
            "realized_pnl_percentage": result["realized_pnl_percentage"],
            "exit_price": result["exit_price"],
            "tx_hash": result["tx_hash"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/moonlander/positions/{position_id}")
async def get_position(position_id: str):
    """
    Get details of a specific position.

    Returns current position state including unrealized PnL.
    """
    try:
        position = moonlander.get_position(position_id)

        return {
            "success": True,
            "position": position,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/moonlander/positions")
async def list_positions(asset: Optional[str] = Query(None, description="Filter by asset")):
    """
    List all open positions.

    Args:
        asset: Optional filter by base asset

    Returns list of open positions with current PnL.
    """
    try:
        positions = moonlander.list_positions(asset=asset)

        return {
            "success": True,
            "positions": positions,
            "count": len(positions),
        }
    except Exception as e:
        logger.error(f"Error listing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/moonlander/positions/{position_id}/risk-management")
async def set_risk_management(position_id: str, request: SetRiskManagementRequest):
    """
    Set stop-loss and/or take-profit for a position.

    Can set one or both risk management levels.
    """
    try:
        result = moonlander.set_risk_management(
            position_id=position_id,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
        )

        return {
            "success": True,
            "position_id": result["position_id"],
            "stop_loss": result["stop_loss"],
            "take_profit": result["take_profit"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting risk management: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Delphi Prediction Markets Endpoints
# ============================================================================

class PlaceBetRequest(BaseModel):
    """Request to place a prediction bet."""
    market_id: str = Field(..., description="Market identifier")
    outcome: str = Field(..., description="Predicted outcome")
    amount_usd: float = Field(..., gt=0, description="Bet amount in USDC")
    odds: Optional[float] = Field(None, description="Odds to accept (None for current)")


@router.get("/delphi/markets")
async def get_delphi_markets(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: str = Query("active", description="Market status"),
    limit: int = Query(50, ge=1, le=100, description="Max markets to return")
):
    """
    Get list of prediction markets.

    Args:
        category: Optional filter by category (crypto, defi, etc.)
        status: Filter by status (active, resolved, cancelled)
        limit: Maximum number of markets to return

    Returns list of available prediction markets.
    """
    try:
        markets = delphi.get_markets(category=category, status=status, limit=limit)

        return {
            "success": True,
            "markets": markets,
            "count": len(markets),
        }
    except Exception as e:
        logger.error(f"Error getting Delphi markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delphi/markets/{market_id}")
async def get_delphi_market(market_id: str):
    """
    Get details of a specific prediction market.

    Returns full market information including current odds and probabilities.
    """
    try:
        market = delphi.get_market(market_id)

        return {
            "success": True,
            "market": market,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting market: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delphi/markets/{market_id}/outcomes")
async def get_market_outcomes(market_id: str):
    """
    Get current outcomes and odds for a market.

    Returns odds and implied probabilities for all outcomes.
    """
    try:
        outcomes = delphi.get_market_outcomes(market_id)

        return {
            "success": True,
            "outcomes": outcomes,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting market outcomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delphi/markets/{market_id}/outcome")
async def get_market_outcome(market_id: str):
    """
    Get the outcome of a resolved market.

    Returns winning outcome if market is resolved.
    """
    try:
        outcome = delphi.get_outcome(market_id)

        return {
            "success": True,
            "outcome": outcome,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting market outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delphi/bets")
async def place_bet(request: PlaceBetRequest):
    """
    Place a bet on a prediction market.

    Creates a new position in the specified market.
    """
    try:
        result = delphi.place_bet(
            market_id=request.market_id,
            outcome=request.outcome,
            amount=request.amount_usd,
            odds=request.odds,
        )

        return {
            "success": True,
            "bet": result["bet"],
            "tx_hash": result["tx_hash"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error placing bet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delphi/bets/{bet_id}/claim")
async def claim_winnings(bet_id: str):
    """
    Claim winnings from a resolved bet.

    Returns payout amount and profit/loss.
    """
    try:
        result = delphi.claim_winnings(bet_id)

        return {
            "success": True,
            "bet_id": result["bet_id"],
            "did_win": result["did_win"],
            "payout_usd": result["payout_usd"],
            "profit_usd": result["profit_usd"],
            "winning_outcome": result["winning_outcome"],
            "tx_hash": result["tx_hash"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error claiming winnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delphi/bets/{bet_id}")
async def get_bet(bet_id: str):
    """
    Get details of a specific bet.

    Returns bet information including current status.
    """
    try:
        bet = delphi.get_bet(bet_id)

        return {
            "success": True,
            "bet": bet,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting bet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delphi/bets")
async def list_bets(
    market_id: Optional[str] = Query(None, description="Filter by market ID"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    List bets with optional filters.

    Args:
        market_id: Optional filter by market
        status: Optional filter by status (active, won, lost)

    Returns list of user's bets.
    """
    try:
        bets = delphi.list_bets(market_id=market_id, status=status)

        return {
            "success": True,
            "bets": bets,
            "count": len(bets),
        }
    except Exception as e:
        logger.error(f"Error listing bets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

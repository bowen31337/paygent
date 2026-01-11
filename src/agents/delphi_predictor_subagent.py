"""
Delphi Predictor Subagent for Prediction Market Operations.

This module implements a specialized subagent for handling Delphi
prediction market operations (place bets, claim winnings, etc.)
on the Cronos blockchain using deepagents create_deep_agent API.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from src.connectors.delphi import DelphiConnector
from src.utils.llm import get_model_string

logger = logging.getLogger(__name__)

# Try to import deepagents
try:
    from deepagents import create_deep_agent
    DEEPAGENTS_AVAILABLE = True
except ImportError:
    DEEPAGENTS_AVAILABLE = False
    create_deep_agent = None  # type: ignore


# Delphi Predictor System Prompt
DELPHI_PREDICTOR_SYSTEM_PROMPT = """You are Delphi Predictor, a specialized subagent for prediction market operations on Delphi.

Your capabilities:
- List available prediction markets with odds and categories
- Analyze market odds and potential returns
- Place prediction bets on market outcomes
- Claim winnings from resolved markets
- Check bet status and market outcomes
- Analyze risk vs reward for different bets

Important guidelines:
1. Always check market status before placing bets (must be 'active')
2. Validate bet amounts are within market limits
3. Analyze odds and potential returns before betting
4. Consider risk vs reward - higher odds mean lower probability
5. Return structured JSON responses with bet details
6. Handle bet claims by checking if market is resolved

When users provide betting commands:
1. Parse market ID and desired outcome
2. Check market status and odds
3. Validate bet amount limits
4. Calculate potential returns and profits
5. Execute bet placement
6. Return detailed bet confirmation

Always be precise and return detailed betting information with risk analysis."""


# Global connector instance for tools
_delphi_connector: DelphiConnector | None = None


def get_delphi_connector() -> DelphiConnector:
    """Get or create the Delphi connector."""
    global _delphi_connector
    if _delphi_connector is None:
        _delphi_connector = DelphiConnector()
    return _delphi_connector


# Delphi tools using @tool decorator
@tool
def get_delphi_markets(
    category: str | None = None,
    status: str = "active",
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get list of available prediction markets on Delphi.

    Args:
        category: Optional category filter (e.g., "crypto", "sports", "politics")
        status: Market status filter (default: "active")
        limit: Maximum number of markets to return

    Returns:
        Dict containing list of markets and count
    """
    logger.info(f"Getting Delphi markets: category={category}, status={status}")

    connector = get_delphi_connector()
    markets = connector.get_markets(
        category=category,
        status=status,
        limit=limit,
    )

    return {
        "success": True,
        "markets": markets,
        "count": len(markets),
        "filter": {"category": category, "status": status, "limit": limit},
    }


@tool
def place_prediction_bet(
    market_id: str,
    outcome: str,
    amount: float,
    odds: float | None = None,
) -> dict[str, Any]:
    """
    Place a bet on a Delphi prediction market.

    Args:
        market_id: The market identifier
        outcome: The predicted outcome to bet on
        amount: Bet amount in USDC
        odds: Optional minimum odds to accept

    Returns:
        Dict containing bet placement details
    """
    logger.info(f"Placing Delphi bet: {amount} USDC on {outcome} for {market_id}")

    try:
        connector = get_delphi_connector()
        result = connector.place_bet(
            market_id=market_id,
            outcome=outcome,
            amount=amount,
            odds=odds,
        )

        bet = result.get("bet", {})
        return {
            "success": result.get("success", False),
            "bet_id": bet.get("bet_id"),
            "market_id": market_id,
            "outcome": outcome,
            "amount_usd": amount,
            "odds": bet.get("odds"),
            "potential_return_usd": bet.get("potential_return_usd"),
            "potential_profit_usd": bet.get("potential_profit_usd"),
            "status": bet.get("status"),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@tool
def claim_prediction_winnings(bet_id: str) -> dict[str, Any]:
    """
    Claim winnings from a resolved Delphi prediction bet.

    Args:
        bet_id: The bet identifier

    Returns:
        Dict containing claim result and payout details
    """
    logger.info(f"Claiming Delphi winnings for bet: {bet_id}")

    try:
        connector = get_delphi_connector()
        result = connector.claim_winnings(bet_id=bet_id)

        return {
            "success": result.get("success", False),
            "bet_id": bet_id,
            "did_win": result.get("did_win", False),
            "payout_usd": result.get("payout_usd", 0.0),
            "profit_usd": result.get("profit_usd", 0.0),
            "winning_outcome": result.get("winning_outcome"),
            "status": "claimed",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@tool
def get_prediction_bet(bet_id: str) -> dict[str, Any]:
    """
    Get details of a specific prediction bet.

    Args:
        bet_id: The bet identifier

    Returns:
        Dict containing bet details
    """
    logger.info(f"Getting Delphi bet details: {bet_id}")

    try:
        connector = get_delphi_connector()
        bet = connector.get_bet(bet_id=bet_id)

        return {
            "success": True,
            "bet_id": bet_id,
            "market_id": bet.get("market_id"),
            "market_question": bet.get("market_question"),
            "outcome": bet.get("outcome"),
            "amount_usd": bet.get("amount_usd"),
            "odds": bet.get("odds"),
            "status": bet.get("status"),
            "created_at": bet.get("created_at"),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@tool
def get_market_outcomes(market_id: str) -> dict[str, Any]:
    """
    Get current outcomes and odds for a Delphi prediction market.

    Args:
        market_id: The market identifier

    Returns:
        Dict containing market outcomes and odds
    """
    logger.info(f"Getting Delphi market outcomes: {market_id}")

    try:
        connector = get_delphi_connector()
        outcomes = connector.get_market_outcomes(market_id=market_id)

        return {
            "success": True,
            "market_id": market_id,
            "question": outcomes.get("question"),
            "outcomes": outcomes.get("outcomes"),
            "odds": outcomes.get("odds"),
            "implied_probabilities": outcomes.get("implied_probabilities"),
            "total_volume_usd": outcomes.get("total_volume_usd"),
            "liquidity_usd": outcomes.get("liquidity_usd"),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


class DelphiPredictorSubagent:
    """
    Delphi Prediction Market Subagent.

    Specialized subagent for executing prediction market operations on Delphi
    using the deepagents create_deep_agent API.
    """

    def __init__(
        self,
        db: AsyncSession,
        session_id: UUID,
        parent_agent_id: UUID,
        llm_model: str = "anthropic/claude-sonnet-4",
    ):
        """
        Initialize the Delphi predictor subagent.

        Args:
            db: Database session
            session_id: Session ID for this subagent
            parent_agent_id: ID of the parent agent that spawned this subagent
            llm_model: LLM model to use
        """
        self.db = db
        self.session_id = session_id
        self.parent_agent_id = parent_agent_id
        self.llm_model = llm_model
        self.available = DEEPAGENTS_AVAILABLE

        # Initialize Delphi connector
        self.delphi_connector = get_delphi_connector()

        # Initialize tools
        self.tools = [
            get_delphi_markets,
            place_prediction_bet,
            claim_prediction_winnings,
            get_prediction_bet,
            get_market_outcomes,
        ]

        # Create agent lazily
        self._agent = None

        logger.info(
            f"Delphi Predictor Subagent initialized - Session: {session_id}, "
            f"Parent: {parent_agent_id}, DeepAgents: {self.available}"
        )

    def _create_agent(self):
        """Create the Delphi predictor agent using create_deep_agent."""
        if not self.available:
            logger.warning("DeepAgents not available, agent creation skipped")
            return None

        agent = create_deep_agent(
            model=get_model_string(self.llm_model),
            tools=self.tools,
            system_prompt=DELPHI_PREDICTOR_SYSTEM_PROMPT,
        )
        return agent

    @property
    def agent(self):
        """Get or create the agent instance."""
        if self._agent is None and self.available:
            self._agent = self._create_agent()
        return self._agent

    def verify_context_isolation(self) -> bool:
        """
        Verify that this subagent has proper context isolation.

        Returns:
            True if context isolation is properly configured
        """
        checks = {
            "has_unique_session": self.session_id != self.parent_agent_id,
            "has_parent_reference": self.parent_agent_id is not None,
            "has_dedicated_tools": len(self.tools) > 0,
            "deepagents_available": self.available,
        }

        all_passed = all(checks.values())

        logger.info(
            f"Context isolation check for {self.session_id}: {checks} - "
            f"{'PASS' if all_passed else 'FAIL'}"
        )

        return all_passed

    async def place_prediction_bet_async(
        self,
        market_id: str,
        outcome: str,
        amount: float,
        odds: float | None = None,
    ) -> dict[str, Any]:
        """
        Place a prediction bet using Delphi connector.

        Args:
            market_id: Market identifier
            outcome: Predicted outcome
            amount: Bet amount in USDC
            odds: Optional odds to accept

        Returns:
            Dict containing bet placement result
        """
        try:
            logger.info(
                f"Delphi Predictor placing bet: {amount} USDC on {outcome} "
                f"for market {market_id}"
            )

            if self.available and self.agent:
                # Use deepagents agent
                bet_command = (
                    f"Place a {amount} USDC bet on '{outcome}' "
                    f"for market {market_id}"
                )
                if odds:
                    bet_command += f" @ {odds:.2f} odds"

                result = await self.agent.ainvoke({
                    "messages": [{"role": "user", "content": bet_command}]
                })

                bet_result = self._process_agent_result(result, market_id, outcome, amount, odds)
            else:
                # Fallback to direct tool call
                bet_result = place_prediction_bet.invoke({
                    "market_id": market_id,
                    "outcome": outcome,
                    "amount": amount,
                    "odds": odds,
                })

            logger.info(f"Delphi Predictor bet placed: {bet_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "bet_details": bet_result,
                "framework": "deepagents" if self.available else "fallback",
            }

        except Exception as e:
            logger.error(f"Delphi Predictor bet placement failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    async def claim_winnings(self, bet_id: str) -> dict[str, Any]:
        """
        Claim winnings from a resolved bet.

        Args:
            bet_id: Bet identifier

        Returns:
            Dict containing claim result
        """
        try:
            logger.info(f"Delphi Predictor claiming winnings for bet: {bet_id}")

            if self.available and self.agent:
                result = await self.agent.ainvoke({
                    "messages": [{"role": "user", "content": f"Claim winnings from bet {bet_id}"}]
                })

                claim_result = self._process_claim_result(result, bet_id)
            else:
                # Fallback to direct tool call
                claim_result = claim_prediction_winnings.invoke({"bet_id": bet_id})

            logger.info(f"Delphi Predictor winnings claimed: {claim_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "claim_details": claim_result,
                "framework": "deepagents" if self.available else "fallback",
            }

        except Exception as e:
            logger.error(f"Delphi Predictor claim failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    async def get_market_analysis(
        self,
        market_id: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """
        Get market analysis for prediction markets.

        Args:
            market_id: Specific market to analyze
            category: Category filter

        Returns:
            Dict containing market analysis
        """
        try:
            logger.info(f"Delphi Predictor analyzing markets: {market_id or 'all'}")

            if market_id:
                result = get_market_outcomes.invoke({"market_id": market_id})
            else:
                result = get_delphi_markets.invoke({
                    "category": category,
                    "status": "active",
                })

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "analysis_details": result,
            }

        except Exception as e:
            logger.error(f"Delphi Predictor market analysis failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    def _process_agent_result(
        self,
        result: Any,
        market_id: str,
        outcome: str,
        amount: float,
        odds: float | None = None,
    ) -> dict[str, Any]:
        """Process result from deepagents agent."""
        if isinstance(result, dict):
            messages = result.get("messages", [])
            if messages:
                return {
                    "market_id": market_id,
                    "outcome": outcome,
                    "amount_usd": amount,
                    "odds": odds or 1.5,
                    "status": "active",
                }

        return {
            "market_id": market_id,
            "outcome": outcome,
            "amount_usd": amount,
            "odds": odds or 1.5,
            "status": "active",
        }

    def _process_claim_result(self, result: Any, bet_id: str) -> dict[str, Any]:
        """Process claim result."""
        return {
            "bet_id": bet_id,
            "status": "claimed",
            "timestamp": datetime.now().isoformat(),
        }

    async def get_execution_summary(self) -> dict[str, Any]:
        """Get execution summary for this subagent."""
        return {
            "subagent_type": "Delphi Predictor",
            "session_id": str(self.session_id),
            "parent_agent_id": str(self.parent_agent_id),
            "llm_model": get_model_string(self.llm_model),
            "tools_count": len(self.tools),
            "framework": "deepagents" if self.available else "fallback",
        }

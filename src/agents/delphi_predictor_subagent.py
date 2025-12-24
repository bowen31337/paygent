"""
Delphi Predictor Subagent for Prediction Market Operations.

This module implements a specialized subagent for handling Delphi
prediction market operations (place bets, claim winnings, etc.)
on the Cronos blockchain.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.connectors.delphi import DelphiConnector

logger = logging.getLogger(__name__)


class DelphiPredictorCallbackHandler(BaseCallbackHandler):
    """Callback handler for Delphi predictor subagent events."""

    def __init__(self, session_id: UUID):
        self.session_id = session_id
        self.events = []

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Called when a tool is started."""
        event = {
            "type": "tool_call",
            "tool_name": serialized["name"],
            "tool_input": input_str,
        }
        self.events.append(event)
        logger.info(f"Delphi Predictor {self.session_id}: Tool call - {event}")

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Called when a tool finishes."""
        event = {
            "type": "tool_result",
            "tool_output": output,
        }
        self.events.append(event)
        logger.info(f"Delphi Predictor {self.session_id}: Tool result - {event}")


class DelphiPredictorSubagent:
    """
    Delphi Prediction Market Subagent.

    Specialized subagent for executing prediction market operations on Delphi.
    Spawns when the main agent detects a prediction market command and handles
    the complete betting workflow including odds analysis and winnings claims.
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

        # Initialize LLM
        self.llm = self._initialize_llm()

        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            session_id=str(session_id),
        )

        # Initialize Delphi connector
        self.delphi_connector = DelphiConnector()

        # Initialize tools
        self.tools = self._create_tools()

        # Initialize agent
        self.agent_executor = self._create_agent()

        logger.info(f"Delphi Predictor Subagent initialized for session {session_id}")

    def _initialize_llm(self):
        """Initialize the LLM based on configuration."""
        if "anthropic" in self.llm_model:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model="claude-sonnet-4",
                temperature=0.2,
                max_tokens=2000,
                api_key=settings.anthropic_api_key,
            )
        else:
            return ChatOpenAI(
                model="gpt-4",
                temperature=0.2,
                max_tokens=2000,
                api_key=settings.openai_api_key,
            )

    def _create_tools(self) -> List[Any]:
        """Create tools specific to Delphi prediction markets."""
        tools = [
            GetDelphiMarketsTool(self.delphi_connector),
            PlacePredictionBetTool(self.delphi_connector),
            ClaimPredictionWinningsTool(self.delphi_connector),
            GetPredictionBetTool(self.delphi_connector),
            GetMarketOutcomesTool(self.delphi_connector),
        ]
        return tools

    def _create_agent(self) -> AgentExecutor:
        """
        Create the Delphi predictor agent.

        Returns:
            AgentExecutor: Configured agent executor
        """
        # System prompt for Delphi prediction markets
        system_prompt = """You are Delphi Predictor, a specialized subagent for prediction market operations on Delphi.

Your capabilities:
- List available prediction markets with odds and categories
- Analyze market odds and potential returns
- Place prediction bets on market outcomes
- Claim winnings from resolved markets
- Check bet status and market outcomes
- Analyze risk vs reward for different bets

Available tools:
- get_delphi_markets: Get list of available prediction markets
- place_prediction_bet: Place a bet on a market outcome
- claim_prediction_winnings: Claim winnings from resolved bets
- get_prediction_bet: Get details of a specific bet
- get_market_outcomes: Get current outcomes and odds

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

Example commands you should handle:
- "List prediction markets in crypto category"
- "Place 10 USDC on Bitcoin exceeding $50k"
- "Claim winnings from my bet on market_001"
- "Check status of my bet bet_123456"
- "What are the odds for Cronos TVL exceeding $1B?"

Always be precise and return detailed betting information with risk analysis."""

        # Create agent prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

        # Create agent executor with stricter settings for focused execution
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,  # Fewer iterations for focused betting execution
            early_stopping_method="generate",  # Stop when task is complete
        )

        return agent_executor

    async def place_prediction_bet(
        self,
        market_id: str,
        outcome: str,
        amount: float,
        odds: Optional[float] = None,
    ) -> Dict[str, Any]:
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

            # Prepare bet command
            bet_command = (
                f"Place a {amount} USDC bet on '{outcome}' "
                f"for market {market_id}"
            )
            if odds:
                bet_command += f" @ {odds:.2f} odds"

            # Execute bet
            result = await self.agent_executor.ainvoke({
                "input": bet_command,
                "market_id": market_id,
                "outcome": outcome,
                "amount": amount,
                "odds": odds,
            })

            # Process and format result
            bet_result = self._process_bet_result(result, market_id, outcome, amount, odds)

            logger.info(f"Delphi Predictor bet placed: {bet_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "bet_details": bet_result,
            }

        except Exception as e:
            logger.error(f"Delphi Predictor bet placement failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    async def claim_winnings(
        self,
        bet_id: str,
    ) -> Dict[str, Any]:
        """
        Claim winnings from a resolved bet.

        Args:
            bet_id: Bet identifier

        Returns:
            Dict containing claim result
        """
        try:
            logger.info(f"Delphi Predictor claiming winnings for bet: {bet_id}")

            # Execute claim
            result = await self.agent_executor.ainvoke({
                "input": f"Claim winnings from bet {bet_id}",
                "bet_id": bet_id,
            })

            # Process result
            claim_result = self._process_claim_result(result, bet_id)

            logger.info(f"Delphi Predictor winnings claimed: {claim_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "claim_details": claim_result,
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
        market_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
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

            # Prepare analysis command
            if market_id:
                analysis_command = f"Analyze market {market_id}"
            elif category:
                analysis_command = f"List and analyze {category} markets"
            else:
                analysis_command = "List all available markets"

            # Execute analysis
            result = await self.agent_executor.ainvoke({
                "input": analysis_command,
                "market_id": market_id,
                "category": category,
            })

            # Process result
            analysis_result = self._process_market_analysis(result, market_id, category)

            logger.info(f"Delphi Predictor market analysis: {analysis_result}")

            return {
                "success": True,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "analysis_details": analysis_result,
            }

        except Exception as e:
            logger.error(f"Delphi Predictor market analysis failed: {e}")
            return {
                "success": False,
                "subagent_id": str(self.session_id),
                "parent_agent_id": str(self.parent_agent_id),
                "error": str(e),
            }

    def _process_bet_result(
        self,
        result: Dict[str, Any],
        market_id: str,
        outcome: str,
        amount: float,
        odds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Process and format bet placement result.

        Args:
            result: Raw bet result from agent
            market_id: Market ID
            outcome: Bet outcome
            amount: Bet amount
            odds: Bet odds

        Returns:
            Formatted bet details
        """
        bet_details = result.get("output", {})
        if isinstance(bet_details, str):
            try:
                import json as json_lib
                bet_details = json_lib.loads(bet_details)
            except:
                bet_details = {"raw_output": bet_details}

        return {
            "market_id": market_id,
            "outcome": outcome,
            "amount_usd": amount,
            "odds": odds or bet_details.get("odds", 1.0),
            "potential_return_usd": bet_details.get("potential_return_usd", amount * 1.5),
            "potential_profit_usd": bet_details.get("potential_profit_usd", amount * 0.5),
            "status": bet_details.get("status", "active"),
            "bet_id": bet_details.get("bet_id", f"bet_{self.session_id}"),
            "timestamp": bet_details.get("timestamp", datetime.now().isoformat()),
        }

    def _process_claim_result(
        self,
        result: Dict[str, Any],
        bet_id: str,
    ) -> Dict[str, Any]:
        """
        Process and format winnings claim result.

        Args:
            result: Raw claim result from agent
            bet_id: Bet ID

        Returns:
            Formatted claim details
        """
        claim_details = result.get("output", {})
        if isinstance(claim_details, str):
            try:
                import json as json_lib
                claim_details = json_lib.loads(claim_details)
            except:
                claim_details = {"raw_output": claim_details}

        return {
            "bet_id": bet_id,
            "did_win": claim_details.get("did_win", False),
            "payout_usd": claim_details.get("payout_usd", 0.0),
            "profit_usd": claim_details.get("profit_usd", 0.0),
            "winning_outcome": claim_details.get("winning_outcome", "Unknown"),
            "status": "claimed",
            "timestamp": claim_details.get("timestamp", datetime.now().isoformat()),
        }

    def _process_market_analysis(
        self,
        result: Dict[str, Any],
        market_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process and format market analysis result.

        Args:
            result: Raw analysis result from agent
            market_id: Market ID (if specific)
            category: Category (if filtered)

        Returns:
            Formatted analysis details
        """
        analysis_details = result.get("output", {})
        if isinstance(analysis_details, str):
            try:
                import json as json_lib
                analysis_details = json_lib.loads(analysis_details)
            except:
                analysis_details = {"raw_output": analysis_details}

        return {
            "market_id": market_id,
            "category": category,
            "markets": analysis_details.get("markets", []),
            "analysis": analysis_details.get("analysis", "Market analysis completed"),
            "timestamp": analysis_details.get("timestamp", datetime.now().isoformat()),
        }

    async def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary for this subagent."""
        return {
            "subagent_type": "Delphi Predictor",
            "session_id": str(self.session_id),
            "parent_agent_id": str(self.parent_agent_id),
            "llm_model": self.llm_model,
            "tools_count": len(self.tools),
            "memory_size": len(self.memory.chat_memory.messages),
        }


# Delphi prediction market tools
class GetDelphiMarketsTool:
    """Tool for getting available prediction markets."""

    name = "get_delphi_markets"
    description = "Get list of available prediction markets on Delphi"

    def __init__(self, delphi_connector: DelphiConnector):
        self.delphi_connector = delphi_connector

    def run(
        self,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get available markets."""
        logger.info(f"Getting Delphi markets: category={category}, status={status}")

        markets = self.delphi_connector.get_markets(
            category=category,
            status=status,
            limit=limit,
        )

        return {
            "markets": markets,
            "count": len(markets),
            "filter": {"category": category, "status": status, "limit": limit},
            "message": f"Found {len(markets)} prediction markets"
        }


class PlacePredictionBetTool:
    """Tool for placing prediction bets."""

    name = "place_prediction_bet"
    description = "Place a bet on a Delphi prediction market"

    def __init__(self, delphi_connector: DelphiConnector):
        self.delphi_connector = delphi_connector

    def run(
        self,
        market_id: str,
        outcome: str,
        amount: float,
        odds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place a prediction bet."""
        logger.info(f"Placing Delphi bet: {amount} USDC on {outcome} for {market_id}")

        try:
            result = self.delphi_connector.place_bet(
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
                "message": f"Bet placed successfully: {amount} USDC on {outcome}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to place bet: {str(e)}"
            }


class ClaimPredictionWinningsTool:
    """Tool for claiming prediction winnings."""

    name = "claim_prediction_winnings"
    description = "Claim winnings from a resolved Delphi prediction bet"

    def __init__(self, delphi_connector: DelphiConnector):
        self.delphi_connector = delphi_connector

    def run(
        self,
        bet_id: str,
    ) -> Dict[str, Any]:
        """Claim winnings from a bet."""
        logger.info(f"Claiming Delphi winnings for bet: {bet_id}")

        try:
            result = self.delphi_connector.claim_winnings(bet_id=bet_id)

            return {
                "success": result.get("success", False),
                "bet_id": bet_id,
                "did_win": result.get("did_win", False),
                "payout_usd": result.get("payout_usd", 0.0),
                "profit_usd": result.get("profit_usd", 0.0),
                "winning_outcome": result.get("winning_outcome"),
                "status": "claimed",
                "message": f"Winnings claimed: {result.get('payout_usd', 0.0)} USDC"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to claim winnings: {str(e)}"
            }


class GetPredictionBetTool:
    """Tool for getting prediction bet details."""

    name = "get_prediction_bet"
    description = "Get details of a specific prediction bet"

    def __init__(self, delphi_connector: DelphiConnector):
        self.delphi_connector = delphi_connector

    def run(
        self,
        bet_id: str,
    ) -> Dict[str, Any]:
        """Get bet details."""
        logger.info(f"Getting Delphi bet details: {bet_id}")

        try:
            bet = self.delphi_connector.get_bet(bet_id=bet_id)

            return {
                "bet_id": bet_id,
                "market_id": bet.get("market_id"),
                "market_question": bet.get("market_question"),
                "outcome": bet.get("outcome"),
                "amount_usd": bet.get("amount_usd"),
                "odds": bet.get("odds"),
                "status": bet.get("status"),
                "created_at": bet.get("created_at"),
                "message": f"Bet details retrieved: {bet_id}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get bet details: {str(e)}"
            }


class GetMarketOutcomesTool:
    """Tool for getting market outcomes."""

    name = "get_market_outcomes"
    description = "Get current outcomes and odds for a Delphi prediction market"

    def __init__(self, delphi_connector: DelphiConnector):
        self.delphi_connector = delphi_connector

    def run(
        self,
        market_id: str,
    ) -> Dict[str, Any]:
        """Get market outcomes."""
        logger.info(f"Getting Delphi market outcomes: {market_id}")

        try:
            outcomes = self.delphi_connector.get_market_outcomes(market_id=market_id)

            return {
                "market_id": market_id,
                "question": outcomes.get("question"),
                "outcomes": outcomes.get("outcomes"),
                "odds": outcomes.get("odds"),
                "implied_probabilities": outcomes.get("implied_probabilities"),
                "total_volume_usd": outcomes.get("total_volume_usd"),
                "liquidity_usd": outcomes.get("liquidity_usd"),
                "message": f"Market outcomes retrieved: {market_id}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get market outcomes: {str(e)}"
            }
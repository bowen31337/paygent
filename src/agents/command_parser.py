"""
Natural language command parser for Paygent agent.

This module provides sophisticated parsing of natural language payment commands
using pattern matching and intent recognition.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    """Parsed command with intent and parameters."""

    intent: str  # e.g., "payment", "swap", "balance_check", "service_discovery", "perpetual_trade"
    action: str  # e.g., "pay", "transfer", "swap", "check", "open"
    parameters: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    raw_command: str


class CommandParser:
    """
    Parse natural language commands into structured intents.

    Uses pattern matching and keyword analysis to understand user intent.
    """

    # Patterns for different command types
    PATTERNS = {
        "payment": [
            r"pay\s+([\d.]+)\s+(\w+)\s+to\s+(.+)$",  # Capture everything after "to"
            r"pay\s+([\d.]+)\s+(\w+)\s+for\s+(.+)$",  # Alternative: "for" instead of "to"
            r"transfer\s+([\d.]+)\s+(\w+)\s+to\s+(.+)$",
            r"send\s+([\d.]+)\s+(\w+)\s+to\s+(.+)$",
        ],
        "swap": [
            r"swap\s+([\d.]+)\s+(\w+)\s+(?:for|to)\s+(\w+)",
            r"exchange\s+([\d.]+)\s+(\w+)\s+(?:for|to)\s+(\w+)",
            r"trade\s+([\d.]+)\s+(\w+)\s+(?:for|to)\s+(\w+)",
        ],
        "perpetual_trade": [
            r"(?:open|long|short)\s+(?:a\s+)?([\d.]+)\s+(\w+)\s+(long|short)\s+(?:position\s+)?(?:on\s+)?(\w+)",
            r"(?:open|long|short)\s+(?:a\s+)?([\d.]+)\s+(\w+)\s+(?:position\s+)?(?:on\s+)?(\w+)",
            r"(?:open|long|short)\s+(?:a\s+)?([\d.]+)\s+(\w+)\s+(?:position\s+)?(?:on\s+)?(\w+)\s+with\s+([\d.]+)x\s+leverage",
        ],
        "balance_check": [
            r"(?:check|show|get|what(?:'s| is))\s+(?:my\s+)?(?:wallet\s+)?balance",
            r"how\s+much\s+(\w+)\s+do\s+i\s+have",
            r"(?:check|show|get)\s+(\w+)\s+balance",
        ],
        "service_discovery": [
            r"(?:find|search|discover|list)\s+(?:for\s+)?services?",
            r"what\s+services?\s+(?:are\s+)?available",
            r"find\s+(\w+)\s+services?",
        ],
    }

    # Keywords for intent detection
    INTENT_KEYWORDS = {
        "payment": ["pay", "transfer", "send", "payment"],
        "swap": ["swap", "exchange", "trade"],
        "perpetual_trade": ["long", "short", "position", "leverage", "perpetual"],
        "balance_check": ["balance", "how much", "check"],
        "service_discovery": ["find", "search", "discover", "list services", "available"],
    }

    def __init__(self):
        """Initialize the command parser."""
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.compiled_patterns = {}
        for intent, patterns in self.PATTERNS.items():
            self.compiled_patterns[intent] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in patterns
            ]

    def parse(self, command: str) -> ParsedCommand:
        """
        Parse a natural language command.

        Args:
            command: Raw natural language command from user

        Returns:
            ParsedCommand with detected intent and parameters
        """
        command = command.strip()
        logger.info(f"Parsing command: {command}")

        # Try pattern matching first (most accurate)
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(command)
                if match:
                    parsed = self._extract_parameters_from_match(
                        intent, match, command
                    )
                    logger.info(f"Pattern matched: intent={intent}, confidence={parsed.confidence}")
                    return parsed

        # Fallback to keyword matching
        return self._parse_by_keywords(command)

    def _extract_parameters_from_match(
        self, intent: str, match: re.Match, raw_command: str
    ) -> ParsedCommand:
        """Extract parameters from regex match."""
        groups = match.groups()

        if intent == "payment":
            # Pattern: pay 0.10 USDC to service
            recipient = groups[2]
            return ParsedCommand(
                intent="payment",
                action="pay",
                parameters={
                    "amount": float(groups[0]),
                    "token": groups[1].upper(),
                    "recipient": recipient,
                },
                confidence=0.95,
                raw_command=raw_command,
            )

        elif intent == "swap":
            # Pattern: swap 10 CRO for USDC
            return ParsedCommand(
                intent="swap",
                action="swap",
                parameters={
                    "from_token": groups[1].upper(),
                    "to_token": groups[2].upper(),
                    "amount": float(groups[0]),
                },
                confidence=0.95,
                raw_command=raw_command,
            )

        elif intent == "perpetual_trade":
            # Pattern: open 100 USDC long position on BTC with 10x leverage
            # Groups: [0]=amount, [1]=token, [2]=direction (optional), [3]=symbol, [4]=leverage (optional)
            amount = float(groups[0])
            token = groups[1].upper()

            # Handle different pattern variations
            if len(groups) >= 4 and groups[3]:
                # Pattern with direction and symbol
                direction = groups[2] if groups[2] else "long"
                symbol = groups[3]
            else:
                # Pattern without explicit direction
                direction = "long"  # Default to long
                symbol = groups[2] if len(groups) > 2 else "BTC"

            # Check for leverage in groups
            leverage = 10.0  # Default leverage
            if len(groups) > 4 and groups[4]:
                leverage = float(groups[4])

            return ParsedCommand(
                intent="perpetual_trade",
                action="open",
                parameters={
                    "amount": amount,
                    "token": token,
                    "direction": direction.lower(),
                    "symbol": symbol.upper(),
                    "leverage": leverage,
                },
                confidence=0.95,
                raw_command=raw_command,
            )

        elif intent == "balance_check":
            # Pattern: check balance
            tokens = [g.upper() for g in groups if g] if groups else ["CRO", "USDC"]
            return ParsedCommand(
                intent="balance_check",
                action="check",
                parameters={
                    "tokens": tokens,
                },
                confidence=0.90,
                raw_command=raw_command,
            )

        elif intent == "service_discovery":
            # Pattern: find services
            category = groups[0] if groups else None
            return ParsedCommand(
                intent="service_discovery",
                action="discover",
                parameters={
                    "category": category.lower() if category else None,
                },
                confidence=0.85,
                raw_command=raw_command,
            )

        # Fallback
        return ParsedCommand(
            intent="unknown",
            action="unknown",
            parameters={},
            confidence=0.0,
            raw_command=raw_command,
        )

    def _parse_by_keywords(self, command: str) -> ParsedCommand:
        """
        Parse command using keyword matching (fallback).

        Scores each intent based on keyword matches in the command.
        """
        command_lower = command.lower()
        scores = {}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(
                1 for keyword in keywords if keyword in command_lower
            )
            if score > 0:
                scores[intent] = score / len(keywords)

        if not scores:
            return ParsedCommand(
                intent="unknown",
                action="unknown",
                parameters={},
                confidence=0.0,
                raw_command=command,
            )

        # Get highest scoring intent
        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] * 0.7, 0.7)  # Max 0.7 for keyword matching

        logger.info(f"Keyword matched: intent={best_intent}, confidence={confidence}")

        # Extract basic parameters
        parameters = self._extract_basic_parameters(command, best_intent)

        return ParsedCommand(
            intent=best_intent,
            action=best_intent.split("_")[0],
            parameters=parameters,
            confidence=confidence,
            raw_command=command,
        )

    def _extract_basic_parameters(self, command: str, intent: str) -> Dict[str, Any]:
        """Extract basic parameters from command string."""
        parameters = {}
        command_lower = command.lower()

        # Extract amounts (e.g., "0.10", "100")
        amounts = re.findall(r"([\d.]+)\s*(\w+)", command)
        if amounts:
            if intent == "payment":
                parameters["amount"] = float(amounts[0][0])
                parameters["token"] = amounts[0][1].upper()
            elif intent == "swap":
                if len(amounts) >= 1:
                    parameters["amount"] = float(amounts[0][0])
                    parameters["from_token"] = amounts[0][1].upper()
                if len(amounts) >= 2:
                    parameters["to_token"] = amounts[1][1].upper()
            elif intent == "perpetual_trade":
                if len(amounts) >= 1:
                    parameters["amount"] = float(amounts[0][0])
                    parameters["token"] = amounts[0][1].upper()

        # Extract tokens
        tokens = re.findall(r"\b(CRO|USDC|USDT|ETH|WBTC|BTC)\b", command, re.IGNORECASE)
        if tokens:
            parameters["tokens"] = list(set([t.upper() for t in tokens]))

        # Extract categories
        categories = re.findall(
            r"\b(market.?data|defi|prediction|trading|analytics)\b",
            command,
            re.IGNORECASE
        )
        if categories:
            parameters["category"] = categories[0].lower()

        # Extract direction for perpetual trades
        if intent == "perpetual_trade":
            if "long" in command_lower:
                parameters["direction"] = "long"
            elif "short" in command_lower:
                parameters["direction"] = "short"
            else:
                parameters["direction"] = "long"  # Default

            # Extract symbol
            symbol_match = re.search(r"\b(BTC|ETH|CRO)\b", command, re.IGNORECASE)
            if symbol_match:
                parameters["symbol"] = symbol_match.group(1).upper()

            # Extract leverage
            leverage_match = re.search(r"([\d.]+)x\s+leverage", command_lower)
            if leverage_match:
                parameters["leverage"] = float(leverage_match.group(1))

        return parameters


def test_parser():
    """Test the command parser with sample commands."""
    parser = CommandParser()

    test_commands = [
        "Pay 0.10 USDC to API service",
        "Check my wallet balance",
        "Swap 10 CRO for USDC",
        "How much USDC do I have",
        "Find available services",
        "Transfer 50 USDC to market data feed",
        "Exchange 100 CRO to USDC",
        "What is my balance",
        "Open a 100 USDC long position on BTC with 10x leverage",
        "Open a 50 USDC short position on ETH",
        "Long 200 USDC BTC",
        "Short 100 USDC ETH with 5x leverage",
    ]

    print("Command Parser Test Results")
    print("=" * 80)

    for cmd in test_commands:
        parsed = parser.parse(cmd)
        print(f"\nCommand: {cmd}")
        print(f"  Intent: {parsed.intent}")
        print(f"  Confidence: {parsed.confidence:.2f}")
        print(f"  Parameters: {parsed.parameters}")


if __name__ == "__main__":
    test_parser()

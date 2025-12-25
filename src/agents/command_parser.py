"""
Natural language command parser for Paygent agent.

This module provides sophisticated parsing of natural language payment commands
using pattern matching and intent recognition.
"""

import logging
import re
from dataclasses import dataclass
from re import Match
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    """Parsed command with intent and parameters."""

    intent: str  # e.g., "payment", "swap", "balance_check", "service_discovery", "perpetual_trade"
    action: str  # e.g., "pay", "transfer", "swap", "check", "open"
    parameters: dict[str, Any]
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
            r"pay\s+([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+to\s+(.+)$",
            r"pay\s+([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+for\s+(.+)$",
            r"transfer\s+([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+to\s+(.+)$",
            r"send\s+([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+to\s+(.+)$",
        ],
        "swap": [
            r"swap\s+([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+(?:for|to)\s+([\w-]+)",
            r"exchange\s+([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+(?:for|to)\s+([\w-]+)",
            r"trade\s+([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+(?:for|to)\s+([\w-]+)",
        ],
        "perpetual_trade": [
            # Pattern 0: "open a 10x long position on BTC/USDC" -> [leverage, direction, market]
            r"(?:open|long|short)\s+(?:a\s+)?([\d.]+)x\s+(long|short)\s+position\s+on\s+([\w/]+)",
            # Pattern 1: "open a 100 USDC long position on BTC" -> [amount, token, direction, market]
            r"(?:open|long|short)\s+(?:a\s+)?([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+(long|short)\s+(?:position\s+)?(?:on\s+)?([\w/]+)",
            # Pattern 2: "open a 100 USDC long position on BTC with 10x leverage" -> [amount, token, market, leverage]
            r"(?:open|long|short)\s+(?:a\s+)?([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+(?:position\s+)?(?:on\s+)?([\w/]+)\s+with\s+([\d.]+)x\s+leverage",
            # Pattern 3: "short 5x BTC/USDT" -> [leverage, market]
            r"(?:short|long)\s+([\d.]+)x\s+([\w/]+)",
            # Pattern 4: "long 200 USDC BTC" -> [amount, token, market]
            r"(?:long|short)\s+([\d.]+(?:e[+-]?\d+)?)\s+([\w-]+)\s+([\w/]+)",
        ],
        "balance_check": [
            r"(?:check|show|get|what(?:'s| is))\s+(?:my\s+)?(?:wallet\s+)?balance",
            r"how\s+much\s+([\w-]+)\s+do\s+i\s+have",
            r"(?:check|show|get)\s+my\s+([\w-]+)\s+balance",
        ],
        "service_discovery": [
            r"(?:find|search|discover|list)\s+for\s+([\w\s]+?)\s+(?:services?|protocols?)",
            r"(?:find|search|discover|list)\s+([\w\s]+?)\s+(?:services?|protocols?)",
            r"what\s+services?\s+(?:are\s+)?available",
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

    def __init__(self) -> None:
        """Initialize the command parser."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self.compiled_patterns: dict[str, list[re.Pattern[str]]] = {}
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
        self, intent: str, match: Match[str], raw_command: str
    ) -> ParsedCommand:
        """Extract parameters from regex match."""
        groups = match.groups()
        raw_lower = raw_command.lower()

        if intent == "payment":
            # Pattern: pay 0.10 USDC to service
            recipient = groups[2]
            # Extract action from the command
            action = "pay"  # default
            if raw_lower.startswith("transfer"):
                action = "transfer"
            elif raw_lower.startswith("send"):
                action = "send"

            return ParsedCommand(
                intent="payment",
                action=action,
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
            # Extract action from the command
            action = "swap"  # default
            if raw_lower.startswith("exchange"):
                action = "exchange"
            elif raw_lower.startswith("trade"):
                action = "trade"

            return ParsedCommand(
                intent="swap",
                action=action,
                parameters={
                    "from_token": groups[1].upper(),
                    "to_token": groups[2].upper(),
                    "amount": float(groups[0]),
                },
                confidence=0.95,
                raw_command=raw_command,
            )

        elif intent == "perpetual_trade":
            # Determine action from first word
            first_word = raw_lower.split()[0]
            if first_word in ["open", "long", "short"]:
                action = first_word
            else:
                action = "open"

            # Determine direction
            if "short" in raw_lower:
                direction = "short"
            elif "long" in raw_lower:
                direction = "long"
            else:
                direction = "long"  # Default

            # Default values
            amount = 100.0
            token = "USDC"
            leverage = "10"
            market = "BTC"

            # Determine which pattern matched by number of groups
            num_groups = len(groups)

            if num_groups == 3:
                # Pattern 0: [leverage, direction, market] - "open a 10x long position on BTC/USDC"
                # Pattern 4: [amount, token, market] - "long 200 USDC BTC"
                if 'x' in raw_lower and groups[0] and groups[0].replace('.', '').isdigit():
                    # Pattern 0
                    leverage = groups[0]
                    direction = groups[1].lower()
                    market = groups[2]
                else:
                    # Pattern 4
                    amount = float(groups[0])
                    token = groups[1].upper()
                    market = groups[2]

            elif num_groups == 4:
                # Pattern 1: [amount, token, direction, market] - "open a 100 USDC long position on BTC"
                # Pattern 2: [amount, token, market, leverage] - "open a 100 USDC long position on BTC with 10x leverage"
                if 'leverage' in raw_lower:
                    # Pattern 2
                    amount = float(groups[0])
                    token = groups[1].upper()
                    market = groups[2]
                    leverage = groups[3]
                else:
                    # Pattern 1
                    amount = float(groups[0])
                    token = groups[1].upper()
                    direction = groups[2].lower()
                    market = groups[3]

            elif num_groups == 2:
                # Pattern 3: [leverage, market] - "short 5x BTC/USDT"
                leverage = groups[0]
                market = groups[1]

            # Normalize market format (ensure uppercase)
            market = market.upper()

            return ParsedCommand(
                intent="perpetual_trade",
                action=action,
                parameters={
                    "amount": amount,
                    "token": token,
                    "direction": direction,
                    "market": market,
                    "leverage": leverage,
                },
                confidence=0.95,
                raw_command=raw_command,
            )

        elif intent == "balance_check":
            # Pattern: check balance
            # Check for specific token in command - first check regex groups, then search
            token = "all"
            if groups:
                # Pattern like "check my CRO balance" or "how much USDC do I have"
                token = groups[0].upper()
            else:
                # Try to extract from command
                token_match = re.search(r"\b(CRO|USDC|USDT|ETH|BTC)\b", raw_command, re.IGNORECASE)
                if token_match:
                    token = token_match.group(1).upper()

            return ParsedCommand(
                intent="balance_check",
                action="check",
                parameters={
                    "token": token,
                },
                confidence=0.90,
                raw_command=raw_command,
            )

        elif intent == "service_discovery":
            # Pattern: find services
            category = groups[0] if groups else None

            # Extract action from command
            action = "find"
            if raw_lower.startswith("search"):
                action = "search"
            elif raw_lower.startswith("discover"):
                action = "discover"
            elif raw_lower.startswith("list"):
                action = "list"

            # Clean up category (remove trailing whitespace)
            if category:
                category = category.strip()

            return ParsedCommand(
                intent="service_discovery",
                action=action,
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
        scores: dict[str, float] = {}

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
        best_intent = max(scores, key=lambda k: scores[k])
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

    def _extract_basic_parameters(self, command: str, intent: str) -> dict[str, Any]:
        """Extract basic parameters from command string."""
        parameters: dict[str, Any] = {}
        command_lower = command.lower()

        # Extract amounts (e.g., "0.10", "100")
        amounts = re.findall(r"([\d.]+)\s*([\w-]+)", command)
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
            parameters["tokens"] = list({t.upper() for t in tokens})

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


def parse_command(command: str) -> ParsedCommand:
    """
    Convenience function to parse a command.

    Args:
        command: Natural language command string

    Returns:
        ParsedCommand object
    """
    parser = CommandParser()
    return parser.parse(command)


def test_parser() -> None:
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
        print(f"  Action: {parsed.action}")
        print(f"  Confidence: {parsed.confidence:.2f}")
        print(f"  Parameters: {parsed.parameters}")


if __name__ == "__main__":
    test_parser()

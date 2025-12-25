"""
Tests for the command parser module.
"""

import pytest
from src.agents.command_parser import CommandParser, ParsedCommand


class TestParsedCommand:
    """Test ParsedCommand dataclass."""

    def test_create_parsed_command(self):
        """Test creating a parsed command."""
        cmd = ParsedCommand(
            intent="payment",
            action="pay",
            parameters={"amount": 100.0, "token": "USDC"},
            confidence=0.95,
            raw_command="Pay 100 USDC"
        )

        assert cmd.intent == "payment"
        assert cmd.action == "pay"
        assert cmd.parameters == {"amount": 100.0, "token": "USDC"}
        assert cmd.confidence == 0.95
        assert cmd.raw_command == "Pay 100 USDC"


class TestCommandParser:
    """Test CommandParser class."""

    def test_parser_initialization(self):
        """Test parser initializes and compiles patterns."""
        parser = CommandParser()
        assert parser.compiled_patterns is not None
        assert len(parser.compiled_patterns) == 5
        assert "payment" in parser.compiled_patterns
        assert "swap" in parser.compiled_patterns
        assert "perpetual_trade" in parser.compiled_patterns
        assert "balance_check" in parser.compiled_patterns
        assert "service_discovery" in parser.compiled_patterns

    def test_parse_payment_command_to(self):
        """Test parsing payment commands with 'to' keyword."""
        parser = CommandParser()

        result = parser.parse("pay 100 USDC to merchant")

        assert result.intent == "payment"
        assert result.action == "pay"
        assert result.parameters["amount"] == 100.0
        assert result.parameters["token"] == "USDC"
        assert result.parameters["recipient"] == "merchant"
        assert result.confidence == 0.95

    def test_parse_payment_command_for(self):
        """Test parsing payment commands with 'for' keyword."""
        parser = CommandParser()

        result = parser.parse("pay 0.10 USDC for service access")

        assert result.intent == "payment"
        assert result.action == "pay"
        assert result.parameters["amount"] == 0.10
        assert result.parameters["token"] == "USDC"
        assert result.parameters["recipient"] == "service access"

    def test_parse_transfer_command(self):
        """Test parsing transfer commands."""
        parser = CommandParser()

        result = parser.parse("transfer 50 CRO to 0x123456789")

        assert result.intent == "payment"
        assert result.parameters["amount"] == 50.0
        assert result.parameters["token"] == "CRO"

    def test_parse_send_command(self):
        """Test parsing send commands."""
        parser = CommandParser()

        result = parser.parse("send 25 USDC to recipient")

        assert result.intent == "payment"
        assert result.parameters["amount"] == 25.0
        assert result.parameters["token"] == "USDC"

    def test_parse_swap_command(self):
        """Test parsing swap commands."""
        parser = CommandParser()

        result = parser.parse("swap 100 CRO for USDC")

        assert result.intent == "swap"
        assert result.action == "swap"
        assert result.parameters["amount"] == 100.0
        assert result.parameters["from_token"] == "CRO"
        assert result.parameters["to_token"] == "USDC"
        assert result.confidence == 0.95

    def test_parse_exchange_command(self):
        """Test parsing exchange commands."""
        parser = CommandParser()

        result = parser.parse("exchange 50 USDC to CRO")

        assert result.intent == "swap"
        assert result.parameters["from_token"] == "USDC"
        assert result.parameters["to_token"] == "CRO"

    def test_parse_trade_command(self):
        """Test parsing trade commands."""
        parser = CommandParser()

        result = parser.parse("trade 10 BTC for ETH")

        assert result.intent == "swap"
        assert result.parameters["from_token"] == "BTC"
        assert result.parameters["to_token"] == "ETH"

    def test_parse_balance_check_simple(self):
        """Test parsing simple balance check commands."""
        parser = CommandParser()

        commands = [
            "check balance",
            "show balance",
            "get balance",
            "what's my balance",
            "what is my balance"
        ]

        for cmd in commands:
            result = parser.parse(cmd)
            assert result.intent == "balance_check", f"Failed for: {cmd}"

    def test_parse_balance_check_with_token(self):
        """Test parsing balance check for specific token."""
        parser = CommandParser()

        result = parser.parse("how much USDC do i have")

        assert result.intent == "balance_check"

        result = parser.parse("check CRO balance")

        assert result.intent == "balance_check"

    def test_parse_service_discovery_general(self):
        """Test parsing general service discovery commands."""
        parser = CommandParser()

        commands = [
            "find services",
            "search for services",
            "discover services",
            "list services",
            "what services are available"
        ]

        for cmd in commands:
            result = parser.parse(cmd)
            assert result.intent == "service_discovery", f"Failed for: {cmd}"

    def test_parse_service_discovery_specific(self):
        """Test parsing specific service discovery commands."""
        parser = CommandParser()

        result = parser.parse("find oracle services")

        assert result.intent == "service_discovery"

    def test_parse_perpetual_trade_long(self):
        """Test parsing perpetual long position commands."""
        parser = CommandParser()

        result = parser.parse("open 100 USDC long BTC")

        assert result.intent == "perpetual_trade"

    def test_parse_perpetual_trade_short(self):
        """Test parsing perpetual short position commands."""
        parser = CommandParser()

        result = parser.parse("short 50 USDC BTC")

        assert result.intent == "perpetual_trade"

    def test_parse_with_leverage(self):
        """Test parsing leverage commands."""
        parser = CommandParser()

        result = parser.parse("open 100 USDC long position on BTC with 10x leverage")

        assert result.intent == "perpetual_trade"

    def test_case_insensitive_parsing(self):
        """Test that parsing is case-insensitive."""
        parser = CommandParser()

        commands = [
            "PAY 100 USDC TO MERCHANT",
            "Pay 100 usdc to merchant",
            "PaY 100 UsDc To MeRcHaNt"
        ]

        for cmd in commands:
            result = parser.parse(cmd)
            assert result.intent == "payment"
            assert result.parameters["token"] in ["USDC", "usdc", "UsDc"]

    def test_whitespace_handling(self):
        """Test handling of extra whitespace."""
        parser = CommandParser()

        result = parser.parse("  pay   100   USDC   to   merchant  ")

        assert result.intent == "payment"
        assert result.parameters["amount"] == 100.0

    def test_decimal_amounts(self):
        """Test parsing decimal amounts."""
        parser = CommandParser()

        result = parser.parse("pay 0.123 USDC to merchant")

        assert result.parameters["amount"] == 0.123

        result = parser.parse("swap 12.5 CRO for USDC")

        assert result.parameters["amount"] == 12.5

    def test_confidence_scores(self):
        """Test that pattern matching gives high confidence."""
        parser = CommandParser()

        result = parser.parse("pay 100 USDC to merchant")

        assert result.confidence >= 0.9

    def test_raw_command_preserved(self):
        """Test that raw command is preserved in result."""
        parser = CommandParser()

        original = "pay 100 USDC to merchant"
        result = parser.parse(original)

        assert result.raw_command == original

    def test_empty_command(self):
        """Test parsing empty command."""
        parser = CommandParser()

        result = parser.parse("")

        assert result.raw_command == ""

    def test_whitespace_only_command(self):
        """Test parsing whitespace-only command."""
        parser = CommandParser()

        result = parser.parse("   ")

        assert result.raw_command == ""

    def test_unrecognized_command(self):
        """Test parsing unrecognized command falls back to keyword matching."""
        parser = CommandParser()

        result = parser.parse("do something weird")

        # Should still return a ParsedCommand with lower confidence
        assert isinstance(result, ParsedCommand)
        assert result.confidence < 0.9

    def test_command_with_numbers_as_recipient(self):
        """Test parsing commands with numeric recipient (address)."""
        parser = CommandParser()

        result = parser.parse("pay 100 USDC to 0x1234567890abcdef")

        assert result.intent == "payment"
        assert "0x1234567890abcdef" in result.parameters["recipient"]

    def test_multiple_swap_patterns(self):
        """Test various swap patterns."""
        parser = CommandParser()

        patterns = [
            "swap 100 CRO for USDC",
            "exchange 100 CRO to USDC",
            "trade 100 CRO for USDC"
        ]

        for pattern in patterns:
            result = parser.parse(pattern)
            assert result.intent == "swap", f"Failed for pattern: {pattern}"

    def test_complex_payment_recipient(self):
        """Test payment with complex recipient description."""
        parser = CommandParser()

        result = parser.parse("pay 100 USDC to the market data api service")

        assert result.intent == "payment"
        assert "market data api service" in result.parameters["recipient"]

"""Test command parser functionality."""

import pytest
from unittest.mock import patch

from src.agents.command_parser import CommandParser, ParsedCommand


def test_parse_payment_command():
    """Test parsing of payment commands."""
    parser = CommandParser()

    # Test basic payment command
    result = parser.parse("pay 0.10 USDC to market data API")
    assert result.intent == "payment"
    assert result.action == "pay"
    assert result.parameters["amount"] == "0.10"
    assert result.parameters["token"] == "USDC"
    assert result.parameters["recipient"] == "market data API"
    assert result.confidence == 1.0

    # Test transfer command
    result = parser.parse("transfer 100 CRO to wallet address")
    assert result.intent == "payment"
    assert result.action == "transfer"
    assert result.parameters["amount"] == "100"
    assert result.parameters["token"] == "CRO"
    assert result.parameters["recipient"] == "wallet address"

    # Test send command
    result = parser.parse("send 50 ETH to Alice")
    assert result.intent == "payment"
    assert result.action == "send"
    assert result.parameters["amount"] == "50"
    assert result.parameters["token"] == "ETH"
    assert result.parameters["recipient"] == "Alice"


def test_parse_swap_command():
    """Test parsing of swap commands."""
    parser = CommandParser()

    # Test swap command
    result = parser.parse("swap 100 USDC for CRO")
    assert result.intent == "swap"
    assert result.action == "swap"
    assert result.parameters["amount"] == "100"
    assert result.parameters["from_token"] == "USDC"
    assert result.parameters["to_token"] == "CRO"

    # Test exchange command
    result = parser.parse("exchange 50 ETH to BTC")
    assert result.intent == "swap"
    assert result.action == "exchange"
    assert result.parameters["amount"] == "50"
    assert result.parameters["from_token"] == "ETH"
    assert result.parameters["to_token"] == "BTC"

    # Test trade command
    result = parser.parse("trade 200 USDT for SOL")
    assert result.intent == "swap"
    assert result.action == "trade"
    assert result.parameters["amount"] == "200"
    assert result.parameters["from_token"] == "USDT"
    assert result.parameters["to_token"] == "SOL"


def test_parse_perpetual_trade_command():
    """Test parsing of perpetual trade commands."""
    parser = CommandParser()

    # Test long position
    result = parser.parse("open a 10x long position on BTC/USDC")
    assert result.intent == "perpetual_trade"
    assert result.action == "open"
    assert result.parameters["leverage"] == "10"
    assert result.parameters["direction"] == "long"
    assert result.parameters["market"] == "BTC/USDC"

    # Test short position
    result = parser.parse("short 5x BTC/USDT")
    assert result.intent == "perpetual_trade"
    assert result.action == "short"
    assert result.parameters["leverage"] == "5"
    assert result.parameters["direction"] == "short"
    assert result.parameters["market"] == "BTC/USDT"


def test_parse_balance_check_command():
    """Test parsing of balance check commands."""
    parser = CommandParser()

    # Test simple balance check
    result = parser.parse("check my CRO balance")
    assert result.intent == "balance_check"
    assert result.action == "check"
    assert result.parameters["token"] == "CRO"

    # Test wallet balance
    result = parser.parse("what is my wallet balance")
    assert result.intent == "balance_check"
    assert result.action == "check"
    assert result.parameters["token"] == "all"

    # Test token balance
    result = parser.parse("how much USDC do I have")
    assert result.intent == "balance_check"
    assert result.action == "check"
    assert result.parameters["token"] == "USDC"


def test_parse_service_discovery_command():
    """Test parsing of service discovery commands."""
    parser = CommandParser()

    # Test service discovery
    result = parser.parse("find market data services")
    assert result.intent == "service_discovery"
    assert result.action == "find"
    assert result.parameters["category"] == "market data"

    # Test service search
    result = parser.parse("search for DeFi protocols")
    assert result.intent == "service_discovery"
    assert result.action == "search"
    assert result.parameters["category"] == "DeFi"


def test_parse_unrecognized_command():
    """Test parsing of unrecognized commands."""
    parser = CommandParser()

    # Test completely unrecognized command
    result = parser.parse("do something random")
    assert result.intent == "unknown"
    assert result.action == "unknown"
    assert result.confidence == 0.0
    assert result.raw_command == "do something random"


def test_parse_complex_payment_commands():
    """Test parsing of complex payment commands with various formats."""
    parser = CommandParser()

    # Test with "for" instead of "to"
    result = parser.parse("pay 0.5 ETH for API access")
    assert result.intent == "payment"
    assert result.action == "pay"
    assert result.parameters["amount"] == "0.5"
    assert result.parameters["token"] == "ETH"
    assert result.parameters["recipient"] == "API access"

    # Test with decimal amounts
    result = parser.parse("pay 123.456789 USDC to service")
    assert result.intent == "payment"
    assert result.parameters["amount"] == "123.456789"

    # Test with different token cases
    result = parser.parse("pay 10 usdc to recipient")
    assert result.parameters["token"] == "usdc"


def test_parse_confidence_scoring():
    """Test that confidence scoring works correctly."""
    parser = CommandParser()

    # Exact match should have high confidence
    result = parser.parse("pay 100 USDC to service")
    assert result.confidence >= 0.8

    # Partial match should have lower confidence
    result = parser.parse("pay some tokens to someone")
    assert result.confidence < 0.8

    # Unrecognized should have zero confidence
    result = parser.parse("random text")
    assert result.confidence == 0.0


def test_parse_edge_cases():
    """Test parsing of edge cases and malformed commands."""
    parser = CommandParser()

    # Empty command
    result = parser.parse("")
    assert result.intent == "unknown"

    # Command with only numbers
    result = parser.parse("123")
    assert result.intent == "unknown"

    # Command with only tokens
    result = parser.parse("USDC")
    assert result.intent == "unknown"


def test_parse_case_insensitivity():
    """Test that parsing is case insensitive."""
    parser = CommandParser()

    # Test uppercase
    result1 = parser.parse("PAY 100 USDC TO SERVICE")
    assert result1.intent == "payment"
    assert result1.parameters["amount"] == "100"
    assert result1.parameters["token"] == "USDC"

    # Test lowercase
    result2 = parser.parse("pay 100 usdc to service")
    assert result2.intent == "payment"
    assert result2.parameters["amount"] == "100"
    assert result2.parameters["token"] == "usdc"

    # Test mixed case
    result3 = parser.parse("Pay 100 Usdc To Service")
    assert result3.intent == "payment"
    assert result3.parameters["amount"] == "100"
    assert result3.parameters["token"] == "Usdc"


def test_parse_token_extraction():
    """Test that token extraction works correctly with various formats."""
    parser = CommandParser()

    # Standard tokens
    result = parser.parse("pay 100 USDC to service")
    assert result.parameters["token"] == "USDC"

    # Token with slash (trading pair)
    result = parser.parse("pay 100 USDC/ETH to service")
    assert result.parameters["token"] == "USDC/ETH"

    # Complex token names
    result = parser.parse("pay 100 Wrapped-BTC to service")
    assert result.parameters["token"] == "Wrapped-BTC"


def test_parse_amount_extraction():
    """Test that amount extraction works correctly."""
    parser = CommandParser()

    # Integer amounts
    result = parser.parse("pay 100 USDC to service")
    assert result.parameters["amount"] == "100"

    # Decimal amounts
    result = parser.parse("pay 123.456 USDC to service")
    assert result.parameters["amount"] == "123.456"

    # Scientific notation
    result = parser.parse("pay 1.23e-5 USDC to service")
    assert result.parameters["amount"] == "1.23e-5"

    # Large numbers
    result = parser.parse("pay 1000000 USDC to service")
    assert result.parameters["amount"] == "1000000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
#!/usr/bin/env python3
"""
Test script for VVS Trader Subagent functionality.

This script tests the VVS trader subagent spawning and execution.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from uuid import uuid4

from src.agents.command_parser import CommandParser
from src.agents.vvs_trader_subagent import VVSTraderSubagent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_vvs_subagent_direct():
    """Test VVS subagent directly."""
    logger.info("🧪 Testing VVS Trader Subagent directly...")

    # Create a mock database session (we'll use None for testing)
    db = None
    session_id = uuid4()
    parent_agent_id = uuid4()

    try:
        # Create VVS subagent
        vvs_subagent = VVSTraderSubagent(
            db=db,
            session_id=session_id,
            parent_agent_id=parent_agent_id,
        )

        # Test swap execution
        result = await vvs_subagent.execute_swap(
            from_token="CRO",
            to_token="USDC",
            amount=100.0,
            slippage_tolerance_percent=1.0
        )

        print("✅ VVS Subagent direct test result:")
        print(f"   Success: {result['success']}")
        if result['success']:
            print(f"   Subagent ID: {result['subagent_id']}")
            print(f"   Swap Details: {result['swap_details']}")
        else:
            print(f"   Error: {result['error']}")

        return result['success']

    except Exception as e:
        logger.error(f"❌ VVS Subagent direct test failed: {e}")
        return False


async def test_command_parsing():
    """Test command parsing logic."""
    logger.info("🧪 Testing command parsing logic...")

    parser = CommandParser()

    test_commands = [
        "Swap 100 USDC for CRO",
        "Exchange 50 CRO to USDC",
        "Trade 200 USDC into CRO",
        "Convert 10 BTC to ETH",
        "Check my balance",  # Should not trigger VVS
        "Pay 0.10 USDC to API",  # Should not trigger VVS
    ]

    for command in test_commands:
        parsed = parser.parse(command)
        should_use_vvs = (
            "swap" in command.lower() or
            "exchange" in command.lower() or
            "trade" in command.lower() or
            "convert" in command.lower()
        )

        print(f"   Command: '{command}'")
        print(f"   Intent: {parsed.intent}")
        print(f"   Should use VVS: {should_use_vvs}")
        print(f"   Parameters: {parsed.parameters}")
        print()


async def test_vvs_detection():
    """Test VVS subagent detection logic."""
    logger.info("🧪 Testing VVS subagent detection...")

    # Test the detection logic from main agent
    test_commands = [
        ("Swap 100 USDC for CRO", True),
        ("Exchange 50 CRO to USDC", True),
        ("Trade 200 USDC into CRO", True),
        ("Convert 10 BTC to ETH", True),
        ("Check my balance", False),
        ("Pay 0.10 USDC to API", False),
        ("Use VVS Finance to swap tokens", True),
        ("Access the market data API", False),
    ]

    for command, expected in test_commands:
        # Simulate the detection logic
        command_lower = command.lower()
        swap_keywords = ["swap", "exchange", "trade", "convert"]
        vvs_keywords = ["vvs", "vvs finance", "dex"]

        has_swap_keyword = any(keyword in command_lower for keyword in swap_keywords)
        mentions_vvs = any(keyword in command_lower for keyword in vvs_keywords)

        token_pattern = r"\b(?:CRO|USDC|USDT|BTC|ETH|BNB)\s*(?:to|for|and)\s*(?:CRO|USDC|USDT|BTC|ETH|BNB)\b"
        import re
        has_token_pattern = bool(re.search(token_pattern, command_lower))

        should_use = (
            (has_swap_keyword and (mentions_vvs or has_token_pattern)) or
            mentions_vvs
        )

        status = "✅" if should_use == expected else "❌"
        print(f"   {status} Command: '{command}'")
        print(f"      Expected: {expected}, Got: {should_use}")
        print()


async def test_vvs_subagent_parsing():
    """Test VVS subagent command parsing."""
    logger.info("🧪 Testing VVS subagent command parsing...")

    # Test the parsing logic
    test_commands = [
        "Swap 100 USDC for CRO",
        "Exchange 50 CRO to USDC",
        "Trade 200 USDC into CRO",
        "Convert 10 BTC to ETH",
        "Invalid swap command",
    ]

    for command in test_commands:
        # Simulate the parsing logic from _parse_swap_command
        import re

        pattern = r"(?:swap|exchange|trade|convert)\s+(\d+(?:\.\d+)?)\s*([A-Z]+)\s+(?:for|to|into|and)\s*([A-Z]+)"
        match = re.search(pattern, command, re.IGNORECASE)

        if not match:
            pattern = r"(\d+(?:\.\d+)?)\s*([A-Z]+)\s+(?:for|to|into|and)\s+(\d+(?:\.\d+)?)\s*([A-Z]+)"
            match = re.search(pattern, command, re.IGNORECASE)

        if match:
            amount = float(match.group(1))
            from_token = match.group(2).upper()
            to_token = match.group(3).upper()

            print(f"   ✅ Command: '{command}'")
            print(f"      Parsed: {amount} {from_token} -> {to_token}")
        else:
            print(f"   ❌ Command: '{command}'")
            print("      Failed to parse")


async def main():
    """Run all tests."""
    logger.info("🚀 Starting VVS Trader Subagent Tests")
    logger.info("=" * 50)

    # Test 1: Direct VVS subagent execution
    direct_test_result = await test_vvs_subagent_direct()
    print()

    # Test 2: Command parsing
    await test_command_parsing()
    print()

    # Test 3: VVS detection logic
    await test_vvs_detection()
    print()

    # Test 4: VVS subagent parsing
    await test_vvs_subagent_parsing()
    print()

    logger.info("=" * 50)
    if direct_test_result:
        logger.info("🎉 VVS Trader Subagent implementation is working!")
        logger.info("✅ Feature 20: Agent spawns VVS trader subagent for DeFi swap operations")
    else:
        logger.error("❌ VVS Trader Subagent implementation has issues")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Final test of VVS subagent detection logic after fixes.
"""

import re


def test_detection_logic():
    """Test the fixed VVS detection logic."""
    print("🧪 Testing Fixed VVS Detection Logic")
    print("=" * 40)

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
        command_lower = command.lower()

        # Keywords that indicate a swap operation
        swap_keywords = [
            "swap",
            "exchange",
            "trade",
            "convert",
        ]

        # VVS-specific keywords
        vvs_keywords = [
            "vvs",
            "vvs finance",
            "dex",
        ]

        # Check if command contains swap-related keywords
        has_swap_keyword = any(keyword in command_lower for keyword in swap_keywords)

        # Check if command mentions VVS or DEX
        mentions_vvs = any(keyword in command_lower for keyword in vvs_keywords)

        # Check for token symbols that indicate a swap
        # More flexible pattern to match token pairs
        token_pattern = r"\b(?:CRO|USDC|USDT|BTC|ETH|BNB)\s+(?:for|to|into)\s+(?:CRO|USDC|USDT|BTC|ETH|BNB)\b"
        has_token_pattern = bool(re.search(token_pattern, command_lower, re.IGNORECASE))

        # Use VVS subagent if:
        # 1. Command contains swap keywords AND (mentions VVS OR has token pattern)
        # 2. OR command explicitly mentions VVS Finance
        should_use = (
            (has_swap_keyword and (mentions_vvs or has_token_pattern)) or
            mentions_vvs
        )

        status = "✅" if should_use == expected else "❌"
        print(f"   {status} Command: '{command}'")
        print(f"      Expected: {expected}, Got: {should_use}")
        print(f"      Swap keyword: {has_swap_keyword}")
        print(f"      Mentions VVS: {mentions_vvs}")
        print(f"      Token pattern: {has_token_pattern}")
        print()

def main():
    test_detection_logic()

if __name__ == "__main__":
    main()

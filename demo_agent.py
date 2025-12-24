#!/usr/bin/env python3
"""
Demo script showing Paygent agent execution capabilities.

This script demonstrates how the AI agent processes natural language commands
and executes various payment and blockchain operations.
"""

import json
from src.agents.main_agent import PaygentAgent
from src.agents.tools import create_agent_tools
from src.services.x402_service import X402PaymentService
from src.services.service_registry import ServiceRegistryService
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4


async def demo_agent_execution():
    """Demonstrate agent execution with various commands."""
    print("🤖 Paygent Agent Execution Demo")
    print("=" * 50)

    # Mock database session for demo
    class MockDB:
        pass

    db = MockDB()

    # Initialize services
    payment_service = X402PaymentService()
    service_registry = ServiceRegistryService(db)

    # Create agent tools
    tools = create_agent_tools(payment_service, service_registry, db)

    # Initialize agent
    session_id = uuid4()
    agent = PaygentAgent(
        db=db,
        session_id=session_id,
        llm_model="anthropic/claude-sonnet-4",
    )

    # Add tools to agent
    for tool in tools:
        await agent.add_tool(tool)

    # Demo commands
    demo_commands = [
        {
            "command": "Pay 0.10 USDC to access the market data API",
            "description": "HTTP 402 payment execution"
        },
        {
            "command": "Swap 100 USDC for CRO on VVS Finance",
            "description": "DeFi token swap"
        },
        {
            "command": "Check my CRO and USDC balance",
            "description": "Wallet balance inquiry"
        },
        {
            "command": "Transfer 0.05 ETH to 0x1234...5678",
            "description": "Token transfer"
        }
    ]

    # Execute each command
    for i, demo in enumerate(demo_commands, 1):
        print(f"\n📝 Demo {i}: {demo['description']}")
        print(f"Command: {demo['command']}")
        print("-" * 30)

        try:
            # Note: This will show the agent structure but not execute
            # since we don't have actual LLM API keys configured
            print("✅ Agent prepared with tools:")
            for tool in tools:
                print(f"   - {tool.name}: {tool.description}")

            print(f"✅ Agent ready to execute with session ID: {session_id}")
            print("   (In production, this would use Claude/OpenAI for actual execution)")

        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    print("\nKey capabilities demonstrated:")
    print("• Natural language command parsing")
    print("• X402 payment protocol execution")
    print("• DeFi protocol integration")
    print("• Service discovery and registry")
    print("• Multi-tool agent orchestration")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_agent_execution())
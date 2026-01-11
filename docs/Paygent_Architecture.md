# Paygent Architecture Document

## AI-Powered Multi-Agent Payment Orchestration Platform

**Technical Architecture & Implementation Guide**

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Component Specifications](#3-component-specifications)
4. [deepagents Integration](#4-deepagents-integration)
5. [x402 Payment Flow](#5-x402-payment-flow)
6. [Smart Contract Architecture](#6-smart-contract-architecture)
7. [API Specifications](#7-api-specifications)
8. [Data Models](#8-data-models)
9. [Security Architecture](#9-security-architecture)
10. [Infrastructure & Deployment](#10-infrastructure--deployment)
11. [Project Structure](#11-project-structure)
12. [Implementation Guide](#12-implementation-guide)

---

## 1. System Overview

### 1.1 High-Level Architecture

Paygent is built on a modular, layered architecture designed for:
- **Scalability**: Handle thousands of concurrent agent operations
- **Security**: Non-custodial design with human-in-the-loop controls
- **Extensibility**: Easy integration of new DeFi protocols and services
- **Reliability**: Fault-tolerant with graceful degradation

### 1.2 Technology Stack

| Layer | Technologies |
|-------|--------------|
| **Agent Framework** | deepagents 0.2.7, LangGraph, LangChain |
| **AI/LLM** | Claude Sonnet 4, OpenAI GPT-4 (fallback) |
| **Blockchain** | Cronos EVM, Solidity 0.8.x, ethers.js v6 |
| **x402** | @crypto.com/facilitator-client, EIP-712 |
| **Crypto.com SDK** | crypto-com-developer-platform-client (Python) |
| **MCP** | langchain-mcp-adapters |
| **Backend** | Python 3.11+, FastAPI, asyncio |
| **Database** | PostgreSQL 15, Redis 7 |
| **Infrastructure** | Docker, Kubernetes, AWS/GCP |
| **Monitoring** | Prometheus, Grafana, OpenTelemetry |

---

## 2. Architecture Diagram

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                    (CLI / Web Dashboard / API Client)                        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PAYGENT CORE                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      MAIN AGENT (deepagents)                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │  Planning   │  │  Filesystem │  │  Subagent   │                  │   │
│  │  │  Middleware │  │  Middleware │  │  Middleware │                  │   │
│  │  │(write_todos)│  │ (ls,read,   │  │  (task)     │                  │   │
│  │  │             │  │  write,edit)│  │             │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              CUSTOM MIDDLEWARE                               │   │   │
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │   │   │
│  │  │  │ X402Payment   │  │ CronosWallet  │  │ ServiceRegistry│  │   │   │
│  │  │  │ Middleware    │  │ Middleware    │  │ Middleware     │  │   │   │
│  │  │  └───────────────┘  └───────────────┘  └───────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                  │                                          │
│                    ┌─────────────┴─────────────┐                           │
│                    ▼                           ▼                           │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐         │
│  │        SUBAGENTS            │  │      TOOL REGISTRY          │         │
│  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │         │
│  │  │ VVS Finance Trader    │  │  │  │ x402_payment          │  │         │
│  │  │ - vvs_swap            │  │  │  │ discover_services     │  │         │
│  │  │ - vvs_add_liquidity   │  │  │  │ check_balance         │  │         │
│  │  │ - vvs_remove_liquidity│  │  │  │ transfer_tokens       │  │         │
│  │  └───────────────────────┘  │  │  │ get_market_data       │  │         │
│  │  ┌───────────────────────┐  │  │  └───────────────────────┘  │         │
│  │  │ Moonlander Trader     │  │  └─────────────────────────────┘         │
│  │  │ - open_position       │  │                                          │
│  │  │ - close_position      │  │                                          │
│  │  │ - set_stop_loss       │  │                                          │
│  │  └───────────────────────┘  │                                          │
│  │  ┌───────────────────────┐  │                                          │
│  │  │ Market Researcher     │  │                                          │
│  │  │ - mcp_query           │  │                                          │
│  │  │ - analyze_trends      │  │                                          │
│  │  └───────────────────────┘  │                                          │
│  └─────────────────────────────┘                                          │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  CRYPTO.COM MCP   │  │  x402 FACILITATOR │  │  SERVICE REGISTRY │
│  ┌─────────────┐  │  │  ┌─────────────┐  │  │  ┌─────────────┐  │
│  │ Market Data │  │  │  │   Verify    │  │  │  │  Discovery  │  │
│  │ Price Feeds │  │  │  │   Settle    │  │  │  │  Pricing    │  │
│  │ Order Books │  │  │  │   ~200ms    │  │  │  │  Reputation │  │
│  └─────────────┘  │  │  └─────────────┘  │  │  └─────────────┘  │
└───────────────────┘  └─────────┬─────────┘  └───────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CRONOS EVM                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  AgentWallet    │  │  PaymentRouter  │  │  ServiceRegistry│             │
│  │  Contract       │  │  Contract       │  │  Contract       │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        DEFI PROTOCOLS                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ VVS Finance │  │ Moonlander  │  │   Delphi    │                  │   │
│  │  │    (DEX)    │  │  (Perps)    │  │(Predictions)│                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Diagram

```
┌──────────┐    Natural Language     ┌──────────────┐
│   User   │ ───────────────────────▶│  Main Agent  │
└──────────┘    "Swap 100 USDC       └──────┬───────┘
                to CRO on VVS"              │
                                            │ 1. Parse Intent
                                            │ 2. Create Plan
                                            ▼
                                    ┌──────────────┐
                                    │ write_todos  │
                                    │  Planning    │
                                    └──────┬───────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
            ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
            │ Check Price  │      │ Check Balance│      │ Execute Swap │
            │ (MCP Query)  │      │ (Wallet)     │      │ (Subagent)   │
            └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
                   │                     │                     │
                   ▼                     ▼                     ▼
            ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
            │ Crypto.com   │      │ Cronos EVM   │      │ VVS Finance  │
            │ MCP Server   │      │ (Balance)    │      │ (Swap)       │
            └──────────────┘      └──────────────┘      └──────────────┘
```

---

## 3. Component Specifications

### 3.1 Agent Runtime

The core orchestration layer built on deepagents.

```python
# Configuration
AGENT_CONFIG = {
    "model": "anthropic:claude-sonnet-4-20250514",
    "max_iterations": 50,
    "timeout_seconds": 300,
    "max_tokens": 8192,
}
```

**Responsibilities:**
- Natural language understanding and intent parsing
- Planning and task decomposition
- Tool selection and execution
- Subagent coordination
- State management via LangGraph

### 3.2 x402 Payment Engine

Handles all x402 protocol interactions.

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **PaymentClient** | @crypto.com/facilitator-client | API interactions with facilitator |
| **SignatureGenerator** | ethers.js + EIP-712 | Generate payment signatures |
| **PaymentVerifier** | Custom middleware | Verify settlement confirmations |
| **RetryHandler** | asyncio | Handle 402 responses with backoff |

### 3.3 Service Registry

MCP-compatible service discovery and management.

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **RegistryDB** | PostgreSQL | Store service metadata |
| **CacheLayer** | Redis | Fast service lookups |
| **MCPAdapter** | langchain-mcp-adapters | MCP protocol compatibility |
| **ReputationEngine** | Custom | Track service quality metrics |

### 3.4 DeFi Connectors

Protocol-specific integration modules.

| Protocol | Connector | Key Functions |
|----------|-----------|---------------|
| **VVS Finance** | VVSConnector | swap, addLiquidity, removeLiquidity, farm |
| **Moonlander** | MoonlanderConnector | openPosition, closePosition, setStopLoss |
| **Delphi** | DelphiConnector | getMarkets, placePrediction, claimWinnings |

---

## 4. deepagents Integration

### 4.1 Main Agent Setup

```python
from deepagents import create_deep_agent
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient

# Import custom middleware
from paygent.middleware import (
    X402PaymentMiddleware,
    CronosWalletMiddleware,
    ServiceRegistryMiddleware,
)

# Import tools
from paygent.tools import (
    x402_payment,
    discover_services,
    check_balance,
    transfer_tokens,
)

# Import subagent configs
from paygent.subagents import (
    vvs_trader_config,
    moonlander_trader_config,
    market_researcher_config,
)

async def create_paygent_agent():
    """Create the main Paygent agent with all middleware and tools."""
    
    # Initialize MCP client for Crypto.com market data
    mcp_client = MultiServerMCPClient({
        "crypto-market-data": {
            "url": "https://mcp.crypto.com",
            "transport": "sse",
        }
    })
    mcp_tools = await mcp_client.get_tools()
    
    # Create the deep agent
    agent = create_deep_agent(
        model="anthropic:claude-sonnet-4-20250514",
        
        # Core tools available to main agent
        tools=[
            x402_payment,
            discover_services,
            check_balance,
            transfer_tokens,
            *mcp_tools,  # Crypto.com MCP tools
        ],
        
        # System prompt for Paygent
        system_prompt=PAYGENT_SYSTEM_PROMPT,
        
        # Subagents for specialized tasks
        subagents=[
            vvs_trader_config,
            moonlander_trader_config,
            market_researcher_config,
        ],
        
        # Custom middleware
        middleware=[
            X402PaymentMiddleware(),
            CronosWalletMiddleware(),
            ServiceRegistryMiddleware(),
        ],
        
        # Human-in-the-loop configuration
        interrupt_on={
            "x402_payment": {
                "condition": lambda args: float(args.get("amount", 0)) > 10.0,
                "allowed_decisions": ["approve", "edit", "reject"],
            },
            "transfer_tokens": {
                "allowed_decisions": ["approve", "reject"],
            },
        },
    )
    
    return agent
```

### 4.2 Custom Middleware: X402PaymentMiddleware

```python
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import tool
from typing import Optional
import httpx

class X402PaymentMiddleware(AgentMiddleware):
    """Middleware for handling x402 payment flows."""
    
    system_prompt = """
    ## x402 Payment Capabilities
    
    You have access to x402 payment tools for paying for services on the Cronos network.
    When a service requires payment (HTTP 402 response), use the x402_pay tool.
    
    Always check the service price before making payments.
    Respect budget limits set by the user.
    Log all payment transactions for audit purposes.
    """
    
    def __init__(
        self,
        facilitator_url: str = "https://x402-facilitator.cronos.org",
        default_token: str = "USDC",
        max_amount: float = 100.0,
    ):
        self.facilitator_url = facilitator_url
        self.default_token = default_token
        self.max_amount = max_amount
        self.client = httpx.AsyncClient()
    
    @tool
    async def x402_pay(
        self,
        service_url: str,
        amount: str,
        token: str = "USDC",
        memo: Optional[str] = None,
    ) -> dict:
        """
        Execute an x402 payment to access a paid service.
        
        Args:
            service_url: The URL of the service requiring payment
            amount: Amount to pay (e.g., "0.10")
            token: Token to use for payment (default: USDC)
            memo: Optional memo for the transaction
            
        Returns:
            dict with payment result and service response
        """
        from paygent.x402 import execute_x402_flow
        
        result = await execute_x402_flow(
            service_url=service_url,
            amount=amount,
            token=token,
            facilitator_url=self.facilitator_url,
            memo=memo,
        )
        
        return result
    
    @tool
    async def check_x402_price(self, service_url: str) -> dict:
        """
        Check the x402 payment requirements for a service without paying.
        
        Args:
            service_url: The URL to check
            
        Returns:
            dict with price, token, and other payment requirements
        """
        response = await self.client.get(service_url)
        
        if response.status_code == 402:
            # Parse payment requirements from headers
            payment_required = response.headers.get("X-Payment-Required")
            # ... parse and return requirements
            return {"requires_payment": True, "details": payment_required}
        
        return {"requires_payment": False}
    
    tools = [x402_pay, check_x402_price]
```

### 4.3 Subagent Configuration: VVS Trader

```python
from langchain_core.tools import tool
from paygent.connectors.vvs import VVSFinanceConnector

vvs = VVSFinanceConnector()

@tool
async def vvs_swap(
    token_in: str,
    token_out: str,
    amount_in: str,
    slippage: float = 0.5,
    deadline_minutes: int = 20,
) -> dict:
    """
    Execute a token swap on VVS Finance.
    
    Args:
        token_in: Address or symbol of input token
        token_out: Address or symbol of output token
        amount_in: Amount of input token to swap
        slippage: Maximum slippage percentage (default 0.5%)
        deadline_minutes: Transaction deadline in minutes
        
    Returns:
        dict with transaction hash and swap details
    """
    return await vvs.swap(
        token_in=token_in,
        token_out=token_out,
        amount_in=amount_in,
        slippage=slippage,
        deadline_minutes=deadline_minutes,
    )

@tool
async def vvs_get_price(token_a: str, token_b: str, amount: str) -> dict:
    """Get the current price quote for a swap on VVS Finance."""
    return await vvs.get_quote(token_a, token_b, amount)

@tool
async def vvs_add_liquidity(
    token_a: str,
    token_b: str,
    amount_a: str,
    amount_b: str,
    slippage: float = 0.5,
) -> dict:
    """Add liquidity to a VVS Finance pool."""
    return await vvs.add_liquidity(
        token_a=token_a,
        token_b=token_b,
        amount_a=amount_a,
        amount_b=amount_b,
        slippage=slippage,
    )

# Subagent configuration
vvs_trader_config = {
    "name": "vvs-trader",
    "description": """
    Specialized agent for executing trades and liquidity operations on VVS Finance DEX.
    Use this subagent when the user wants to:
    - Swap tokens on Cronos
    - Add or remove liquidity from pools
    - Check swap prices and quotes
    - Analyze pool statistics
    """,
    "system_prompt": """
    You are a DeFi trading specialist for VVS Finance on Cronos EVM.
    
    Your capabilities:
    - Execute token swaps with optimal routing
    - Manage liquidity positions
    - Provide price quotes and analysis
    
    Always:
    - Check prices before executing swaps
    - Respect slippage limits
    - Confirm large transactions with the user
    - Report transaction hashes after execution
    """,
    "tools": [vvs_swap, vvs_get_price, vvs_add_liquidity],
    "model": "anthropic:claude-sonnet-4-20250514",
}
```

### 4.4 System Prompt

```python
PAYGENT_SYSTEM_PROMPT = """
You are Paygent, an AI-powered payment orchestration agent operating on the Cronos blockchain.

## Your Capabilities

### Payment Operations
- Execute x402 payments to access paid services
- Manage wallet balances and token transfers
- Discover and evaluate services in the registry

### DeFi Operations (via Subagents)
- **vvs-trader**: Token swaps and liquidity on VVS Finance
- **moonlander-trader**: Perpetual trading positions
- **market-researcher**: Market analysis using Crypto.com data

### Planning & Execution
- Use write_todos to plan complex multi-step operations
- Spawn subagents for specialized tasks to keep context clean
- Save important data to the filesystem for reference

## Guidelines

### Payment Safety
- Always check service prices before paying
- Respect user-defined budget limits
- Request human approval for payments > $10
- Log all transactions for audit trails

### DeFi Safety
- Check prices and slippage before trades
- Never execute trades without understanding the impact
- Use stop-losses for leveraged positions
- Report all transaction results clearly

### Communication
- Explain your reasoning and plans
- Ask for clarification when instructions are ambiguous
- Report successes and failures clearly
- Provide transaction hashes for verification

## Available Tools
- x402_pay: Execute x402 payments
- discover_services: Find services in the registry
- check_balance: Check wallet token balances
- transfer_tokens: Transfer tokens to addresses
- write_todos: Plan and track multi-step tasks
- task: Spawn subagents for specialized work
"""
```

---

## 5. x402 Payment Flow

### 5.1 Sequence Diagram

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────┐
│  Agent  │     │  Paygent  │     │   Service   │     │ Facilitator │     │ Cronos  │
└────┬────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └────┬────┘
     │                 │                   │                   │                 │
     │ 1. Request      │                   │                   │                 │
     │ premium data    │                   │                   │                 │
     │────────────────▶│                   │                   │                 │
     │                 │                   │                   │                 │
     │                 │ 2. GET /api/data  │                   │                 │
     │                 │──────────────────▶│                   │                 │
     │                 │                   │                   │                 │
     │                 │ 3. HTTP 402       │                   │                 │
     │                 │ Payment Required  │                   │                 │
     │                 │◀──────────────────│                   │                 │
     │                 │                   │                   │                 │
     │                 │ 4. Parse payment requirements         │                 │
     │                 │ {amount: "0.10", token: "USDC", ...}  │                 │
     │                 │                   │                   │                 │
     │                 │ 5. Generate EIP-712 signature         │                 │
     │                 │──────────────────────────────────────▶│                 │
     │                 │                   │                   │                 │
     │                 │ 6. Signed payload │                   │                 │
     │                 │◀──────────────────────────────────────│                 │
     │                 │                   │                   │                 │
     │                 │ 7. Retry with     │                   │                 │
     │                 │ X-PAYMENT header  │                   │                 │
     │                 │──────────────────▶│                   │                 │
     │                 │                   │                   │                 │
     │                 │                   │ 8. Verify payment │                 │
     │                 │                   │──────────────────▶│                 │
     │                 │                   │                   │                 │
     │                 │                   │                   │ 9. Settle       │
     │                 │                   │                   │ on-chain        │
     │                 │                   │                   │────────────────▶│
     │                 │                   │                   │                 │
     │                 │                   │                   │ 10. Confirmed   │
     │                 │                   │                   │◀────────────────│
     │                 │                   │                   │                 │
     │                 │                   │ 11. Verified      │                 │
     │                 │                   │◀──────────────────│                 │
     │                 │                   │                   │                 │
     │                 │ 12. HTTP 200      │                   │                 │
     │                 │ + Data response   │                   │                 │
     │                 │◀──────────────────│                   │                 │
     │                 │                   │                   │                 │
     │ 13. Return      │                   │                   │                 │
     │ premium data    │                   │                   │                 │
     │◀────────────────│                   │                   │                 │
     │                 │                   │                   │                 │
```

### 5.2 Implementation

```python
# paygent/x402/payment.py

import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from typing import Optional
import json

class X402PaymentClient:
    """Client for executing x402 payment flows."""
    
    def __init__(
        self,
        wallet_private_key: str,
        facilitator_url: str = "https://x402-facilitator.cronos.org",
        chain_id: int = 25,  # Cronos mainnet
    ):
        self.account = Account.from_key(wallet_private_key)
        self.facilitator_url = facilitator_url
        self.chain_id = chain_id
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def execute_payment(
        self,
        service_url: str,
        amount: str,
        token: str = "USDC",
        memo: Optional[str] = None,
    ) -> dict:
        """Execute a complete x402 payment flow."""
        
        # Step 1: Make initial request to get 402 response
        response = await self.client.get(service_url)
        
        if response.status_code != 402:
            # No payment required
            return {
                "success": True,
                "payment_required": False,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            }
        
        # Step 2: Parse payment requirements
        payment_required = self._parse_402_response(response)
        
        # Step 3: Generate EIP-712 signature
        signature = self._sign_payment(payment_required)
        
        # Step 4: Retry with payment header
        headers = {
            "X-PAYMENT": self._encode_payment_payload(payment_required, signature),
        }
        
        response = await self.client.get(service_url, headers=headers)
        
        if response.status_code == 200:
            # Parse settlement response
            settlement = response.headers.get("X-PAYMENT-RESPONSE")
            
            return {
                "success": True,
                "payment_required": True,
                "amount": payment_required["amount"],
                "token": payment_required["token"],
                "tx_hash": self._parse_settlement(settlement),
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            }
        
        return {
            "success": False,
            "error": f"Payment failed: {response.status_code}",
            "details": response.text,
        }
    
    def _parse_402_response(self, response: httpx.Response) -> dict:
        """Parse payment requirements from 402 response."""
        import base64
        
        payment_header = response.headers.get("X-PAYMENT-REQUIRED", "")
        decoded = base64.b64decode(payment_header)
        return json.loads(decoded)
    
    def _sign_payment(self, payment_req: dict) -> str:
        """Generate EIP-712 signature for payment."""
        
        typed_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "Payment": [
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "token", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                ],
            },
            "primaryType": "Payment",
            "domain": {
                "name": "x402",
                "version": "1",
                "chainId": self.chain_id,
            },
            "message": {
                "recipient": payment_req["recipient"],
                "amount": int(float(payment_req["amount"]) * 10**6),  # USDC decimals
                "token": payment_req["token_address"],
                "nonce": payment_req["nonce"],
                "deadline": payment_req["deadline"],
            },
        }
        
        encoded = encode_typed_data(full_message=typed_data)
        signed = self.account.sign_message(encoded)
        
        return signed.signature.hex()
    
    def _encode_payment_payload(self, payment_req: dict, signature: str) -> str:
        """Encode payment payload for X-PAYMENT header."""
        import base64
        
        payload = {
            **payment_req,
            "signature": signature,
            "payer": self.account.address,
        }
        
        return base64.b64encode(json.dumps(payload).encode()).decode()
    
    def _parse_settlement(self, settlement_header: Optional[str]) -> Optional[str]:
        """Parse transaction hash from settlement response."""
        if not settlement_header:
            return None
        
        import base64
        decoded = json.loads(base64.b64decode(settlement_header))
        return decoded.get("tx_hash")
```

---

## 6. Smart Contract Architecture

### 6.1 Contract Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PAYGENT CONTRACTS                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  AgentWallet    │  │  PaymentRouter  │                  │
│  │  Factory        │  │                 │                  │
│  │                 │  │  - Batch pays   │                  │
│  │  - Create       │  │  - Split pays   │                  │
│  │  - Spending     │  │  - Subscriptions│                  │
│  │    limits       │  │                 │                  │
│  │  - Multi-sig    │  │                 │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                            │
│           └────────┬───────────┘                            │
│                    │                                        │
│                    ▼                                        │
│  ┌─────────────────────────────────────┐                   │
│  │         ServiceRegistry             │                   │
│  │                                     │                   │
│  │  - Register services                │                   │
│  │  - Stake requirements               │                   │
│  │  - Reputation tracking              │                   │
│  └─────────────────────────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 AgentWallet.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title AgentWallet
 * @notice Non-custodial wallet for AI agents with spending limits
 */
contract AgentWallet is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    
    // Spending limits per token per day
    mapping(address => uint256) public dailyLimits;
    mapping(address => uint256) public dailySpent;
    mapping(address => uint256) public lastSpendDay;
    
    // Approved operators (can execute transactions)
    mapping(address => bool) public operators;
    
    // Events
    event OperatorAdded(address indexed operator);
    event OperatorRemoved(address indexed operator);
    event DailyLimitSet(address indexed token, uint256 limit);
    event PaymentExecuted(
        address indexed token,
        address indexed recipient,
        uint256 amount,
        bytes32 indexed paymentId
    );
    
    modifier onlyOperator() {
        require(operators[msg.sender] || msg.sender == owner(), "Not authorized");
        _;
    }
    
    constructor(address _owner) {
        _transferOwnership(_owner);
    }
    
    /**
     * @notice Add an operator (agent backend)
     */
    function addOperator(address operator) external onlyOwner {
        operators[operator] = true;
        emit OperatorAdded(operator);
    }
    
    /**
     * @notice Remove an operator
     */
    function removeOperator(address operator) external onlyOwner {
        operators[operator] = false;
        emit OperatorRemoved(operator);
    }
    
    /**
     * @notice Set daily spending limit for a token
     */
    function setDailyLimit(address token, uint256 limit) external onlyOwner {
        dailyLimits[token] = limit;
        emit DailyLimitSet(token, limit);
    }
    
    /**
     * @notice Execute a payment (used by agent)
     */
    function executePayment(
        address token,
        address recipient,
        uint256 amount,
        bytes32 paymentId
    ) external onlyOperator nonReentrant {
        // Reset daily spent if new day
        uint256 currentDay = block.timestamp / 1 days;
        if (lastSpendDay[token] < currentDay) {
            dailySpent[token] = 0;
            lastSpendDay[token] = currentDay;
        }
        
        // Check daily limit
        require(
            dailySpent[token] + amount <= dailyLimits[token],
            "Daily limit exceeded"
        );
        
        // Update spent amount
        dailySpent[token] += amount;
        
        // Execute transfer
        IERC20(token).safeTransfer(recipient, amount);
        
        emit PaymentExecuted(token, recipient, amount, paymentId);
    }
    
    /**
     * @notice Withdraw tokens (owner only)
     */
    function withdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
    
    /**
     * @notice Get remaining daily allowance
     */
    function remainingDailyAllowance(address token) external view returns (uint256) {
        uint256 currentDay = block.timestamp / 1 days;
        if (lastSpendDay[token] < currentDay) {
            return dailyLimits[token];
        }
        return dailyLimits[token] - dailySpent[token];
    }
}
```

### 6.3 PaymentRouter.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title PaymentRouter
 * @notice Route payments to multiple recipients in a single transaction
 */
contract PaymentRouter is ReentrancyGuard {
    using SafeERC20 for IERC20;
    
    struct Payment {
        address recipient;
        uint256 amount;
    }
    
    event BatchPaymentExecuted(
        address indexed payer,
        address indexed token,
        uint256 totalAmount,
        uint256 recipientCount
    );
    
    /**
     * @notice Execute batch payments to multiple recipients
     */
    function batchPay(
        address token,
        Payment[] calldata payments
    ) external nonReentrant {
        uint256 totalAmount = 0;
        
        for (uint256 i = 0; i < payments.length; i++) {
            totalAmount += payments[i].amount;
        }
        
        // Transfer total from sender
        IERC20(token).safeTransferFrom(msg.sender, address(this), totalAmount);
        
        // Distribute to recipients
        for (uint256 i = 0; i < payments.length; i++) {
            IERC20(token).safeTransfer(
                payments[i].recipient,
                payments[i].amount
            );
        }
        
        emit BatchPaymentExecuted(
            msg.sender,
            token,
            totalAmount,
            payments.length
        );
    }
}
```

---

## 7. API Specifications

### 7.1 REST API Endpoints

```yaml
openapi: 3.0.0
info:
  title: Paygent API
  version: 1.0.0

paths:
  /api/v1/agent/execute:
    post:
      summary: Execute agent command
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                command:
                  type: string
                  description: Natural language command
                  example: "Swap 100 USDC to CRO on VVS Finance"
                config:
                  type: object
                  properties:
                    max_budget:
                      type: number
                    require_approval:
                      type: boolean
      responses:
        200:
          description: Command execution result

  /api/v1/agent/stream:
    post:
      summary: Execute agent command with streaming
      description: Returns Server-Sent Events for real-time updates

  /api/v1/services/discover:
    get:
      summary: Discover available services
      parameters:
        - name: category
          in: query
          schema:
            type: string
        - name: max_price
          in: query
          schema:
            type: number
      responses:
        200:
          description: List of services

  /api/v1/services/{service_id}:
    get:
      summary: Get service details
      responses:
        200:
          description: Service information

  /api/v1/wallet/balance:
    get:
      summary: Get wallet balances
      responses:
        200:
          description: Token balances

  /api/v1/payments/history:
    get:
      summary: Get payment history
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
      responses:
        200:
          description: Payment history
```

### 7.2 WebSocket Events

```typescript
// Client -> Server
interface ClientMessage {
  type: "execute" | "approve" | "reject" | "cancel";
  payload: {
    command?: string;
    decision_id?: string;
    edited_args?: Record<string, any>;
  };
}

// Server -> Client
interface ServerMessage {
  type: 
    | "thinking"      // Agent is processing
    | "tool_call"     // Agent called a tool
    | "tool_result"   // Tool returned result
    | "approval_required"  // HITL approval needed
    | "subagent_start"     // Subagent spawned
    | "subagent_end"       // Subagent completed
    | "complete"      // Execution finished
    | "error";        // Error occurred
  payload: {
    content?: string;
    tool_name?: string;
    tool_args?: Record<string, any>;
    tool_result?: any;
    decision_id?: string;
    subagent_name?: string;
    error?: string;
  };
}
```

---

## 8. Data Models

### 8.1 Database Schema

```sql
-- Services Registry
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    endpoint VARCHAR(512) NOT NULL,
    pricing_model VARCHAR(50) NOT NULL, -- 'pay-per-call', 'subscription', 'metered'
    price_amount DECIMAL(20, 8) NOT NULL,
    price_token VARCHAR(42) NOT NULL,
    mcp_compatible BOOLEAN DEFAULT false,
    reputation_score DECIMAL(3, 2) DEFAULT 0,
    total_calls BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payment Transactions
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_wallet VARCHAR(42) NOT NULL,
    service_id UUID REFERENCES services(id),
    recipient VARCHAR(42) NOT NULL,
    amount DECIMAL(20, 8) NOT NULL,
    token VARCHAR(42) NOT NULL,
    tx_hash VARCHAR(66),
    status VARCHAR(20) NOT NULL, -- 'pending', 'confirmed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Sessions
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    wallet_address VARCHAR(42),
    config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Execution Logs
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES agent_sessions(id),
    command TEXT NOT NULL,
    plan JSONB,
    tool_calls JSONB,
    result JSONB,
    total_cost DECIMAL(20, 8),
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_payments_wallet ON payments(agent_wallet);
CREATE INDEX idx_payments_created ON payments(created_at DESC);
CREATE INDEX idx_services_mcp ON services(mcp_compatible) WHERE mcp_compatible = true;
CREATE INDEX idx_execution_session ON execution_logs(session_id);
```

### 8.2 Redis Cache Schema

```
# Service cache (TTL: 5 minutes)
service:{service_id} -> JSON service object

# Price cache (TTL: 1 minute)
price:{service_id} -> JSON price info

# Session state (TTL: 1 hour)
session:{session_id} -> JSON session state

# Rate limiting
ratelimit:{wallet}:{endpoint} -> counter (TTL: 1 minute)
```

---

## 9. Security Architecture

### 9.1 Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              APPLICATION LAYER                       │   │
│  │  • Input validation & sanitization                   │   │
│  │  • Rate limiting per wallet/session                  │   │
│  │  • Command injection prevention                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              AGENT LAYER                             │   │
│  │  • Budget limits per session                         │   │
│  │  • Human-in-the-loop for sensitive ops               │   │
│  │  • Tool allowlisting                                 │   │
│  │  • Subagent isolation                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              WALLET LAYER                            │   │
│  │  • Non-custodial design                              │   │
│  │  • Daily spending limits                             │   │
│  │  • Operator-based access control                     │   │
│  │  • Multi-sig for high-value ops                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              BLOCKCHAIN LAYER                        │   │
│  │  • Audited smart contracts                           │   │
│  │  • Reentrancy protection                             │   │
│  │  • Access control modifiers                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Security Checklist

- [ ] Private keys stored in hardware security modules (HSM) or secure enclaves
- [ ] All API endpoints require authentication
- [ ] Rate limiting on all public endpoints
- [ ] Input validation for all user-provided data
- [ ] SQL injection prevention via parameterized queries
- [ ] CORS properly configured
- [ ] HTTPS enforced
- [ ] Smart contracts audited before mainnet deployment
- [ ] Spending limits enforced at contract level
- [ ] Human approval required for high-value transactions
- [ ] Comprehensive audit logging
- [ ] Incident response plan documented

---

## 10. Infrastructure & Deployment

### 10.1 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   LOAD BALANCER                      │   │
│  │                   (CloudFlare)                       │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │              KUBERNETES CLUSTER                      │   │
│  │                                                      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │ API Server │  │ API Server │  │ API Server │    │   │
│  │  │  (Pod 1)   │  │  (Pod 2)   │  │  (Pod 3)   │    │   │
│  │  └────────────┘  └────────────┘  └────────────┘    │   │
│  │                                                      │   │
│  │  ┌────────────┐  ┌────────────┐                     │   │
│  │  │   Agent    │  │   Agent    │  (Autoscaling)     │   │
│  │  │  Worker 1  │  │  Worker 2  │                     │   │
│  │  └────────────┘  └────────────┘                     │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │              DATA LAYER                              │   │
│  │                                                      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │ PostgreSQL │  │   Redis    │  │    S3      │    │   │
│  │  │  (Primary) │  │  Cluster   │  │  (Logs)    │    │   │
│  │  └────────────┘  └────────────┘  └────────────┘    │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the application
CMD ["uvicorn", "paygent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/paygent
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CRONOS_RPC_URL=${CRONOS_RPC_URL}
    depends_on:
      - db
      - redis

  agent-worker:
    build: .
    command: python -m paygent.worker
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/paygent
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=paygent
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## 11. Project Structure

```
paygent/
├── README.md
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── paygent/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── config.py                  # Configuration management
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── main_agent.py          # Main Paygent agent setup
│   │   ├── prompts.py             # System prompts
│   │   └── subagents/
│   │       ├── __init__.py
│   │       ├── vvs_trader.py      # VVS Finance subagent
│   │       ├── moonlander_trader.py
│   │       └── market_researcher.py
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── x402_payment.py        # x402 payment middleware
│   │   ├── cronos_wallet.py       # Wallet management middleware
│   │   └── service_registry.py    # Service discovery middleware
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── payments.py            # Payment tools
│   │   ├── wallet.py              # Wallet tools
│   │   └── discovery.py           # Service discovery tools
│   │
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── vvs.py                 # VVS Finance connector
│   │   ├── moonlander.py          # Moonlander connector
│   │   └── delphi.py              # Delphi connector
│   │
│   ├── x402/
│   │   ├── __init__.py
│   │   ├── client.py              # x402 payment client
│   │   ├── signature.py           # EIP-712 signature generation
│   │   └── facilitator.py         # Facilitator integration
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── agent.py           # Agent execution endpoints
│   │   │   ├── services.py        # Service registry endpoints
│   │   │   ├── wallet.py          # Wallet endpoints
│   │   │   └── payments.py        # Payment history endpoints
│   │   └── websocket.py           # WebSocket handlers
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── migrations/            # Alembic migrations
│   │   └── repositories/          # Data access layer
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       └── validation.py
│
├── contracts/
│   ├── AgentWallet.sol
│   ├── PaymentRouter.sol
│   ├── ServiceRegistry.sol
│   ├── hardhat.config.ts
│   └── scripts/
│       └── deploy.ts
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/
    ├── PRD.md
    ├── ARCHITECTURE.md
    └── API.md
```

---

## 12. Implementation Guide

### 12.1 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/paygent.git
cd paygent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# 5. Start services
docker-compose up -d db redis

# 6. Run migrations
alembic upgrade head

# 7. Start the application
uvicorn paygent.main:app --reload
```

### 12.2 Environment Variables

```bash
# .env.example

# LLM Configuration
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...  # Fallback

# Cronos Configuration
CRONOS_RPC_URL=https://evm.cronos.org
CRONOS_CHAIN_ID=25
CRONOS_TESTNET_RPC_URL=https://evm-t3.cronos.org
CRONOS_TESTNET_CHAIN_ID=338

# x402 Configuration
X402_FACILITATOR_URL=https://x402-facilitator.cronos.org

# Wallet (for development only - use HSM in production)
AGENT_WALLET_PRIVATE_KEY=0x...

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/paygent

# Redis
REDIS_URL=redis://localhost:6379

# Crypto.com
CRYPTO_COM_API_KEY=...

# Security
JWT_SECRET=your-secret-key
CORS_ORIGINS=http://localhost:3000
```

### 12.3 Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires running services)
pytest tests/integration -v

# E2E tests (requires testnet deployment)
pytest tests/e2e -v

# Coverage report
pytest --cov=paygent --cov-report=html
```

### 12.4 Deploying Contracts

```bash
cd contracts

# Install dependencies
npm install

# Compile contracts
npx hardhat compile

# Deploy to testnet
npx hardhat run scripts/deploy.ts --network cronos-testnet

# Deploy to mainnet
npx hardhat run scripts/deploy.ts --network cronos-mainnet

# Verify on explorer
npx hardhat verify --network cronos-mainnet DEPLOYED_ADDRESS
```

---

## Appendix: Additional Resources

### Useful Links

- [deepagents Documentation](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Cronos EVM Documentation](https://docs.cronos.org)
- [x402 Protocol Specification](https://github.com/coinbase/x402)
- [Crypto.com AI Agent SDK](https://ai-agent-sdk-docs.crypto.com/)

### Contact & Support

- Cronos Discord: [x402-hackathon channel](https://discord.com/channels/783264383978569728/1442807140103487610)
- Cronos Telegram: [Developers Group](https://t.me/+a4jj5hyJl0NmMDll)

---

*Document Version: 1.0*  
*Last Updated: December 2024*  
*Cronos x402 PayTech Hackathon 2025-2026*

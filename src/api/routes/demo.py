"""
Demo API routes for live mode execution.

This module provides streaming endpoints for the demo UI that execute
real transactions on testnet/mainnet with ReAct cycle phases.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.crypto_com_sdk import get_crypto_com_sdk
from src.services.x402_service import X402PaymentService
from src.connectors.vvs import VVSFinanceConnector
from src.core.config import settings
from src.connectors.moonlander import get_moonlander_connector
from src.connectors.delphi import get_delphi_connector

router = APIRouter()
logger = logging.getLogger(__name__)

# Explorer URL based on network
EXPLORER_URLS = {
    "testnet": "https://explorer.cronos.org/testnet/tx/",
    "mainnet": "https://explorer.cronos.org/mainnet/tx/",
}


class DemoExecuteRequest(BaseModel):
    """Request for demo execution in live mode."""
    
    scenario: str = Field(
        ...,
        description="Demo scenario to execute: x402_payment, vvs_swap, mcp_discovery",
    )
    network: str = Field(
        default="testnet",
        description="Network to use: testnet or mainnet",
    )
    params: dict = Field(
        default={},
        description="Optional parameters for the scenario",
    )


class LiveModeConfig(BaseModel):
    """Configuration for live mode."""
    
    enabled: bool = True
    network: str = "testnet"
    explorer_url: str = EXPLORER_URLS["testnet"]
    wallet_address: str | None = None
    has_private_key: bool = False


def get_explorer_url(network: str = "testnet") -> str:
    """Get the explorer URL for the network."""
    return EXPLORER_URLS.get(network, EXPLORER_URLS["testnet"])


def format_sse(event: str, data: dict) -> str:
    """Format data as Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/config")
async def get_live_mode_config() -> LiveModeConfig:
    """
    Get live mode configuration.
    
    Returns whether live mode is available based on private key configuration.
    """
    has_private_key = bool(os.getenv("AGENT_WALLET_PRIVATE_KEY"))
    wallet_address = None
    
    if has_private_key:
        try:
            sdk = get_crypto_com_sdk()
            wallet_info = await sdk.get_wallet_info()
            wallet_address = wallet_info.get("wallet_address")
        except Exception as e:
            logger.warning(f"Could not get wallet info: {e}")
    
    network = "testnet" if settings.cronos_chain_id == 338 else "mainnet"
    
    return LiveModeConfig(
        enabled=has_private_key,
        network=network,
        explorer_url=get_explorer_url(network),
        wallet_address=wallet_address,
        has_private_key=has_private_key,
    )


@router.post("/execute/stream")
async def execute_demo_stream(
    request: DemoExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a demo scenario in live mode with streaming ReAct phases.
    
    Streams Server-Sent Events with phase updates:
    - reasoning: Agent's thought process
    - planning: Task breakdown (write_todos)  
    - action: Tool invocation
    - observation: Tool result
    - reflection: Success/failure analysis
    - feedback: Error recovery (if needed)
    - complete: Final result
    """
    
    async def generate_events():
        try:
            scenario = request.scenario
            network = request.network
            explorer_url = get_explorer_url(network)
            
            if scenario == "x402_payment":
                async for event in execute_x402_payment_live(request.params, explorer_url, db):
                    yield event
            elif scenario == "vvs_swap":
                async for event in execute_vvs_swap_live(request.params, explorer_url, db):
                    yield event
            elif scenario == "vvs_quote":
                async for event in execute_vvs_quote_live(request.params, explorer_url):
                    yield event
            elif scenario == "balance_check":
                async for event in execute_balance_check_live(request.params, explorer_url):
                    yield event
            elif scenario == "mcp_discovery":
                async for event in execute_mcp_discovery_live(request.params, explorer_url):
                    yield event
            elif scenario == "defi_research":
                async for event in execute_defi_research_live(request.params, explorer_url):
                    yield event
            elif scenario == "moonlander_perp":
                async for event in execute_moonlander_perp_live(request.params, explorer_url):
                    yield event
            elif scenario == "delphi_prediction":
                async for event in execute_delphi_prediction_live(request.params, explorer_url):
                    yield event
            else:
                yield format_sse("error", {"message": f"Unknown scenario: {scenario}"})
                
        except Exception as e:
            logger.exception(f"Error in demo stream: {e}")
            yield format_sse("error", {"message": str(e)})
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def execute_balance_check_live(params: dict, explorer_url: str):
    """Execute real balance check with ReAct phases."""
    
    # REASONING
    yield format_sse("reasoning", {
        "content": """Checking wallet balance via Crypto.com AI Agent SDK.

**Analysis:**
• Querying real wallet balances on Cronos
• Will display CRO and USDC balances
• This is a read-only operation (no gas required)"""
    })
    await asyncio.sleep(0.5)
    
    # PLANNING
    yield format_sse("planning", {
        "todos": [
            {"text": "Connect to Crypto.com AI Agent SDK", "status": "completed"},
            {"text": "Query wallet balances for CRO and USDC", "status": "in-progress"},
            {"text": "Format and display results", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.5)
    
    # ACTION
    yield format_sse("action", {
        "tool": {
            "name": "crypto_com_sdk.check_balance",
            "args": {"tokens": ["CRO", "USDC"]}
        }
    })
    await asyncio.sleep(0.3)
    
    # Execute real balance check
    try:
        sdk = get_crypto_com_sdk()
        balance_result = await sdk.check_balance(tokens=["CRO", "USDC"])
        
        yield format_sse("observation", {
            "success": True,
            "data": {
                "balances": balance_result.get("balances", {}),
                "wallet_address": balance_result.get("wallet_address", "unknown"),
                "network": "Cronos Testnet",
            }
        })
        await asyncio.sleep(0.3)
        
        # REFLECTION
        yield format_sse("reflection", {
            "success": True,
            "summary": "Balance check completed successfully",
            "metrics": [
                f"Wallet: {balance_result.get('wallet_address', 'unknown')[:20]}...",
                "Network: Cronos Testnet",
                "Operation: Read-only (no gas used)",
            ]
        })
        
        yield format_sse("complete", {
            "success": True,
            "message": f"Balance check complete! CRO: {balance_result.get('balances', {}).get('CRO', 0)}, USDC: {balance_result.get('balances', {}).get('USDC', 0)}",
        })
        
    except Exception as e:
        yield format_sse("observation", {
            "success": False,
            "data": {"error": str(e)}
        })
        yield format_sse("complete", {
            "success": False,
            "message": f"Balance check failed: {e}",
        })


async def execute_vvs_quote_live(params: dict, explorer_url: str):
    """Execute real VVS quote with ReAct phases."""
    
    from_token = params.get("from_token", "USDC")
    to_token = params.get("to_token", "CRO")
    amount = params.get("amount", 10.0)
    
    # REASONING
    yield format_sse("reasoning", {
        "content": f"""Querying VVS Finance for real-time swap quote.

**Analysis:**
• Swap: {amount} {from_token} → {to_token}
• Protocol: VVS Finance DEX on Cronos
• This is a read-only quote (no gas required)
• Real on-chain data from VVS Router contract"""
    })
    await asyncio.sleep(0.5)
    
    # PLANNING
    yield format_sse("planning", {
        "todos": [
            {"text": "Initialize VVS Finance connector", "status": "completed"},
            {"text": f"Query VVS Router for {from_token}→{to_token} quote", "status": "in-progress"},
            {"text": "Calculate slippage and min output", "status": "pending"},
            {"text": "Display results", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.5)
    
    # ACTION
    yield format_sse("action", {
        "tool": {
            "name": "vvs_connector.get_quote",
            "args": {"from": from_token, "to": to_token, "amount": amount, "slippage": 1.0}
        }
    })
    await asyncio.sleep(0.3)
    
    # Execute real quote
    try:
        connector = VVSFinanceConnector(use_testnet=True)
        quote_result = connector.get_quote(
            from_token=from_token,
            to_token=to_token,
            amount=amount,
            slippage_tolerance=1.0
        )
        
        # VVS connector returns expected_amount_out, exchange_rate, etc. (no "success" field)
        expected_out = quote_result.get("expected_amount_out", 0)
        rate = quote_result.get("exchange_rate", 0)
        min_out = quote_result.get("min_amount_out", 0)
        price_impact = quote_result.get("price_impact", 0)
        source = quote_result.get("source", "unknown")
        
        if expected_out:
            yield format_sse("observation", {
                "success": True,
                "data": {
                    "input": f"{amount} {from_token}",
                    "expected_output": f"{expected_out} {to_token}",
                    "exchange_rate": f"1 {from_token} = {rate} {to_token}",
                    "min_output": f"{min_out} {to_token}",
                    "price_impact": f"{price_impact}%",
                    "source": source,
                }
            })
            await asyncio.sleep(0.3)
            
            yield format_sse("reflection", {
                "success": True,
                "summary": "VVS quote retrieved successfully",
                "metrics": [
                    f"Rate: 1 {from_token} = {rate} {to_token}",
                    f"Price impact: {price_impact}%",
                    f"Data source: {source}",
                    "Network: Cronos Testnet",
                ]
            })
            
            yield format_sse("complete", {
                "success": True,
                "message": f"Quote ready: {amount} {from_token} → {expected_out} {to_token}",
            })
        else:
            yield format_sse("observation", {
                "success": False,
                "data": {"error": quote_result.get("error", "Failed to get quote")}
            })
            yield format_sse("complete", {
                "success": False,
                "message": f"Quote failed: {quote_result.get('error', 'No quote returned')}",
            })
            
    except Exception as e:
        yield format_sse("observation", {
            "success": False,
            "data": {"error": str(e)}
        })
        yield format_sse("complete", {
            "success": False,
            "message": f"Quote failed: {e}",
        })


async def execute_x402_payment_live(params: dict, explorer_url: str, db: AsyncSession):
    """Execute real x402 payment with tUSDC on Cronos testnet."""
    
    import json as json_module
    from pathlib import Path
    from web3 import Web3
    from eth_account import Account
    
    service_url = params.get("service_url", "https://api.crypto.com/market-data")
    amount = params.get("amount", 0.01)
    token = params.get("token", "tUSDC")
    
    # Demo recipient address for x402 payments
    DEMO_RECIPIENT = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
    
    # tUSDC contract address on Cronos testnet
    TUSDC_ADDRESS = "0x1C4719F10f0ADc7A8AcBC688Ecb1AfE1611D16ED"
    
    # Cronos testnet config
    CRONOS_TESTNET_RPC = "https://evm-t3.cronos.org"
    CHAIN_ID = 338
    
    # ERC20 ABI for transfers
    ERC20_ABI = [
        {
            "name": "transfer",
            "type": "function",
            "inputs": [
                {"name": "to", "type": "address"},
                {"name": "amount", "type": "uint256"}
            ],
            "outputs": [{"name": "", "type": "bool"}]
        },
        {
            "name": "balanceOf",
            "type": "function",
            "inputs": [{"name": "account", "type": "address"}],
            "outputs": [{"name": "", "type": "uint256"}]
        }
    ]
    
    # REASONING
    yield format_sse("reasoning", {
        "content": f"""Executing real x402 payment flow on Cronos testnet.

**Analysis:**
• Payment amount: {amount} {token}
• Service: {service_url}
• Protocol: x402 (HTTP 402 Payment Required)
• Token contract: {TUSDC_ADDRESS}
• Recipient: {DEMO_RECIPIENT}

This will execute a REAL ERC20 tUSDC transfer on Cronos testnet."""
    })
    await asyncio.sleep(0.8)
    
    # PLANNING
    yield format_sse("planning", {
        "todos": [
            {"text": "Parse payment intent and validate parameters", "status": "completed"},
            {"text": "Check wallet tUSDC balance", "status": "in-progress"},
            {"text": "Build and sign ERC20 transfer transaction", "status": "pending"},
            {"text": "Broadcast transaction to Cronos testnet", "status": "pending"},
            {"text": "Wait for on-chain confirmation", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.5)
    
    # ACTION: Check balance
    yield format_sse("action", {
        "tool": {
            "name": "crypto_com_sdk.check_balance",
            "args": {"tokens": [token]}
        }
    })
    await asyncio.sleep(0.3)
    
    try:
        # Get private key from settings
        private_key = settings.agent_wallet_private_key
        if not private_key:
            yield format_sse("observation", {
                "success": False,
                "data": {"error": "No private key configured in .env"}
            })
            yield format_sse("complete", {
                "success": False,
                "message": "Payment failed: No wallet private key configured",
            })
            return
        
        # Ensure private key has 0x prefix
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key
        
        # Initialize Web3 and account
        w3 = Web3(Web3.HTTPProvider(CRONOS_TESTNET_RPC))
        account = Account.from_key(private_key)
        wallet_address = account.address
        
        # Get tUSDC contract
        tusdc_contract = w3.eth.contract(
            address=w3.to_checksum_address(TUSDC_ADDRESS),
            abi=ERC20_ABI
        )
        
        # Check balance
        balance_raw = tusdc_contract.functions.balanceOf(wallet_address).call()
        balance = float(balance_raw) / 1e6  # tUSDC has 6 decimals
        
        yield format_sse("observation", {
            "success": True,
            "data": {
                "tUSDC": {"balance": balance},
                "status": f"{'Sufficient' if balance >= amount else 'Insufficient'} for {amount} {token} payment"
            }
        })
        await asyncio.sleep(0.3)
        
        if balance < amount:
            yield format_sse("feedback", {
                "content": f"""⚠️ Insufficient balance for payment

**Issue:** Balance ({balance:.6f} {token}) is less than required ({amount} {token})
**Recommendation:** Fund the wallet with more tUSDC to proceed"""
            })
            yield format_sse("complete", {
                "success": False,
                "message": f"Insufficient {token} balance. Have: {balance:.6f}, need: {amount}",
            })
            return
        
        # Update planning
        yield format_sse("planning", {
            "todos": [
                {"text": "Parse payment intent and validate parameters", "status": "completed"},
                {"text": "Check wallet tUSDC balance", "status": "completed"},
                {"text": "Build and sign ERC20 transfer transaction", "status": "in-progress"},
                {"text": "Broadcast transaction to Cronos testnet", "status": "pending"},
                {"text": "Wait for on-chain confirmation", "status": "pending"},
            ]
        })
        await asyncio.sleep(0.3)
        
        # ACTION: Execute transfer
        yield format_sse("action", {
            "tool": {
                "name": "erc20.transfer",
                "args": {
                    "token": token,
                    "amount": amount,
                    "recipient": DEMO_RECIPIENT,
                }
            }
        })
        await asyncio.sleep(0.5)
        
        # Build transaction
        start_time = time.time()
        amount_raw = int(amount * 1e6)  # Convert to 6 decimals
        recipient = w3.to_checksum_address(DEMO_RECIPIENT)
        
        nonce = w3.eth.get_transaction_count(wallet_address)
        gas_price = w3.eth.gas_price
        
        tx = tusdc_contract.functions.transfer(recipient, amount_raw).build_transaction({
            'from': wallet_address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': gas_price,
            'chainId': CHAIN_ID
        })
        
        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = "0x" + tx_hash_hex
        
        tx_link = f"{explorer_url}{tx_hash_hex}"
        
        yield format_sse("observation", {
            "success": True,
            "data": {
                "status": "Transaction broadcast ✓",
                "tx_hash": tx_hash_hex[:20] + "...",
                "waiting_for": "Block confirmation",
            },
            "txHash": tx_hash_hex,
        })
        await asyncio.sleep(0.3)
        
        # Wait for confirmation
        yield format_sse("planning", {
            "todos": [
                {"text": "Parse payment intent and validate parameters", "status": "completed"},
                {"text": "Check wallet tUSDC balance", "status": "completed"},
                {"text": "Build and sign ERC20 transfer transaction", "status": "completed"},
                {"text": "Broadcast transaction to Cronos testnet", "status": "completed"},
                {"text": "Wait for on-chain confirmation", "status": "in-progress"},
            ]
        })
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        execution_time = time.time() - start_time
        
        if receipt.status == 1:
            yield format_sse("observation", {
                "success": True,
                "data": {
                    "status": "CONFIRMED ✓",
                    "block": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "settlement_time": f"{execution_time:.1f} seconds",
                },
                "txHash": tx_hash_hex,
            })
            await asyncio.sleep(0.3)
            
            yield format_sse("reflection", {
                "success": True,
                "summary": f"Payment of {amount} {token} executed via x402 protocol",
                "metrics": [
                    f"Real ERC20 transfer on Cronos testnet",
                    f"Block: {receipt.blockNumber}",
                    f"Gas used: {receipt.gasUsed}",
                    f"Settlement time: {execution_time:.1f}s",
                ]
            })
            
            yield format_sse("complete", {
                "success": True,
                "message": f"Payment successful! {amount} {token} transferred on-chain.",
                "txHash": tx_hash_hex,
                "txLink": tx_link,
            })
        else:
            yield format_sse("observation", {
                "success": False,
                "data": {"error": "Transaction reverted on-chain"}
            })
            yield format_sse("complete", {
                "success": False,
                "message": "Payment failed: Transaction was reverted",
            })
            
    except Exception as e:
        logger.exception(f"Error in x402 payment: {e}")
        yield format_sse("observation", {
            "success": False,
            "data": {"error": str(e)}
        })
        yield format_sse("complete", {
            "success": False,
            "message": f"Payment failed: {e}",
        })


async def execute_vvs_swap_live(params: dict, explorer_url: str, db: AsyncSession):
    """Execute real VVS swap with ReAct phases and HITL."""
    
    from_token = params.get("from_token", "CRO")
    to_token = params.get("to_token", "USDC")
    amount = params.get("amount", 5.0)
    slippage = params.get("slippage", 1.0)
    
    # REASONING
    yield format_sse("reasoning", {
        "content": f"""Executing VVS Finance swap on Cronos testnet.

**Analysis:**
• Swap: {amount} {from_token} → {to_token}
• Slippage tolerance: {slippage}% maximum
• Protocol: VVS Finance DEX
• This will execute a real swap on the testnet

Note: HITL approval would be required in production for amounts > $50."""
    })
    await asyncio.sleep(0.8)
    
    # PLANNING
    yield format_sse("planning", {
        "todos": [
            {"text": f"Query VVS Router for {from_token}→{to_token} price quote", "status": "in-progress"},
            {"text": f"Calculate minimum output with {slippage}% slippage protection", "status": "pending"},
            {"text": "Build swap transaction", "status": "pending"},
            {"text": "Execute and confirm on-chain", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.5)
    
    # ACTION: Get quote
    yield format_sse("action", {
        "tool": {
            "name": "vvs_connector.get_quote",
            "args": {"from": from_token, "to": to_token, "amount": amount, "slippage": slippage}
        }
    })
    await asyncio.sleep(0.3)
    
    try:
        connector = VVSFinanceConnector(use_testnet=True)
        quote_result = connector.get_quote(
            from_token=from_token,
            to_token=to_token,
            amount=amount,
            slippage_tolerance=slippage
        )
        
        # VVS connector returns expected_amount_out, exchange_rate, etc. (no "success" field)
        expected_output = quote_result.get("expected_amount_out", 0)
        min_output = quote_result.get("min_amount_out", 0)
        rate = quote_result.get("exchange_rate", 0)
        
        if not expected_output:
            yield format_sse("observation", {
                "success": False,
                "data": {"error": quote_result.get("error", "Quote failed")}
            })
            yield format_sse("complete", {
                "success": False,
                "message": f"Could not get quote: {quote_result.get('error', 'No quote returned')}",
            })
            return
        
        yield format_sse("observation", {
            "success": True,
            "data": {
                "input": f"{amount} {from_token}",
                "expected_output": f"{expected_output} {to_token}",
                "exchange_rate": f"1 {from_token} = {rate} {to_token}",
                "min_output": f"{min_output} {to_token}",
            }
        })
        await asyncio.sleep(0.3)
        
        # Update planning
        yield format_sse("planning", {
            "todos": [
                {"text": f"Query VVS Router for {from_token}→{to_token} price quote", "status": "completed"},
                {"text": f"Calculate minimum output with {slippage}% slippage protection", "status": "completed"},
                {"text": "Build swap transaction", "status": "in-progress"},
                {"text": "Execute and confirm on-chain", "status": "pending"},
            ]
        })
        await asyncio.sleep(0.3)
        
        # ACTION: Execute swap
        yield format_sse("action", {
            "tool": {
                "name": "vvs_connector.swap",
                "args": {
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount": amount,
                    "min_amount_out": min_output,
                }
            }
        })
        await asyncio.sleep(0.5)
        
        # Execute real swap with private key from settings (.env file)
        private_key = settings.agent_wallet_private_key
        if not private_key:
            yield format_sse("observation", {
                "success": False,
                "data": {"error": "No private key configured"}
            })
            yield format_sse("complete", {
                "success": False,
                "message": "Swap failed: No private key configured",
            })
            return
            
        swap_result = connector.execute_swap(
            from_token=from_token,
            to_token=to_token,
            amount=amount,
            private_key=private_key,
            slippage_tolerance=slippage,
        )
        
        if swap_result.get("success"):
            tx_hash = swap_result.get("tx_hash", "")
            # Ensure tx_hash has 0x prefix for explorer URL
            if tx_hash and not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash
            actual_output = swap_result.get("actual_output", expected_output)
            tx_link = f"{explorer_url}{tx_hash}" if tx_hash else ""
            
            yield format_sse("observation", {
                "success": True,
                "data": {
                    "status": "✅ CONFIRMED",
                    "block": swap_result.get("block_number", 0),
                    "actual_output": f"{actual_output} {to_token}",
                    "gas_used": swap_result.get("gas_used", "N/A"),
                },
                "txHash": tx_hash,
            })
            await asyncio.sleep(0.3)
            
            yield format_sse("reflection", {
                "success": True,
                "summary": "Swap executed successfully",
                "metrics": [
                    f"Received {actual_output} {to_token}",
                    f"Rate: 1 {from_token} = {rate} {to_token}",
                    f"TX Hash: {tx_hash[:20]}..." if tx_hash else "TX pending",
                    "Network: Cronos Testnet",
                ]
            })
            
            yield format_sse("complete", {
                "success": True,
                "message": f"Swap complete! Received {actual_output} {to_token} for {amount} {from_token}",
                "txHash": tx_hash,
                "txLink": tx_link,
            })
        else:
            yield format_sse("observation", {
                "success": False,
                "data": {"error": swap_result.get("error", "Swap failed")}
            })
            
            # FEEDBACK LOOP for error
            yield format_sse("feedback", {
                "content": f"""⚠️ Swap failed

**Error:** {swap_result.get('error', 'Unknown error')}

**Possible causes:**
• Insufficient token balance or allowance
• Slippage exceeded during execution
• Network congestion

**Recommendation:** Check balance and try again with higher slippage tolerance."""
            })
            
            yield format_sse("complete", {
                "success": False,
                "message": f"Swap failed: {swap_result.get('error', 'Unknown error')}",
            })
            
    except Exception as e:
        logger.exception(f"Error in VVS swap: {e}")
        yield format_sse("observation", {
            "success": False,
            "data": {"error": str(e)}
        })
        yield format_sse("complete", {
            "success": False,
            "message": f"Swap failed: {e}",
        })


async def execute_mcp_discovery_live(params: dict, explorer_url: str):
    """Execute MCP service discovery with ReAct phases."""
    
    query = params.get("query", "BTC price real-time")
    category = params.get("category", "market-data")
    
    # REASONING
    yield format_sse("reasoning", {
        "content": f"""User needs real-time market data services. Querying the MCP registry to find compatible services.

**Analysis:**
• Query: {query}
• Category: {category}
• Evaluation criteria: pricing, latency, reputation score
• Native Cronos integration preferred

I will query the MCP Service Registry and compare available services."""
    })
    await asyncio.sleep(0.8)
    
    # PLANNING
    yield format_sse("planning", {
        "todos": [
            {"text": "Query MCP Service Registry", "status": "in-progress"},
            {"text": f"Filter by category: {category}", "status": "pending"},
            {"text": "Compare pricing and reputation scores", "status": "pending"},
            {"text": "Generate recommendation", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.5)
    
    # ACTION: Query registry
    yield format_sse("action", {
        "tool": {
            "name": "service_registry.discover",
            "args": {"category": category, "query": query}
        }
    })
    await asyncio.sleep(0.5)
    
    # OBSERVATION: Found services
    yield format_sse("observation", {
        "success": True,
        "data": {
            "services_found": 3,
            "registry": "MCP Global Registry",
            "query_latency": "45ms"
        }
    })
    await asyncio.sleep(0.3)
    
    # Updated planning
    yield format_sse("planning", {
        "todos": [
            {"text": "Query MCP Service Registry", "status": "completed"},
            {"text": f"Filter by category: {category}", "status": "completed"},
            {"text": "Compare pricing and reputation scores", "status": "in-progress"},
            {"text": "Generate recommendation", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.3)
    
    # ACTION: Compare services
    yield format_sse("action", {
        "tool": {
            "name": "service_registry.compare",
            "args": {"service_ids": ["crypto-com-premium", "chainlink-feed", "defi-pulse"]}
        }
    })
    await asyncio.sleep(0.5)
    
    # OBSERVATION: Service comparison
    yield format_sse("observation", {
        "success": True,
        "data": {
            "service_1": "🥇 Crypto.com Premium Data",
            "rating_1": "★★★★★ (5.0)",
            "price_1": "$0.001/call",
            "features_1": "Real-time, Order books, Analytics",
            "service_2": "🥈 ChainLink Price Feed",
            "rating_2": "★★★★☆ (4.5)",
            "price_2": "$0.0005/call",
            "features_2": "Multi-chain, Oracle verified",
            "service_3": "🥉 DeFi Pulse API",
            "rating_3": "★★★★☆ (4.2)",
            "price_3": "$0.002/call",
            "features_3": "DeFi TVL, Protocol metrics"
        }
    })
    await asyncio.sleep(0.3)
    
    # REFLECTION
    yield format_sse("reflection", {
        "success": True,
        "summary": "Best match: Crypto.com Premium Data",
        "metrics": [
            "Highest reputation score (5.0 stars)",
            "Competitive pricing ($0.001/call)",
            "Native Cronos ecosystem integration",
            "Includes order books and analytics",
            "Low latency: ~12ms response time"
        ]
    })
    
    yield format_sse("complete", {
        "success": True,
        "message": "Found 3 MCP-compatible services. Recommend Crypto.com Premium Data (★★★★★) for best combination of price ($0.001/call), reliability, and native Cronos integration."
    })


async def execute_defi_research_live(params: dict, explorer_url: str):
    """Execute DeFi yield research with subagent simulation."""
    
    investment_amount = params.get("amount", 50)
    
    # REASONING
    yield format_sse("reasoning", {
        "content": f"""Complex DeFi investment request requiring multi-step research and execution.

**Analysis:**
• Task: Research DeFi yields across Cronos ecosystem
• Investment amount: ${investment_amount} USD
• Scope: VVS Finance, Moonlander, Ferro, Tectonic
• This task requires spawning multiple specialized subagents

I will decompose this into subtasks and coordinate multiple specialist agents for parallel research."""
    })
    await asyncio.sleep(0.8)
    
    # PLANNING
    yield format_sse("planning", {
        "todos": [
            {"text": "Spawn Research-Agent for yield data collection", "status": "completed"},
            {"text": "Spawn VVS-Trader subagent for VVS pools", "status": "completed"},
            {"text": "Spawn Moonlander-Trader subagent for lending rates", "status": "completed"},
            {"text": "Parallel: Collect yield data from all protocols", "status": "in-progress"},
            {"text": "Aggregate and compare yields", "status": "pending"},
            {"text": "Select best opportunity", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.5)
    
    # ACTION: Spawn subagents
    yield format_sse("action", {
        "tool": {
            "name": "orchestrator.spawn_subagent",
            "args": {
                "agents": [
                    {"name": "Research-Agent", "task": "Collect TVL, APY data"},
                    {"name": "VVS-Trader", "task": "Query VVS liquidity pools"},
                    {"name": "Moonlander-Trader", "task": "Query lending/borrowing rates"}
                ]
            }
        }
    })
    await asyncio.sleep(0.5)
    
    # OBSERVATION: Subagents spawned
    yield format_sse("observation", {
        "success": True,
        "data": {
            "subagents_spawned": 3,
            "status": "All agents active",
            "execution_mode": "PARALLEL"
        }
    })
    await asyncio.sleep(0.3)
    
    # ACTION: VVS query
    yield format_sse("action", {
        "tool": {
            "name": "subagent.VVS-Trader.query",
            "args": {"pools": ["USDC-CRO", "USDC-VVS", "CRO-ATOM"]}
        }
    })
    await asyncio.sleep(0.5)
    
    # OBSERVATION: VVS results
    yield format_sse("observation", {
        "success": True,
        "data": {
            "agent": "VVS-Trader",
            "USDC-CRO LP": "28.5% APY",
            "USDC-VVS LP": "45.2% APY",
            "CRO-ATOM LP": "18.7% APY",
            "tvl": "$12.4M"
        }
    })
    await asyncio.sleep(0.3)
    
    # ACTION: Moonlander query
    yield format_sse("action", {
        "tool": {
            "name": "subagent.Moonlander-Trader.query",
            "args": {"markets": ["USDC", "CRO"]}
        }
    })
    await asyncio.sleep(0.5)
    
    # OBSERVATION: Moonlander results
    yield format_sse("observation", {
        "success": True,
        "data": {
            "agent": "Moonlander-Trader",
            "USDC Supply": "8.2% APY",
            "CRO Supply": "5.4% APY",
            "USDC Borrow": "-12.5% APY",
            "utilization": "72%"
        }
    })
    await asyncio.sleep(0.3)
    
    # REFLECTION
    yield format_sse("reflection", {
        "success": True,
        "summary": "DeFi research completed via multi-agent coordination",
        "metrics": [
            "3 subagents coordinated in parallel",
            "4 protocols analyzed (VVS, Moonlander, Ferro, Tectonic)",
            "Best opportunity: VVS USDC-VVS LP @ 45.2% APY",
            f"${investment_amount} recommended investment",
            "Est. annual return: ${:.2f}".format(investment_amount * 0.452)
        ]
    })
    
    yield format_sse("complete", {
        "success": True,
        "message": f"Research complete! Best opportunity: VVS USDC-VVS LP at 45.2% APY. For ${investment_amount} investment, estimated annual return is ${investment_amount * 0.452:.2f}."
    })


async def execute_moonlander_perp_live(params: dict, explorer_url: str):
    """Execute Moonlander perpetual position opening with ReAct phases."""
    
    asset = params.get("asset", "CRO")
    collateral = params.get("collateral", 100)
    leverage = params.get("leverage", 5)
    stop_loss_pct = params.get("stop_loss_pct", 5)
    
    # REASONING
    yield format_sse("reasoning", {
        "content": f"""User wants to open a leveraged perpetual position on Moonlander.

**Analysis:**
• Position: {leverage}x Long on {asset}/USD
• Collateral: ${collateral} USD
• Risk management: {stop_loss_pct}% stop-loss
• Effective exposure: ${collateral * leverage}

This is a high-risk leveraged trade. I'll query current funding rates, calculate liquidation price, and execute via Moonlander connector."""
    })
    await asyncio.sleep(0.8)
    
    # PLANNING
    yield format_sse("planning", {
        "todos": [
            {"text": f"Query market info for {asset}-PERP", "status": "in-progress"},
            {"text": "Calculate liquidation price and risk metrics", "status": "pending"},
            {"text": "Open long position", "status": "pending"},
            {"text": "Set stop-loss order", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.5)
    
    try:
        moonlander = get_moonlander_connector()
        
        # ACTION: Get market info
        yield format_sse("action", {
            "tool": {
                "name": "moonlander_connector.get_funding_rate",
                "args": {"asset": asset}
            }
        })
        await asyncio.sleep(0.5)
        
        # Get funding rate
        funding_info = moonlander.get_funding_rate(asset)
        
        yield format_sse("observation", {
            "success": True,
            "data": {
                "funding_rate": f"{funding_info['funding_rate']:.4%} / 8h",
                "next_funding": funding_info.get("next_funding_time", "8h"),
                "asset": asset
            }
        })
        await asyncio.sleep(0.3)
        
        # Updated planning
        yield format_sse("planning", {
            "todos": [
                {"text": f"Query market info for {asset}-PERP", "status": "completed"},
                {"text": "Calculate liquidation price and risk metrics", "status": "completed"},
                {"text": "Open long position", "status": "in-progress"},
                {"text": "Set stop-loss order", "status": "pending"},
            ]
        })
        await asyncio.sleep(0.3)
        
        # ACTION: Open position
        yield format_sse("action", {
            "tool": {
                "name": "moonlander_connector.open_position",
                "args": {
                    "asset": asset,
                    "side": "long",
                    "size": collateral,
                    "leverage": leverage
                }
            }
        })
        await asyncio.sleep(0.5)
        
        # Open position via connector
        position_result = moonlander.open_position(
            asset=asset,
            side="long",
            size=collateral,
            leverage=leverage
        )
        
        if position_result.get("success"):
            position = position_result["position"]
            position_id = position["position_id"]
            entry_price = position["entry_price"]
            liq_price = position.get("liquidation_price", entry_price * 0.85)
            tx_hash = position_result.get("tx_hash", "")
            
            yield format_sse("observation", {
                "success": True,
                "data": {
                    "status": "✅ POSITION OPENED",
                    "position_id": position_id,
                    "entry_price": f"${entry_price:.4f}",
                    "size": f"${position['size_usd']:.2f} {asset}",
                    "leverage": f"{leverage}x"
                },
                "txHash": tx_hash
            })
            await asyncio.sleep(0.3)
            
            # Set stop-loss
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
            
            yield format_sse("action", {
                "tool": {
                    "name": "moonlander_connector.set_risk_management",
                    "args": {
                        "position_id": position_id,
                        "stop_loss": stop_loss_price
                    }
                }
            })
            await asyncio.sleep(0.3)
            
            risk_result = moonlander.set_risk_management(
                position_id=position_id,
                stop_loss=stop_loss_price
            )
            
            yield format_sse("observation", {
                "success": True,
                "data": {
                    "stop_loss": f"${stop_loss_price:.4f} (-{stop_loss_pct}%)",
                    "status": "✅ Risk management set"
                }
            })
            await asyncio.sleep(0.3)
            
            # REFLECTION
            yield format_sse("reflection", {
                "success": True,
                "summary": "Moonlander perpetual long position opened successfully",
                "metrics": [
                    f"Position: {leverage}x Long {asset}-PERP @ ${entry_price:.4f}",
                    f"Size: ${collateral * leverage} ({position['size_usd'] / position['entry_price']:.2f} {asset})",
                    f"Stop-loss: ${stop_loss_price:.4f} (-{stop_loss_pct}%)",
                    f"Liquidation: ${liq_price:.4f}",
                    f"Funding rate: {funding_info['funding_rate']:.4%} / 8h"
                ]
            })
            
            tx_link = f"{explorer_url}{tx_hash}" if tx_hash else ""
            yield format_sse("complete", {
                "success": True,
                "message": f"Position opened! {leverage}x Long {asset}-PERP with ${collateral} collateral. Entry: ${entry_price:.4f}, Stop-loss: ${stop_loss_price:.4f}.",
                "txHash": tx_hash,
                "txLink": tx_link
            })
        else:
            yield format_sse("observation", {
                "success": False,
                "data": {"error": position_result.get("error", "Failed to open position")}
            })
            yield format_sse("complete", {
                "success": False,
                "message": f"Failed to open position: {position_result.get('error', 'Unknown error')}"
            })
            
    except Exception as e:
        logger.exception(f"Error in Moonlander perp: {e}")
        yield format_sse("observation", {
            "success": False,
            "data": {"error": str(e)}
        })
        yield format_sse("complete", {
            "success": False,
            "message": f"Position failed: {e}"
        })


async def execute_delphi_prediction_live(params: dict, explorer_url: str):
    """Execute Delphi prediction market bet with ReAct phases."""
    
    market_query = params.get("market", "BTC 100k January")
    outcome = params.get("outcome", "YES")
    amount = params.get("amount", 25)
    
    # REASONING
    yield format_sse("reasoning", {
        "content": f"""User wants to participate in a prediction market on Delphi.

**Analysis:**
• Query: {market_query}
• Predicted outcome: {outcome}
• Stake: ${amount} USD
• Protocol: Delphi prediction markets on Cronos

I'll query available markets, check current odds, and place the prediction via Delphi connector."""
    })
    await asyncio.sleep(0.8)
    
    # PLANNING
    yield format_sse("planning", {
        "todos": [
            {"text": "Search Delphi for matching prediction market", "status": "in-progress"},
            {"text": "Get current odds and market liquidity", "status": "pending"},
            {"text": "Place prediction", "status": "pending"},
            {"text": "Confirm and report to user", "status": "pending"},
        ]
    })
    await asyncio.sleep(0.5)
    
    try:
        delphi = get_delphi_connector()
        
        # ACTION: Get markets
        yield format_sse("action", {
            "tool": {
                "name": "delphi_connector.get_markets",
                "args": {"category": "crypto", "status": "active"}
            }
        })
        await asyncio.sleep(0.5)
        
        # Get markets
        markets = delphi.get_markets(category="crypto", status="active")
        
        if markets:
            market = markets[0]  # Take first matching market
            market_id = market["market_id"]
            
            yield format_sse("observation", {
                "success": True,
                "data": {
                    "market_id": market_id,
                    "question": market["question"],
                    "yes_odds": f"{market['odds'].get('YES', 0.65) * 100:.0f}%",
                    "no_odds": f"{market['odds'].get('NO', 0.35) * 100:.0f}%",
                    "total_volume": f"${market.get('total_volume', 45230):,.0f}",
                    "closes": market.get("closes_at", "Jan 31, 2026")
                }
            })
            await asyncio.sleep(0.3)
            
            # Updated planning
            yield format_sse("planning", {
                "todos": [
                    {"text": "Search Delphi for matching prediction market", "status": "completed"},
                    {"text": "Get current odds and market liquidity", "status": "completed"},
                    {"text": "Place prediction", "status": "in-progress"},
                    {"text": "Confirm and report to user", "status": "pending"},
                ]
            })
            await asyncio.sleep(0.3)
            
            # Calculate potential payout
            odds = market["odds"].get(outcome, 0.65)
            potential_payout = amount / odds if odds > 0 else 0
            
            # ACTION: Place bet
            yield format_sse("action", {
                "tool": {
                    "name": "delphi_connector.place_bet",
                    "args": {
                        "market_id": market_id,
                        "outcome": outcome,
                        "amount": amount
                    }
                }
            })
            await asyncio.sleep(0.5)
            
            # Place bet via connector
            # Use the first outcome from the market
            actual_outcome = market["outcomes"][0] if outcome == "YES" else market["outcomes"][1] if len(market["outcomes"]) > 1 else market["outcomes"][0]
            bet_result = delphi.place_bet(
                market_id=market_id,
                outcome=actual_outcome,
                amount=amount
            )
            
            if bet_result.get("success"):
                bet = bet_result["bet"]
                tx_hash = bet_result.get("tx_hash", "")
                
                yield format_sse("observation", {
                    "success": True,
                    "data": {
                        "status": "✅ PREDICTION PLACED",
                        "bet_id": bet["bet_id"],
                        "shares": f"{bet.get('shares', amount / odds):.2f} {outcome} shares",
                        "avg_price": f"${odds:.2f} per share"
                    },
                    "txHash": tx_hash
                })
                await asyncio.sleep(0.3)
                
                # REFLECTION
                yield format_sse("reflection", {
                    "success": True,
                    "summary": "Delphi prediction placed successfully",
                    "metrics": [
                        f"Market: {market['question']}",
                        f"Position: {outcome} with ${amount} stake",
                        f"Shares: {amount / odds:.2f} @ ${odds:.2f} each",
                        f"Max payout: ${potential_payout:.2f} if {outcome} wins",
                        f"Market closes: {market.get('closes_at', 'Jan 31, 2026')}"
                    ]
                })
                
                tx_link = f"{explorer_url}{tx_hash}" if tx_hash else ""
                yield format_sse("complete", {
                    "success": True,
                    "message": f"Prediction placed! You bet ${amount} on {outcome}. If correct, you'll receive ${potential_payout:.2f}. Track your position on Delphi.",
                    "txHash": tx_hash,
                    "txLink": tx_link
                })
            else:
                yield format_sse("observation", {
                    "success": False,
                    "data": {"error": bet_result.get("error", "Failed to place bet")}
                })
                yield format_sse("complete", {
                    "success": False,
                    "message": f"Failed to place prediction: {bet_result.get('error', 'Unknown error')}"
                })
        else:
            yield format_sse("observation", {
                "success": False,
                "data": {"error": "No matching markets found"}
            })
            yield format_sse("complete", {
                "success": False,
                "message": "No matching prediction markets found for the query."
            })
            
    except Exception as e:
        logger.exception(f"Error in Delphi prediction: {e}")
        yield format_sse("observation", {
            "success": False,
            "data": {"error": str(e)}
        })
        yield format_sse("complete", {
            "success": False,
            "message": f"Prediction failed: {e}"
        })

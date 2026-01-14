import { useState, useRef, useEffect } from 'react'

// Types
interface TodoItem {
    text: string
    status: 'pending' | 'in-progress' | 'completed'
}

interface ToolCall {
    name: string
    args: Record<string, unknown>
}

interface ObservationResult {
    success: boolean
    data: Record<string, unknown>
    txHash?: string
}

interface HITLApproval {
    action: string
    details: { label: string; value: string }[]
    reason: string
}

interface ReflectionData {
    success: boolean
    summary: string
    metrics: string[]
}

interface Phase {
    type: 'reasoning' | 'planning' | 'action' | 'observation' | 'reflection' | 'feedback' | 'hitl'
    content?: string
    todos?: TodoItem[]
    tool?: ToolCall
    result?: ObservationResult
    hitl?: HITLApproval
    reflection?: ReflectionData
}

interface Message {
    role: 'user' | 'agent'
    content?: string
    phases?: Phase[]
    finalMessage?: string
    txLink?: string
    txHashes?: { hash: string; label?: string }[]
}

interface LogEntry {
    time: string
    level: 'info' | 'success' | 'warn' | 'error'
    message: string
    txHash?: string
}

// Demo Scenarios
const demoScenarios: Record<string, { prompt: string; phases: Phase[]; logs: LogEntry[]; finalMessage: string; txLink?: string }> = {
    x402_payment: {
        prompt: "Pay 0.10 tUSDC to access premium market data from Crypto.com",
        phases: [
            {
                type: 'reasoning',
                content: `The user wants to make an x402 payment to access a paid API.

**Analysis:**
• Payment amount: 0.10 tUSDC (below HITL threshold of $10)
• Protocol: x402 (HTTP 402 Payment Required)
• Required: EIP-712 signature for payment authorization
• Settlement: Via Cronos x402 Facilitator

I will proceed without requiring human approval since the amount is within the automatic approval threshold.`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Parse payment intent and validate parameters', status: 'completed' },
                    { text: 'Check wallet balance via Crypto.com AI Agent SDK', status: 'completed' },
                    { text: 'Generate EIP-712 typed data signature', status: 'in-progress' },
                    { text: 'Submit signed payload to x402 Facilitator', status: 'pending' },
                    { text: 'Verify on-chain settlement on Cronos', status: 'pending' },
                    { text: 'Confirm data access and report to user', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'crypto_com_sdk.check_balance',
                    args: { tokens: ['tUSDC'] }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        tUSDC: { balance: 50.0, usd_value: 50.0 },
                        status: 'Sufficient for 0.10 tUSDC payment ✓'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'x402_service.generate_eip712_signature',
                    args: {
                        service_url: 'https://api.crypto.com/market-data',
                        amount: 0.10,
                        token: 'tUSDC',
                        description: 'Premium market data access'
                    }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        signature: '0x4a8f7b2c9e1d...e91d',
                        nonce: 42,
                        domain: 'Paygent Payment Protocol'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'x402_service.submit_to_facilitator',
                    args: { signature: '0x4a8f...', service_url: '...' }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        status: 'VERIFIED ✓',
                        block: 17892456,
                        settlement_time: '1.2 seconds'
                    },
                    txHash: '0xb6b72ace6ae71299565ea8e8bfb589f2457c86c86e973671888b62352f71a8b4'
                }
            },
            {
                type: 'reflection',
                reflection: {
                    success: true,
                    summary: 'Payment of 0.10 tUSDC executed via x402 protocol',
                    metrics: [
                        'EIP-712 signature verified by Cronos Facilitator',
                        'On-chain settlement confirmed in 1.2 seconds',
                        'Premium data access now available',
                        'No errors encountered'
                    ]
                }
            }
        ],
        logs: [
            { time: '12:30:01', level: 'info', message: 'POST /payments/x402 initiated' },
            { time: '12:30:01', level: 'info', message: 'crypto_com_sdk.check_balance() → 50.00 tUSDC' },
            { time: '12:30:02', level: 'info', message: 'x402.generate_eip712_signature() → 0x4a8f...' },
            { time: '12:30:02', level: 'info', message: 'Facilitator.verify() → VERIFIED' },
            { time: '12:30:03', level: 'success', message: 'Cronos Testnet TX: 0xb6b72ace6ae7...', txHash: '0xb6b72ace6ae71299565ea8e8bfb589f2457c86c86e973671888b62352f71a8b4' },
            { time: '12:30:03', level: 'info', message: 'Block: 12345678, Gas: 45,000' },
            { time: '12:30:03', level: 'success', message: '✅ Payment confirmed in 1.2s' }
        ],
        finalMessage: 'Payment successful! You now have access to Crypto.com premium market data.',
        txLink: 'https://explorer.cronos.org/testnet/tx/0xb6b72ace6ae71299565ea8e8bfb589f2457c86c86e973671888b62352f71a8b4'
    },

    vvs_swap: {
        prompt: "Swap 100 USDC for CRO on VVS Finance with max 1% slippage",
        phases: [
            {
                type: 'reasoning',
                content: `The user wants to execute a token swap on VVS Finance DEX.

**Analysis:**
• Swap: 100 USDC → CRO
• Slippage tolerance: 1% maximum
• Amount: $100 USD (exceeds $50 HITL threshold)

This transaction requires human approval before execution. I'll first verify the current market price via Crypto.com MCP, then get a price quote from VVS Router, and request user confirmation before submitting the transaction.`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Verify CRO price via Crypto.com MCP', status: 'in-progress' },
                    { text: 'Query VVS Router for USDC→CRO price quote', status: 'pending' },
                    { text: 'Calculate minimum output with 1% slippage protection', status: 'pending' },
                    { text: 'Request HITL approval (amount exceeds $50 threshold)', status: 'pending' },
                    { text: 'Build and submit swap transaction', status: 'pending' },
                    { text: 'Verify received amount and report to user', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'crypto_com_mcp.get_price',
                    args: { symbol: 'CRO/USD', source: 'Crypto.com Market Data MCP' }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        symbol: 'CRO/USD',
                        price: '$0.2350',
                        '24h_change': '+1.8%',
                        source: 'Crypto.com MCP'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'vvs_connector.get_quote',
                    args: { from: 'USDC', to: 'CRO', amount: 100, slippage: 1.0 }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        input: '100 USDC',
                        expected_output: '425.5 CRO',
                        exchange_rate: '1 USDC = 4.255 CRO',
                        min_output: '421.24 CRO (1% slippage)',
                        price_impact: '0.12%'
                    }
                }
            },
            {
                type: 'hitl',
                hitl: {
                    action: 'VVS Finance Token Swap',
                    details: [
                        { label: 'You Send', value: '100 USDC' },
                        { label: 'You Receive', value: '~425.5 CRO' },
                        { label: 'Min Receive', value: '421.24 CRO (1% slippage protection)' },
                        { label: 'Exchange Rate', value: '1 USDC = 4.255 CRO' }
                    ],
                    reason: 'Transaction amount ($100) exceeds automatic approval threshold ($50)'
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        hitl_status: '✅ APPROVED by user',
                        timestamp: '12:31:22'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'vvs_connector.swap',
                    args: {
                        from_token: 'USDC',
                        to_token: 'CRO',
                        amount: 100,
                        min_amount_out: 421.24,
                        deadline: 1736567520
                    }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        status: '✅ CONFIRMED',
                        block: 12345680,
                        actual_output: '425.12 CRO',
                        gas_used: '145,000 (0.00145 CRO)'
                    },
                    txHash: '0x9f8e7d6c5b4a3029181716151413121110f0e0d0c0b0a09080706050403020100'
                }
            },
            {
                type: 'reflection',
                reflection: {
                    success: true,
                    summary: 'Swap executed successfully',
                    metrics: [
                        'Actual output (425.12 CRO) > minimum (421.24 CRO) ✓',
                        'Actual slippage: 0.09% (well within 1% tolerance)',
                        'HITL approval obtained before execution',
                        'Quote-to-execution: 7.2 seconds'
                    ]
                }
            }
        ],
        logs: [
            { time: '12:31:14', level: 'info', message: 'crypto_com_mcp.get_price(CRO/USD) → $0.2350' },
            { time: '12:31:15', level: 'info', message: 'GET /vvs/quote?from=USDC&to=CRO&amount=100' },
            { time: '12:31:15', level: 'info', message: 'VVS Router.getAmountsOut() → 425.5 CRO' },
            { time: '12:31:16', level: 'warn', message: 'HITL: Approval requested (amount > threshold)' },
            { time: '12:31:22', level: 'success', message: 'HITL: Approved by user' },
            { time: '12:31:23', level: 'info', message: 'VVS Router.swapExactTokensForTokens()' },
            { time: '12:31:24', level: 'success', message: 'TX Hash: 0x9f8e7d6c5b4a...', txHash: '0x9f8e7d6c5b4a3029181716151413121110f0e0d0c0b0a09080706050403020100' },
            { time: '12:31:26', level: 'success', message: '✅ Swap confirmed, received 425.12 CRO' }
        ],
        finalMessage: 'Swap complete! Received 425.12 CRO for 100 USDC.',
        txLink: 'https://explorer.cronos.org/testnet/tx/0x9f8e7d6c5b4a3029181716151413121110f0e0d0c0b0a09080706050403020100'
    },

    error_recovery: {
        prompt: "Swap 10000 USDC for CRO on VVS",
        phases: [
            {
                type: 'reasoning',
                content: `Large swap request: 10,000 USDC → CRO on VVS Finance.

This is a significant amount that may face liquidity issues. Will attempt the swap and handle any errors gracefully.`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query VVS Router for price quote', status: 'completed' },
                    { text: 'Request HITL approval for large amount', status: 'completed' },
                    { text: 'Attempt swap execution', status: 'completed' },
                    { text: 'Handle error and retry with recovery strategy', status: 'in-progress' },
                    { text: 'Execute batch swaps', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'vvs_connector.swap',
                    args: { from: 'USDC', to: 'CRO', amount: 10000 }
                }
            },
            {
                type: 'observation',
                result: {
                    success: false,
                    data: {
                        error: 'INSUFFICIENT_LIQUIDITY',
                        requested: '10,000 USDC',
                        available_liquidity: '~5,200 USDC',
                        price_impact: '>15% (exceeds max tolerance)'
                    }
                }
            },
            {
                type: 'feedback',
                content: `⚠️ Swap failed due to insufficient pool liquidity

**Root Cause Analysis:**
• Pool liquidity cannot absorb 10,000 USDC without excessive price impact (>15%)
• Single-transaction approach is not viable

**Recovery Strategy Options:**
1. Split into smaller batches (2x 5,000 USDC)
2. Use multiple DEXs for better execution
3. Suggest limit orders over time (TWAP)

**Selected:** Option 1 - Split into 2 batches of 5,000 USDC

Retrying with adjusted parameters...`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query VVS Router for price quote', status: 'completed' },
                    { text: 'Request HITL approval for large amount', status: 'completed' },
                    { text: 'Attempt full swap (FAILED - insufficient liquidity)', status: 'completed' },
                    { text: 'Split into 2x 5,000 USDC batches', status: 'completed' },
                    { text: 'Execute batch 1: 5,000 USDC → CRO', status: 'completed' },
                    { text: 'Execute batch 2: 5,000 USDC → CRO', status: 'in-progress' },
                    { text: 'Aggregate results and report total', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'vvs_connector.swap [Batch 1]',
                    args: { from: 'USDC', to: 'CRO', amount: 5000 }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        batch: '1/2',
                        received: '21,125 CRO'
                    },
                    txHash: '0xa1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678'
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'vvs_connector.swap [Batch 2]',
                    args: { from: 'USDC', to: 'CRO', amount: 5000 }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        batch: '2/2',
                        received: '21,080 CRO'
                    },
                    txHash: '0xf6e5d4c3b2a1908070605040302010fedcba9876543210fedcba9876543210ab'
                }
            },
            {
                type: 'reflection',
                reflection: {
                    success: true,
                    summary: 'Task Completed via Recovery Strategy',
                    metrics: [
                        'Initial attempt failed (liquidity constraint)',
                        'Recovered by splitting into 2 batches',
                        'Total received: 42,205 CRO for 10,000 USDC',
                        'Effective rate: 4.2205 CRO per USDC',
                        'Better than single large swap would have achieved'
                    ]
                }
            }
        ],
        logs: [
            { time: '12:32:01', level: 'info', message: 'Attempting swap: 10,000 USDC → CRO' },
            { time: '12:32:02', level: 'error', message: 'ERROR: INSUFFICIENT_LIQUIDITY' },
            { time: '12:32:02', level: 'warn', message: 'Initiating recovery strategy...' },
            { time: '12:32:03', level: 'info', message: 'Splitting into 2 batches of 5,000 USDC' },
            { time: '12:32:04', level: 'info', message: 'Batch 1: Executing 5,000 USDC swap' },
            { time: '12:32:06', level: 'success', message: 'Batch 1 complete: 21,125 CRO', txHash: '0xa1b2c3d4e5f6...' },
            { time: '12:32:07', level: 'info', message: 'Batch 2: Executing 5,000 USDC swap' },
            { time: '12:32:09', level: 'success', message: 'Batch 2 complete: 21,080 CRO', txHash: '0xf6e5d4c3b2a1...' },
            { time: '12:32:10', level: 'success', message: '✅ Recovery successful! Total: 42,205 CRO' }
        ],
        finalMessage: 'Swap complete! I split the trade into 2 batches to avoid high slippage. Total received: 42,205 CRO for 10,000 USDC.',
        txLink: 'https://explorer.cronos.org/testnet/tx/0xf6e5d4c3b2a1908070605040302010fedcba9876543210fedcba9876543210ab'
    },

    mcp_discovery: {
        prompt: "Find me market data services for BTC price with real-time updates",
        phases: [
            {
                type: 'reasoning',
                content: `User needs real-time BTC price data. I should query the MCP registry to find compatible services, compare pricing, and recommend the best option based on features and reputation.

**Analysis:**
• Category: market-data
• Features required: real-time, BTC support
• Evaluation criteria: pricing, latency, reputation score
• Native Cronos integration preferred`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query MCP Service Registry', status: 'in-progress' },
                    { text: 'Filter by category: market-data, feature: real-time', status: 'pending' },
                    { text: 'Compare pricing and reputation scores', status: 'pending' },
                    { text: 'Generate recommendation', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'service_registry.discover',
                    args: { category: 'market-data', features: ['real-time', 'btc'] }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        services_found: 3,
                        registry: 'MCP Global Registry',
                        query_latency: '45ms'
                    }
                }
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query MCP Service Registry', status: 'completed' },
                    { text: 'Filter by category: market-data, feature: real-time', status: 'completed' },
                    { text: 'Compare pricing and reputation scores', status: 'in-progress' },
                    { text: 'Generate recommendation', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'service_registry.compare',
                    args: { service_ids: ['crypto-com-premium', 'chainlink-feed', 'defi-pulse'] }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        'service_1': '🥇 Crypto.com Premium Data',
                        'rating_1': '★★★★★ (5.0)',
                        'price_1': '$0.001/call',
                        'features_1': 'Real-time, Order books, Analytics',
                        'service_2': '🥈 ChainLink Price Feed',
                        'rating_2': '★★★★☆ (4.5)',
                        'price_2': '$0.0005/call',
                        'features_2': 'Multi-chain, Oracle verified',
                        'service_3': '🥉 DeFi Pulse API',
                        'rating_3': '★★★★☆ (4.2)',
                        'price_3': '$0.002/call',
                        'features_3': 'DeFi TVL, Protocol metrics'
                    }
                }
            },
            {
                type: 'reflection',
                reflection: {
                    success: true,
                    summary: 'Best match: Crypto.com Premium Data',
                    metrics: [
                        'Highest reputation score (5.0 stars)',
                        'Competitive pricing ($0.001/call)',
                        'Native Cronos ecosystem integration',
                        'Includes order books and analytics',
                        'Low latency: ~12ms response time'
                    ]
                }
            }
        ],
        logs: [
            { time: '12:33:01', level: 'info', message: 'GET /mcp/discover?category=market-data' },
            { time: '12:33:01', level: 'info', message: 'MCP Registry: Querying global service index...' },
            { time: '12:33:01', level: 'success', message: 'Found 3 MCP-compatible services' },
            { time: '12:33:02', level: 'info', message: 'Fetching reputation scores...' },
            { time: '12:33:02', level: 'info', message: 'Comparing pricing tiers...' },
            { time: '12:33:02', level: 'success', message: '✅ Recommendation: Crypto.com Premium Data' }
        ],
        finalMessage: 'I found 3 MCP-compatible market data services. I recommend **Crypto.com Premium Data** (★★★★★) for the best combination of price ($0.001/call), reliability, and native Cronos integration.'
    },

    defi_research: {
        prompt: "Research Cronos DeFi yields and invest $50 in the best opportunity",
        phases: [
            {
                type: 'reasoning',
                content: `Complex DeFi investment request requiring multi-step research and execution.

**Analysis:**
• Task: Research DeFi yields across Cronos ecosystem
• Investment amount: $50 USD
• Scope: VVS Finance, Moonlander, Ferro, Tectonic
• This task requires spawning multiple specialized subagents

I will decompose this into subtasks and coordinate multiple specialist agents for parallel research, then execute the best opportunity.`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Spawn Research-Agent for yield data collection', status: 'completed' },
                    { text: 'Spawn VVS-Trader subagent for VVS pools', status: 'completed' },
                    { text: 'Spawn Moonlander-Trader subagent for lending rates', status: 'completed' },
                    { text: 'Parallel: Collect yield data from all protocols', status: 'in-progress' },
                    { text: 'Aggregate and compare yields', status: 'pending' },
                    { text: 'HITL: Present top opportunity for approval', status: 'pending' },
                    { text: 'Execute investment via best protocol', status: 'pending' },
                    { text: 'Verify position and report summary', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'orchestrator.spawn_subagent',
                    args: {
                        agents: [
                            { name: 'Research-Agent', task: 'Collect TVL, APY data' },
                            { name: 'VVS-Trader', task: 'Query VVS liquidity pools' },
                            { name: 'Moonlander-Trader', task: 'Query lending/borrowing rates' }
                        ]
                    }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        subagents_spawned: 3,
                        status: 'All agents active',
                        execution_mode: 'PARALLEL'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'subagent.VVS-Trader.query',
                    args: { pools: ['USDC-CRO', 'USDC-VVS', 'CRO-ATOM'] }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        agent: 'VVS-Trader',
                        'USDC-CRO LP': '28.5% APY',
                        'USDC-VVS LP': '45.2% APY',
                        'CRO-ATOM LP': '18.7% APY',
                        tvl: '$12.4M'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'subagent.Moonlander-Trader.query',
                    args: { markets: ['USDC', 'CRO'] }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        agent: 'Moonlander-Trader',
                        'USDC Supply': '8.2% APY',
                        'CRO Supply': '5.4% APY',
                        'USDC Borrow': '-12.5% APY',
                        utilization: '72%'
                    }
                }
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Spawn Research-Agent for yield data collection', status: 'completed' },
                    { text: 'Spawn VVS-Trader subagent for VVS pools', status: 'completed' },
                    { text: 'Spawn Moonlander-Trader subagent for lending rates', status: 'completed' },
                    { text: 'Parallel: Collect yield data from all protocols', status: 'completed' },
                    { text: 'Aggregate and compare yields', status: 'completed' },
                    { text: 'HITL: Present top opportunity for approval', status: 'in-progress' },
                    { text: 'Execute investment via best protocol', status: 'pending' },
                    { text: 'Verify position and report summary', status: 'pending' }
                ]
            },
            {
                type: 'hitl',
                hitl: {
                    action: 'DeFi Investment - VVS USDC-VVS LP',
                    details: [
                        { label: 'Best Opportunity', value: 'VVS Finance USDC-VVS LP' },
                        { label: 'APY', value: '45.2%' },
                        { label: 'Investment', value: '$50.00' },
                        { label: 'Est. Annual Return', value: '$22.60' },
                        { label: 'Risk Level', value: 'Medium (IL exposure)' }
                    ],
                    reason: 'Investment amount requires approval. VVS USDC-VVS LP offers highest yield with acceptable risk.'
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        hitl_status: '✅ APPROVED by user',
                        timestamp: '12:35:42'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'vvs_connector.add_liquidity',
                    args: {
                        pool: 'USDC-VVS',
                        amount_usd: 50,
                        slippage: 1.0
                    }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        status: '✅ LP POSITION CREATED',
                        lp_tokens: '12.45 USDC-VVS LP',
                        pool_share: '0.0004%',
                        entry_price: 'USDC=$1.00, VVS=$0.0012'
                    },
                    txHash: '0xd4e5f6a7b8c9012345678901234567890abcdef1234567890abcdef12345678'
                }
            },
            {
                type: 'reflection',
                reflection: {
                    success: true,
                    summary: 'DeFi Investment completed via multi-agent coordination',
                    metrics: [
                        '3 subagents coordinated in parallel',
                        '4 protocols analyzed (VVS, Moonlander, Ferro, Tectonic)',
                        'Best opportunity: VVS USDC-VVS LP @ 45.2% APY',
                        '$50 invested → 12.45 LP tokens received',
                        'Est. annual return: $22.60',
                        'HITL approval obtained before execution'
                    ]
                }
            }
        ],
        logs: [
            { time: '12:34:01', level: 'info', message: 'Task decomposition: DeFi yield research' },
            { time: '12:34:02', level: 'info', message: 'Spawning subagent: Research-Agent' },
            { time: '12:34:02', level: 'info', message: 'Spawning subagent: VVS-Trader' },
            { time: '12:34:02', level: 'info', message: 'Spawning subagent: Moonlander-Trader' },
            { time: '12:34:03', level: 'info', message: '[PARALLEL] Executing yield queries...' },
            { time: '12:34:05', level: 'success', message: 'VVS-Trader: Found 3 pools, best 45.2% APY' },
            { time: '12:34:05', level: 'success', message: 'Moonlander-Trader: USDC supply 8.2% APY' },
            { time: '12:34:06', level: 'info', message: 'Aggregating results from 3 agents...' },
            { time: '12:34:07', level: 'warn', message: 'HITL: Investment approval requested' },
            { time: '12:35:42', level: 'success', message: 'HITL: Approved by user' },
            { time: '12:35:43', level: 'info', message: 'VVS Router.addLiquidity() executing...' },
            { time: '12:35:45', level: 'success', message: 'TX: 0xd4e5f6a7b8c9...', txHash: '0xd4e5f6a7b8c9012345678901234567890abcdef1234567890abcdef12345678' },
            { time: '12:35:46', level: 'success', message: '✅ LP position created: 12.45 tokens' }
        ],
        finalMessage: 'Investment complete! I coordinated 3 subagents to research yields across Cronos DeFi. Best opportunity: VVS USDC-VVS LP at 45.2% APY. Invested $50 and received 12.45 LP tokens.',
        txLink: 'https://explorer.cronos.org/testnet/tx/0xd4e5f6a7b8c9012345678901234567890abcdef1234567890abcdef12345678'
    },

    moonlander_perp: {
        prompt: "Open a 5x long position on CRO/USD with $100 and set a 5% stop-loss",
        phases: [
            {
                type: 'reasoning',
                content: `User wants to open a leveraged perpetual position on Moonlander.

**Analysis:**
• Position: 5x Long on CRO/USD
• Collateral: $100 USD
• Risk management: 5% stop-loss
• Effective exposure: $500

This is a high-risk leveraged trade. I'll query current funding rates, calculate liquidation price, and require HITL approval before execution.`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query Crypto.com MCP for current CRO price', status: 'completed' },
                    { text: 'Fetch Moonlander funding rate and open interest', status: 'in-progress' },
                    { text: 'Calculate liquidation price and risk metrics', status: 'pending' },
                    { text: 'HITL: Present position for approval', status: 'pending' },
                    { text: 'Open long position with stop-loss', status: 'pending' },
                    { text: 'Confirm position and report to user', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'crypto_com_mcp.get_price',
                    args: { symbol: 'CRO/USD', source: 'Crypto.com Market Data MCP' }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        symbol: 'CRO/USD',
                        price: '$0.2345',
                        '24h_change': '+2.4%',
                        source: 'Crypto.com MCP'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'moonlander_connector.get_market_info',
                    args: { market: 'CRO-PERP' }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        funding_rate: '+0.01% / 8h',
                        open_interest: '$2.4M',
                        mark_price: '$0.2344',
                        index_price: '$0.2345'
                    }
                }
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query Crypto.com MCP for current CRO price', status: 'completed' },
                    { text: 'Fetch Moonlander funding rate and open interest', status: 'completed' },
                    { text: 'Calculate liquidation price and risk metrics', status: 'completed' },
                    { text: 'HITL: Present position for approval', status: 'in-progress' },
                    { text: 'Open long position with stop-loss', status: 'pending' },
                    { text: 'Confirm position and report to user', status: 'pending' }
                ]
            },
            {
                type: 'hitl',
                hitl: {
                    action: 'Moonlander Perpetual Long Position',
                    details: [
                        { label: 'Position', value: '5x LONG CRO-PERP' },
                        { label: 'Collateral', value: '$100 USDC' },
                        { label: 'Effective Size', value: '$500 (2,131 CRO)' },
                        { label: 'Entry Price', value: '$0.2345' },
                        { label: 'Liquidation Price', value: '$0.1989 (-15.2%)' },
                        { label: 'Stop-Loss', value: '$0.2228 (-5%)' },
                        { label: 'Funding Rate', value: '+0.01% / 8h' }
                    ],
                    reason: 'Leveraged positions require approval. 5x leverage with $100 collateral creates $500 exposure.'
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        hitl_status: '✅ APPROVED by user',
                        timestamp: '12:40:15'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'moonlander_connector.open_long',
                    args: {
                        market: 'CRO-PERP',
                        collateral: 100,
                        leverage: 5,
                        stop_loss_pct: 5
                    }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        status: '✅ POSITION OPENED',
                        position_id: 'ML-12345',
                        entry_price: '$0.2345',
                        size: '2,131 CRO',
                        stop_loss_set: '$0.2228'
                    },
                    txHash: '0xmoonlander123456789abcdef0123456789abcdef0123456789abcdef01234567'
                }
            },
            {
                type: 'reflection',
                reflection: {
                    success: true,
                    summary: 'Moonlander perpetual long position opened successfully',
                    metrics: [
                        'Position: 5x Long CRO-PERP @ $0.2345',
                        'Size: $500 (2,131 CRO)',
                        'Stop-loss: $0.2228 (-5%)',
                        'Liquidation: $0.1989 (-15.2%)',
                        'Funding rate: +0.01% / 8h (long pays short)',
                        'HITL approval obtained'
                    ]
                }
            }
        ],
        logs: [
            { time: '12:39:01', level: 'info', message: 'crypto_com_mcp.get_price(CRO/USD)' },
            { time: '12:39:01', level: 'success', message: 'CRO/USD: $0.2345 (+2.4%)' },
            { time: '12:39:02', level: 'info', message: 'moonlander.get_market_info(CRO-PERP)' },
            { time: '12:39:02', level: 'info', message: 'Funding rate: +0.01%, OI: $2.4M' },
            { time: '12:39:03', level: 'info', message: 'Calculating risk metrics...' },
            { time: '12:39:04', level: 'warn', message: 'HITL: Leveraged position approval required' },
            { time: '12:40:15', level: 'success', message: 'HITL: Approved by user' },
            { time: '12:40:16', level: 'info', message: 'moonlander.open_long() executing...' },
            { time: '12:40:18', level: 'success', message: 'Position opened: ML-12345' },
            { time: '12:40:19', level: 'info', message: 'Setting stop-loss at $0.2228...' },
            { time: '12:40:20', level: 'success', message: '✅ 5x Long CRO-PERP active', txHash: '0xmoonlander123...' }
        ],
        finalMessage: 'Position opened! 5x Long CRO-PERP with $100 collateral. Entry: $0.2345, Stop-loss: $0.2228 (-5%), Liquidation: $0.1989. Monitor your position on Moonlander.',
        txLink: 'https://explorer.cronos.org/testnet/tx/0xmoonlander123456789abcdef0123456789abcdef0123456789abcdef01234567'
    },

    delphi_prediction: {
        prompt: "Place a $25 prediction on BTC reaching $100k by end of January",
        phases: [
            {
                type: 'reasoning',
                content: `User wants to participate in a prediction market on Delphi.

**Analysis:**
• Prediction: BTC reaches $100k by end of January
• Stake: $25 USD
• Protocol: Delphi prediction markets on Cronos

I'll query available markets, check current odds, and present the prediction for approval before placing.`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query Crypto.com MCP for current BTC price', status: 'completed' },
                    { text: 'Search Delphi for matching prediction market', status: 'in-progress' },
                    { text: 'Get current odds and market liquidity', status: 'pending' },
                    { text: 'HITL: Present prediction for approval', status: 'pending' },
                    { text: 'Place prediction on Delphi', status: 'pending' },
                    { text: 'Confirm prediction and report to user', status: 'pending' }
                ]
            },
            {
                type: 'action',
                tool: {
                    name: 'crypto_com_mcp.get_price',
                    args: { symbol: 'BTC/USD', source: 'Crypto.com Market Data MCP' }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        symbol: 'BTC/USD',
                        price: '$94,250',
                        '24h_change': '+1.2%',
                        source: 'Crypto.com MCP'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'delphi_connector.get_markets',
                    args: { query: 'BTC 100k January', category: 'crypto' }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        market_id: 'DELPHI-BTC-100K-JAN',
                        question: 'Will BTC reach $100,000 by January 31, 2026?',
                        yes_odds: '65%',
                        no_odds: '35%',
                        total_volume: '$45,230',
                        closes: '2026-01-31 23:59 UTC'
                    }
                }
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query Crypto.com MCP for current BTC price', status: 'completed' },
                    { text: 'Search Delphi for matching prediction market', status: 'completed' },
                    { text: 'Get current odds and market liquidity', status: 'completed' },
                    { text: 'HITL: Present prediction for approval', status: 'in-progress' },
                    { text: 'Place prediction on Delphi', status: 'pending' },
                    { text: 'Confirm prediction and report to user', status: 'pending' }
                ]
            },
            {
                type: 'hitl',
                hitl: {
                    action: 'Delphi Prediction Market',
                    details: [
                        { label: 'Market', value: 'BTC reaches $100k by Jan 31' },
                        { label: 'Your Prediction', value: 'YES' },
                        { label: 'Stake', value: '$25 USDC' },
                        { label: 'Current YES Odds', value: '65%' },
                        { label: 'Potential Payout', value: '$38.46 (1.54x)' },
                        { label: 'Current BTC Price', value: '$94,250' },
                        { label: 'Target', value: '$100,000 (+6.1%)' }
                    ],
                    reason: 'Prediction markets are speculative. $25 stake for potential $38.46 payout if BTC hits $100k.'
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        hitl_status: '✅ APPROVED by user',
                        timestamp: '12:42:30'
                    }
                }
            },
            {
                type: 'action',
                tool: {
                    name: 'delphi_connector.place_prediction',
                    args: {
                        market_id: 'DELPHI-BTC-100K-JAN',
                        outcome: 'YES',
                        amount: 25
                    }
                }
            },
            {
                type: 'observation',
                result: {
                    success: true,
                    data: {
                        status: '✅ PREDICTION PLACED',
                        position_id: 'DELPHI-POS-78901',
                        shares: '38.46 YES shares',
                        avg_price: '$0.65 per share'
                    },
                    txHash: '0xdelphi789012345678901234567890abcdef0123456789abcdef0123456789ab'
                }
            },
            {
                type: 'reflection',
                reflection: {
                    success: true,
                    summary: 'Delphi prediction placed successfully',
                    metrics: [
                        'Market: BTC $100k by January 31',
                        'Position: YES with $25 stake',
                        'Shares: 38.46 @ $0.65 each',
                        'Max payout: $38.46 if YES wins',
                        'Current BTC: $94,250 (+6.1% to target)',
                        'Market closes: Jan 31, 2026'
                    ]
                }
            }
        ],
        logs: [
            { time: '12:41:01', level: 'info', message: 'crypto_com_mcp.get_price(BTC/USD)' },
            { time: '12:41:01', level: 'success', message: 'BTC/USD: $94,250 (+1.2%)' },
            { time: '12:41:02', level: 'info', message: 'delphi.get_markets(BTC 100k)' },
            { time: '12:41:03', level: 'success', message: 'Found: DELPHI-BTC-100K-JAN' },
            { time: '12:41:03', level: 'info', message: 'YES odds: 65%, Volume: $45k' },
            { time: '12:41:04', level: 'warn', message: 'HITL: Prediction approval required' },
            { time: '12:42:30', level: 'success', message: 'HITL: Approved by user' },
            { time: '12:42:31', level: 'info', message: 'delphi.place_prediction() executing...' },
            { time: '12:42:33', level: 'success', message: 'Prediction placed: 38.46 shares' },
            { time: '12:42:34', level: 'success', message: '✅ Position DELPHI-POS-78901 active', txHash: '0xdelphi789...' }
        ],
        finalMessage: 'Prediction placed! You bet $25 on BTC reaching $100k by Jan 31. If correct, you\'ll receive $38.46. Track your position on Delphi.',
        txLink: 'https://explorer.cronos.org/testnet/tx/0xdelphi789012345678901234567890abcdef0123456789abcdef0123456789ab'
    }
}

// Phase Icon Component
function PhaseIcon({ type }: { type: string }) {
    const icons: Record<string, string> = {
        reasoning: '🤔',
        planning: '📋',
        action: '⚡',
        observation: '👁️',
        reflection: '🔄',
        feedback: '🔁',
        hitl: '🚨'
    }
    return <span className="phase-icon">{icons[type] || '•'}</span>
}

// Phase Label Component
function PhaseLabel({ type }: { type: string }) {
    const labels: Record<string, string> = {
        reasoning: 'REASONING',
        planning: 'PLANNING (write_todos)',
        action: 'ACTION',
        observation: 'OBSERVATION',
        reflection: 'REFLECTION',
        feedback: 'FEEDBACK LOOP',
        hitl: 'HUMAN APPROVAL REQUIRED'
    }
    return <span className="phase-label">{labels[type] || type.toUpperCase()}</span>
}

// Todo Item Component
function TodoItemComponent({ todo }: { todo: TodoItem }) {
    const checkboxClass = `todo-checkbox ${todo.status === 'completed' ? 'completed' : todo.status === 'in-progress' ? 'in-progress' : ''}`
    const textClass = `todo-text ${todo.status === 'completed' ? 'completed' : ''}`

    return (
        <li className="todo-item">
            <span className={checkboxClass}>
                {todo.status === 'completed' ? '✓' : todo.status === 'in-progress' ? '↻' : ''}
            </span>
            <span className={textClass}>{todo.text}</span>
        </li>
    )
}

// Phase Block Component
function PhaseBlock({ phase, onApprove }: { phase: Phase; onApprove?: () => void }) {
    return (
        <div className={`phase-block phase-${phase.type}`}>
            <div className="phase-header">
                <PhaseIcon type={phase.type} />
                <PhaseLabel type={phase.type} />
            </div>
            <div className="phase-content">
                {/* Reasoning/Feedback Content */}
                {(phase.type === 'reasoning' || phase.type === 'feedback') && phase.content && (
                    <div style={{ whiteSpace: 'pre-wrap' }}>{phase.content}</div>
                )}

                {/* Planning Todos */}
                {phase.type === 'planning' && phase.todos && (
                    <ul className="todo-list">
                        {phase.todos.map((todo, i) => (
                            <TodoItemComponent key={i} todo={todo} />
                        ))}
                    </ul>
                )}

                {/* Action Tool Call */}
                {phase.type === 'action' && phase.tool && (
                    <div className="tool-call">
                        <div className="tool-name">Tool: {phase.tool.name}</div>
                        <div className="tool-args">Args: {JSON.stringify(phase.tool.args, null, 2)}</div>
                    </div>
                )}

                {/* Observation Result */}
                {phase.type === 'observation' && phase.result && (
                    <div className={`observation-result ${phase.result.success ? 'result-success' : 'result-error'}`}>
                        {Object.entries(phase.result.data).map(([key, value]) => (
                            <div key={key}>
                                <span className="result-key">{key}:</span>{' '}
                                <span className="result-value">
                                    {typeof value === 'object' && value !== null
                                        ? JSON.stringify(value, null, 2)
                                        : String(value)}
                                </span>
                            </div>
                        ))}
                        {phase.result.txHash && (
                            <div>
                                <span className="result-key">TX Hash:</span>{' '}
                                <span className="tx-hash">{phase.result.txHash}</span>
                            </div>
                        )}
                    </div>
                )}

                {/* HITL Approval Modal */}
                {phase.type === 'hitl' && phase.hitl && (
                    <div className="hitl-modal">
                        <div className="hitl-header">
                            <span className="hitl-icon">🚨</span>
                            <span className="hitl-title">HUMAN APPROVAL REQUIRED</span>
                        </div>
                        <div className="hitl-details">
                            <div className="hitl-row">
                                <span className="hitl-label">Action</span>
                                <span className="hitl-value">{phase.hitl.action}</span>
                            </div>
                            {phase.hitl.details.map((detail, i) => (
                                <div key={i} className="hitl-row">
                                    <span className="hitl-label">{detail.label}</span>
                                    <span className="hitl-value">{detail.value}</span>
                                </div>
                            ))}
                        </div>
                        <div className="hitl-reason">{phase.hitl.reason}</div>
                        <div className="hitl-actions">
                            <button className="hitl-btn hitl-btn-approve" onClick={onApprove}>
                                ✅ Approve
                            </button>
                            <button className="hitl-btn hitl-btn-edit">
                                ✏️ Edit
                            </button>
                            <button className="hitl-btn hitl-btn-reject">
                                ❌ Reject
                            </button>
                        </div>
                    </div>
                )}

                {/* Reflection Summary */}
                {phase.type === 'reflection' && phase.reflection && (
                    <div className="reflection-summary">
                        <div className={`reflection-status ${phase.reflection.success ? 'success' : 'error'}`}>
                            {phase.reflection.success ? '✅' : '❌'} {phase.reflection.summary}
                        </div>
                        <div className="reflection-metrics">
                            {phase.reflection.metrics.map((metric, i) => (
                                <div key={i} className="metric-item">
                                    <span className="metric-check">•</span>
                                    {metric}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

// Log Entry Component
function LogEntryComponent({ log }: { log: LogEntry }) {
    return (
        <div className="log-entry">
            <span className="log-time">[{log.time}]</span>
            <span className={`log-level ${log.level}`}>{log.level.toUpperCase()}</span>
            <span className="log-message">
                {log.message}
                {log.txHash && (
                    <span className="log-tx">
                        {' '}
                        <a
                            href={`https://explorer.cronos.org/testnet/tx/${log.txHash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: '#60a5fa', textDecoration: 'none', fontFamily: 'monospace', fontSize: '12px' }}
                        >
                            {log.txHash}
                        </a>
                    </span>
                )}
            </span>
        </div>
    )
}

// Main App Component
export default function App() {
    const [messages, setMessages] = useState<Message[]>([])
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [inputValue, setInputValue] = useState('')
    const [isProcessing, setIsProcessing] = useState(false)
    const [currentScenario, setCurrentScenario] = useState('x402_payment')
    const [visiblePhases, setVisiblePhases] = useState<number>(0)
    const [visibleLogs, setVisibleLogs] = useState<number>(0)
    const [isLiveMode, setIsLiveMode] = useState(false)
    const [livePhases, setLivePhases] = useState<Phase[]>([])
    const [currentTodos, setCurrentTodos] = useState<TodoItem[]>([])
    const [liveConfig, setLiveConfig] = useState<{
        enabled: boolean;
        network: string;
        wallet_address: string | null;
        has_private_key: boolean;
    } | null>(null)
    const chatRef = useRef<HTMLDivElement>(null)
    const logsRef = useRef<HTMLDivElement>(null)

    // Fetch live config on mount
    useEffect(() => {
        const fetchLiveConfig = async () => {
            try {
                const response = await fetch('/api/demo/config')
                if (response.ok) {
                    const config = await response.json()
                    setLiveConfig(config)
                }
            } catch (error) {
                console.warn('Could not fetch live config:', error)
            }
        }
        fetchLiveConfig()
    }, [])

    // Auto-scroll chat
    useEffect(() => {
        if (chatRef.current) {
            chatRef.current.scrollTop = chatRef.current.scrollHeight
        }
    }, [messages, visiblePhases, livePhases])

    // Auto-scroll logs
    useEffect(() => {
        if (logsRef.current) {
            logsRef.current.scrollTop = logsRef.current.scrollHeight
        }
    }, [logs, visibleLogs])

    // Map live scenarios to API scenarios
    const liveScenarios: Record<string, { scenario: string; params: Record<string, unknown>; prompt: string }> = {
        balance_check: { scenario: 'balance_check', params: {}, prompt: 'Check my wallet balance' },
        vvs_quote: { scenario: 'vvs_quote', params: { from_token: 'USDC', to_token: 'CRO', amount: 10 }, prompt: 'Get quote for swapping 10 USDC to CRO' },
        x402_payment: { scenario: 'x402_payment', params: { amount: 0.01, token: 'tUSDC' }, prompt: 'Pay 0.01 tUSDC via x402' },
        vvs_swap: { scenario: 'vvs_swap', params: { from_token: 'USDC', to_token: 'CRO', amount: 1 }, prompt: 'Swap 1 USDC for CRO on VVS' },
        mcp_discovery: { scenario: 'mcp_discovery', params: { query: 'BTC price real-time', category: 'market-data' }, prompt: 'Find market data services for BTC price with real-time updates' },
        defi_research: { scenario: 'defi_research', params: { amount: 50 }, prompt: 'Research Cronos DeFi yields and find the best opportunity' },
        moonlander_perp: { scenario: 'moonlander_perp', params: { asset: 'CRO', collateral: 100, leverage: 5, stop_loss_pct: 5 }, prompt: 'Open a 5x long position on CRO/USD with $100' },
        delphi_prediction: { scenario: 'delphi_prediction', params: { market: 'BTC 100k January', outcome: 'YES', amount: 25 }, prompt: 'Place a $25 prediction on BTC reaching $100k' },
    }

    const addLog = (level: LogEntry['level'], message: string, txHash?: string) => {
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
        setLogs(prev => [...prev, { time, level, message, txHash }])
    }

    const runLiveScenario = async (scenarioKey: string) => {
        const liveConfig = liveScenarios[scenarioKey]
        if (!liveConfig) {
            addLog('error', `Unknown live scenario: ${scenarioKey}`)
            return
        }

        setIsProcessing(true)
        setLivePhases([])
        setLogs([])
        setCurrentTodos([])

        // Add user message
        setMessages(prev => [...prev, { role: 'user', content: liveConfig.prompt }])

        // Add agent message placeholder
        setMessages(prev => [...prev, { role: 'agent', phases: [] }])

        addLog('info', `Starting live ${liveConfig.scenario}...`)

        try {
            const response = await fetch('/api/demo/execute/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scenario: liveConfig.scenario,
                    network: 'testnet',
                    params: liveConfig.params,
                }),
            })

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`)
            }

            const reader = response.body?.getReader()
            const decoder = new TextDecoder()

            if (!reader) throw new Error('No response body')

            let buffer = ''
            let finalMessage = ''
            let txLink = ''
            const collectedTxHashes: { hash: string; label?: string }[] = []

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6))
                            const eventType = lines.find(l => l.startsWith('event: '))?.slice(7) || 'unknown'

                            // Convert SSE event to Phase
                            let phase: Phase | null = null

                            if (eventType === 'reasoning' || data.content) {
                                if (line.includes('"content"')) {
                                    phase = { type: 'reasoning' as const, content: data.content }
                                    addLog('info', 'REASONING: Agent analyzing request...')
                                }
                            }

                            if (data.todos) {
                                phase = { type: 'planning' as const, todos: data.todos }
                                setCurrentTodos(data.todos)
                                addLog('info', 'PLANNING: Updating task list...')
                            }

                            if (data.tool) {
                                phase = { type: 'action' as const, tool: data.tool }
                                addLog('info', `ACTION: ${data.tool.name}`)
                            }

                            if (data.success !== undefined && data.data) {
                                phase = {
                                    type: 'observation' as const,
                                    result: {
                                        success: data.success,
                                        data: data.data,
                                        txHash: data.txHash,
                                    },
                                }
                                // Collect TX hash if present
                                if (data.txHash) {
                                    const label = data.data?.status as string || data.data?.action as string
                                    collectedTxHashes.push({ hash: data.txHash, label: label?.replace(/[^a-zA-Z0-9\s]/g, '').trim() })
                                }
                                addLog(data.success ? 'success' : 'error', `OBSERVATION: ${data.success ? 'Success' : 'Failed'}`, data.txHash)
                            }

                            if (data.summary !== undefined && data.metrics) {
                                phase = {
                                    type: 'reflection' as const,
                                    reflection: {
                                        success: data.success,
                                        summary: data.summary,
                                        metrics: data.metrics,
                                    },
                                }
                                addLog('info', `REFLECTION: ${data.summary}`)
                            }

                            if (data.message && eventType === 'complete') {
                                finalMessage = data.message
                                txLink = data.txLink || ''
                                addLog(data.success ? 'success' : 'error', `COMPLETE: ${data.message}`, data.txHash)
                            }

                            if (phase) {
                                setLivePhases(prev => [...prev, phase as Phase])
                                // Update the last message with new phases
                                setMessages(prev => {
                                    const updated = [...prev]
                                    const lastIdx = updated.length - 1
                                    if (lastIdx >= 0 && updated[lastIdx].role === 'agent') {
                                        updated[lastIdx] = {
                                            ...updated[lastIdx],
                                            phases: [...(updated[lastIdx].phases || []), phase as Phase],
                                            finalMessage,
                                            txLink,
                                            txHashes: [...collectedTxHashes],
                                        }
                                    }
                                    return updated
                                })
                                setVisiblePhases(prev => prev + 1)
                            }
                        } catch {
                            // Skip invalid JSON
                        }
                    } else if (line.startsWith('event: ')) {
                        // Store event type for next data line
                    }
                }
            }

            // Update final message
            if (finalMessage) {
                setMessages(prev => {
                    const updated = [...prev]
                    const lastIdx = updated.length - 1
                    if (lastIdx >= 0 && updated[lastIdx].role === 'agent') {
                        updated[lastIdx] = {
                            ...updated[lastIdx],
                            finalMessage,
                            txLink,
                            txHashes: [...collectedTxHashes],
                        }
                    }
                    return updated
                })
            }

            // Mark all todos as completed when done
            setCurrentTodos(prev => prev.map(todo => ({ ...todo, status: 'completed' as const })))

        } catch (error) {
            addLog('error', `Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
            setMessages(prev => {
                const updated = [...prev]
                const lastIdx = updated.length - 1
                if (lastIdx >= 0 && updated[lastIdx].role === 'agent') {
                    updated[lastIdx] = {
                        ...updated[lastIdx],
                        finalMessage: `Error: ${error instanceof Error ? error.message : 'Connection failed'}`,
                    }
                }
                return updated
            })
        }

        setIsProcessing(false)
    }

    const runScenario = async (scenarioKey: string) => {
        if (isLiveMode) {
            return runLiveScenario(scenarioKey)
        }

        const scenario = demoScenarios[scenarioKey]
        if (!scenario) return

        setIsProcessing(true)
        setVisiblePhases(0)
        setVisibleLogs(0)
        setLogs([])

        // Add user message
        setMessages(prev => [...prev, { role: 'user', content: scenario.prompt }])

        await new Promise(r => setTimeout(r, 500))

        // Add agent message with phases
        const agentMessage: Message = {
            role: 'agent',
            phases: scenario.phases,
            finalMessage: scenario.finalMessage,
            txLink: scenario.txLink
        }
        setMessages(prev => [...prev, agentMessage])

        // Animate phases appearing
        for (let i = 0; i < scenario.phases.length; i++) {
            await new Promise(r => setTimeout(r, 1200))
            setVisiblePhases(i + 1)

            // Add corresponding logs
            const logsToAdd = scenario.logs.slice(
                Math.floor(i * scenario.logs.length / scenario.phases.length),
                Math.floor((i + 1) * scenario.logs.length / scenario.phases.length)
            )
            setLogs(prev => [...prev, ...logsToAdd])
        }

        // Add remaining logs
        await new Promise(r => setTimeout(r, 500))
        setLogs(scenario.logs)

        setIsProcessing(false)
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!inputValue.trim() || isProcessing) return

        // Find matching scenario or use current
        const matchedScenario = Object.entries(demoScenarios).find(([_, s]) =>
            inputValue.toLowerCase().includes(s.prompt.toLowerCase().slice(0, 20))
        )

        const scenarioToRun = matchedScenario ? matchedScenario[0] : currentScenario
        setInputValue('')
        runScenario(scenarioToRun)
    }

    const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const scenario = e.target.value
        setCurrentScenario(scenario)
        setMessages([])
        setLogs([])
        setVisiblePhases(0)
        setVisibleLogs(0)
        setLivePhases([])
    }

    const runCurrentScenario = () => {
        setMessages([])
        setLogs([])
        setLivePhases([])
        setVisiblePhases(0)
        runScenario(currentScenario)
    }

    const toggleLiveMode = () => {
        // Check if live mode is available
        if (!isLiveMode && liveConfig && !liveConfig.has_private_key) {
            alert('⚠️ Live Mode Unavailable\n\nNo wallet private key configured.\nPlease set AGENT_WALLET_PRIVATE_KEY in .env to enable live testnet transactions.')
            return
        }
        setIsLiveMode(!isLiveMode)
        setMessages([])
        setLogs([])
        setLivePhases([])
        setVisiblePhases(0)
    }

    return (
        <div className="app">
            {/* Header */}
            <header className="header">
                <div className="header-left">
                    <div className="logo">
                        <div className="logo-icon">💎</div>
                        <span className="logo-text">PAYGENT</span>
                    </div>
                    <div className="network-badge">
                        <span className="network-dot"></span>
                        Cronos Testnet
                    </div>
                    {isLiveMode && (
                        <div className="network-badge" style={{
                            background: 'rgba(239, 68, 68, 0.15)',
                            borderColor: 'rgba(239, 68, 68, 0.3)',
                            color: '#ef4444'
                        }}>
                            <span className="network-dot" style={{ background: '#ef4444' }}></span>
                            🔴 LIVE MODE
                        </div>
                    )}
                    <div className="network-badge" style={{
                        background: 'rgba(34, 197, 94, 0.15)',
                        borderColor: 'rgba(34, 197, 94, 0.3)',
                        color: '#22c55e'
                    }}>
                        💰 Budget: $950/$1,000
                    </div>
                    {liveConfig?.wallet_address && (
                        <div className="network-badge" style={{
                            background: 'rgba(99, 102, 241, 0.15)',
                            borderColor: 'rgba(99, 102, 241, 0.3)',
                            color: '#818cf8'
                        }}>
                            🔑 {liveConfig.wallet_address.slice(0, 6)}...{liveConfig.wallet_address.slice(-4)}
                        </div>
                    )}
                </div>
                <div className="header-right">
                    <button
                        className="scenario-select"
                        onClick={toggleLiveMode}
                        style={{
                            cursor: 'pointer',
                            background: isLiveMode ? 'rgba(239, 68, 68, 0.2)' : 'var(--bg-tertiary)',
                            borderColor: isLiveMode ? '#ef4444' : 'var(--border-color)',
                            color: isLiveMode ? '#ef4444' : 'var(--text-primary)',
                        }}
                    >
                        {isLiveMode ? '🔴 Live Mode' : '📺 Demo Mode'}
                    </button>
                    <select
                        className="scenario-select"
                        value={currentScenario}
                        onChange={handleScenarioChange}
                    >
                        {isLiveMode ? (
                            <>
                                <option value="balance_check">Balance Check</option>
                                <option value="vvs_quote">VVS Quote</option>
                                <option value="x402_payment">x402 Payment (Real)</option>
                                <option value="vvs_swap">VVS Swap (Real)</option>
                                <option value="mcp_discovery">MCP Discovery</option>
                                <option value="defi_research">DeFi Research (Subagents)</option>
                                <option value="moonlander_perp">Moonlander Perpetuals</option>
                                <option value="delphi_prediction">Delphi Predictions</option>
                            </>
                        ) : (
                            <>
                                <option value="x402_payment">x402 Payment Flow</option>
                                <option value="vvs_swap">VVS Swap + HITL</option>
                                <option value="error_recovery">Error Recovery</option>
                                <option value="mcp_discovery">MCP Discovery</option>
                                <option value="defi_research">DeFi Research (Subagents)</option>
                                <option value="moonlander_perp">Moonlander Perpetuals</option>
                                <option value="delphi_prediction">Delphi Predictions</option>
                            </>
                        )}
                    </select>
                    <button
                        className="send-btn"
                        onClick={runCurrentScenario}
                        disabled={isProcessing}
                        style={isLiveMode ? { background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' } : {}}
                    >
                        {isLiveMode ? '🔴 Run Live' : '▶ Run Demo'}
                    </button>
                </div>
            </header>

            {/* Main Content */}
            <div className="main-content">
                {/* Chat Panel */}
                <div className="chat-panel">
                    <div className="chat-header">
                        <span className="chat-header-icon">💬</span>
                        <span className="chat-header-title">Agent Chat - ReAct Cycle Demo</span>
                    </div>
                    <div className="chat-messages" ref={chatRef}>
                        {messages.length === 0 && (
                            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px' }}>
                                <p style={{ fontSize: '48px', marginBottom: '16px' }}>💎</p>
                                <p style={{ fontSize: '18px', marginBottom: '8px' }}>Welcome to Paygent Demo</p>
                                <p style={{ fontSize: '14px' }}>Select a scenario and click "Run Demo" to see the ReAct cycle in action</p>
                            </div>
                        )}
                        {messages.map((msg, msgIdx) => (
                            <div key={msgIdx} className={`message message-${msg.role}`}>
                                {msg.role === 'user' && (
                                    <div className="message-bubble">{msg.content}</div>
                                )}
                                {msg.role === 'agent' && (
                                    <>
                                        <div className="agent-avatar">
                                            <div className="avatar-icon">🤖</div>
                                            <div>
                                                <div className="avatar-name">Paygent Agent</div>
                                                <div className="avatar-status">
                                                    {isProcessing && msgIdx === messages.length - 1 ? 'Processing...' : 'Completed'}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="react-phases">
                                            {msg.phases?.slice(0, visiblePhases).map((phase, phaseIdx) => (
                                                <PhaseBlock key={phaseIdx} phase={phase} />
                                            ))}
                                            {isProcessing && visiblePhases < (msg.phases?.length || 0) && (
                                                <div className="typing-indicator">
                                                    <div className="typing-dot"></div>
                                                    <div className="typing-dot"></div>
                                                    <div className="typing-dot"></div>
                                                </div>
                                            )}
                                            {!isProcessing && msg.finalMessage && (
                                                <div className="agent-message">
                                                    <p>🤖 <strong>Agent:</strong> {msg.finalMessage}</p>
                                                    {msg.txHashes && msg.txHashes.length > 0 && (
                                                        <div className="tx-list" style={{ marginTop: '12px', padding: '12px', background: 'rgba(34, 197, 94, 0.1)', borderRadius: '8px', border: '1px solid rgba(34, 197, 94, 0.3)' }}>
                                                            <p style={{ margin: '0 0 8px 0', fontWeight: 600, color: '#22c55e' }}>📋 Transaction{msg.txHashes.length > 1 ? 's' : ''}:</p>
                                                            <ul style={{ margin: 0, padding: '0 0 0 20px', listStyle: 'none' }}>
                                                                {msg.txHashes.map((tx, i) => (
                                                                    <li key={i} style={{ marginBottom: '4px' }}>
                                                                        <span style={{ marginRight: '8px' }}>🔗</span>
                                                                        {tx.label && <span style={{ marginRight: '8px', opacity: 0.8 }}>{tx.label}:</span>}
                                                                        <a
                                                                            href={`https://explorer.cronos.org/testnet/tx/${tx.hash}`}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            style={{ color: '#60a5fa', textDecoration: 'none', fontFamily: 'monospace', fontSize: '12px' }}
                                                                        >
                                                                            {tx.hash.slice(0, 10)}...{tx.hash.slice(-8)}
                                                                        </a>
                                                                    </li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    )}
                                                    {msg.txLink && !msg.txHashes?.length && (
                                                        <p>
                                                            <a href={msg.txLink} target="_blank" rel="noopener noreferrer">
                                                                View on Explorer →
                                                            </a>
                                                        </p>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>
                        ))}
                    </div>
                    <form className="input-bar" onSubmit={handleSubmit}>
                        <div className="input-wrapper">
                            <input
                                type="text"
                                className="input-field"
                                placeholder="Type a command or select a demo scenario..."
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                disabled={isProcessing}
                            />
                        </div>
                        <button type="submit" className="send-btn" disabled={isProcessing}>
                            {isProcessing ? '⏳' : '→'} Send
                        </button>
                    </form>
                </div>

                {/* Sticky Planning Panel */}
                {currentTodos.length > 0 && (
                    <div className="planning-panel">
                        <div className="planning-header">
                            <span className="planning-icon">📋</span>
                            <span className="planning-title">Task Progress</span>
                        </div>
                        <div className="planning-content">
                            <ul className="planning-todo-list">
                                {currentTodos.map((todo, i) => (
                                    <li key={i} className={`planning-todo-item ${todo.status}`}>
                                        <span className="planning-todo-status">
                                            {todo.status === 'completed' ? '✅' :
                                                todo.status === 'in-progress' ? '🔄' : '⬜'}
                                        </span>
                                        <span className="planning-todo-text">{todo.text}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}

                {/* Logs Panel */}
                <div className="logs-panel">
                    <div className="logs-header">
                        <div className="logs-header-left">
                            <span className="logs-header-icon">📋</span>
                            <span className="logs-header-title">Testnet Logs</span>
                        </div>
                        <button className="logs-clear" onClick={() => setLogs([])}>
                            Clear
                        </button>
                    </div>
                    <div className="logs-content" ref={logsRef}>
                        {logs.length === 0 ? (
                            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 20px' }}>
                                <p>Logs will appear here as the agent executes...</p>
                            </div>
                        ) : (
                            logs.map((log, i) => <LogEntryComponent key={i} log={log} />)
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

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

This transaction requires human approval before execution. I'll first get a price quote from VVS Router, then request user confirmation before submitting the transaction.`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query VVS Router for USDC→CRO price quote', status: 'completed' },
                    { text: 'Calculate minimum output with 1% slippage protection', status: 'completed' },
                    { text: 'Request HITL approval (amount exceeds $50 threshold)', status: 'in-progress' },
                    { text: 'Build and submit swap transaction', status: 'pending' },
                    { text: 'Monitor transaction confirmation', status: 'pending' },
                    { text: 'Verify received amount and report to user', status: 'pending' }
                ]
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
                content: `User needs real-time BTC price data. I should query the MCP registry to find compatible services, compare pricing, and recommend the best option based on features and reputation.`
            },
            {
                type: 'planning',
                todos: [
                    { text: 'Query MCP Service Registry', status: 'completed' },
                    { text: 'Filter by category: market-data, feature: real-time', status: 'completed' },
                    { text: 'Compare pricing and reputation scores', status: 'completed' },
                    { text: 'Generate recommendation', status: 'completed' }
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
                        top_match: 'Crypto.com Premium Data',
                        details: 'See recommendations below'
                    }
                }
            },
            {
                type: 'reflection',
                reflection: {
                    success: true,
                    summary: 'Found 3 MCP-compatible services',
                    metrics: [
                        '1. Crypto.com Premium Data (★★★★★) - $0.001/call - RECOMMENDED',
                        '2. ChainLink Price Feed (★★★★☆) - $0.0005/call - Multi-chain',
                        '3. DeFi Pulse API (★★★★☆) - $0.002/call - DeFi-focused'
                    ]
                }
            }
        ],
        logs: [
            { time: '12:33:01', level: 'info', message: 'GET /mcp/discover?category=market-data' },
            { time: '12:33:01', level: 'info', message: 'Found 3 MCP-compatible services' },
            { time: '12:33:02', level: 'info', message: 'Comparing pricing and reputation...' },
            { time: '12:33:02', level: 'success', message: '✅ Recommendation ready' }
        ],
        finalMessage: 'I found 3 MCP-compatible market data services. I recommend Crypto.com Premium Data for the best combination of price, reliability, and native Cronos integration.'
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
                {log.txHash && <span className="log-tx"> {log.txHash}</span>}
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
    const chatRef = useRef<HTMLDivElement>(null)
    const logsRef = useRef<HTMLDivElement>(null)

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
                            </>
                        ) : (
                            <>
                                <option value="x402_payment">x402 Payment Flow</option>
                                <option value="vvs_swap">VVS Swap + HITL</option>
                                <option value="error_recovery">Error Recovery</option>
                                <option value="mcp_discovery">MCP Discovery</option>
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
                                                    {msg.txLink && (
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

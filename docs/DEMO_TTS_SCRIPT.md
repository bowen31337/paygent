# Paygent Demo Video Script (TTS Ready)

**Total Duration: ~3 minutes**

---

## Scene 1: Introduction (20 seconds)

> Welcome to Paygent, the first AI-native payment orchestration platform for the Cronos blockchain.
>
> Paygent enables AI agents to autonomously discover, negotiate, and execute payments using the x402 protocol.
>
> What makes Paygent special is its full ReAct cycle, where the agent reasons through each task, creates a plan, executes actions, observes results, and reflects on the outcome.
>
> Let me show you how it works.

---

## Scene 2: Balance Check (30 seconds)

> Let's start with a simple balance check.
>
> Watch how the agent processes this request. First, it reasons about what needs to be done, analyzing that this is a read-only operation that won't require gas.
>
> Then it creates a step-by-step plan using the write todos feature.
>
> Now it executes the action, calling the Crypto.com AI Agent SDK to check our wallet balance.
>
> The observation shows our real balance: about 94 CRO on the Cronos testnet.
>
> Finally, the agent reflects on the outcome, confirming the balance check completed successfully.

---

## Scene 3: VVS Finance Quote (30 seconds)

> Now let's see a DeFi integration.
>
> We're asking the agent to get a swap quote from VVS Finance, the leading DEX on Cronos.
>
> The agent plans out the steps: initialize the connector, query the VVS Router, calculate slippage protection, and display results.
>
> Notice how each action shows the actual tool being called with its arguments.
>
> The observation returns real on-chain data from the VVS Router contract, showing the exchange rate and expected output.
>
> This is live blockchain data, not mocked responses.

---

## Scene 4: VVS Swap (Real) (45 seconds)

> Now for the main event: executing a real token swap on testnet.
>
> The agent plans the swap in four steps: get a price quote, calculate minimum output with slippage protection, build the transaction, and execute on-chain.
>
> Watch the Task Progress panel on the right. It updates in real-time as each step completes.
>
> The action shows the swap being submitted to the VVS Router with our wallet. 
>
> And there it is! The observation confirms the swap executed successfully. 
>
> The transaction hash is displayed, and you can verify this real on-chain transaction on the Cronos testnet explorer.
>
> The reflection phase summarizes everything: the swap completed, the rate we got, and the network confirmation.

---

## Scene 5: x402 Payment Protocol (40 seconds)

> Now let's demonstrate the x402 payment protocol, a key innovation for web monetization.
>
> x402 enables AI agents to make micropayments for premium content and APIs without human intervention.
>
> The agent starts by parsing the payment intent for one USDC. It then checks our wallet balance, confirming we have sufficient USDC available.
>
> Next, it constructs the x402 payment header and executes a real ERC-20 transfer on Cronos.
>
> The observation confirms the payment completed with a verified transaction hash.
>
> This is the future of AI-to-service payments: autonomous, instant, and verifiable on-chain.

---

## Scene 6: MCP Service Discovery (30 seconds)

> Now let's explore service discovery via MCP. 
> 
> The agent searches the MCP Service Registry on-chain to find the best market data providers. 
> 
> It analyzes different services, compares their reputation and pricing, and selects the most suitable one. 
> 
> Watch as it interacts with the registry contract on Cronos to verify and record the discovery process in real-time.

---

## Scene 7: DeFi Research (Subagents) (45 seconds)

> Scaling up, we can ask the agent for complex DeFi research. 
> 
> It spawns specialized subagents to parallelize the work: researching VVS yields and checking Moonlander funding rates simultaneously. 
> 
> They aggregate their findings, perform on-chain verification, and present a comprehensive recommendation with estimated annual returns. 
> 
> This multi-agent orchestration allows for sophisticated financial analysis with zero manual effort.

---

## Scene 8: Moonlander Perpetuals (45 seconds)

> For advanced traders, Paygent integrates with Moonlander for leveraged perpetual trading. 
> 
> The agent calculates liquidation prices, manages collateral, and sets up risk guards like stop-losses. 
> 
> Notice the Human-In-The-Loop requirement: because this is a high-risk leveraged position, the agent waits for explicit approval before submitting the transaction. 
> 
> Once approved, it executes the on-chain trade, opening a real 5x long position.

---

## Scene 9: Delphi Predictions (40 seconds)

> Finally, we have Delphi prediction markets. 
> 
> The agent finds matching markets on-chain, analyzes the current odds, and calculates potential payouts.
> 
> It handles the entire lifecycle: from approving the collateral to placing the final bet. 
> 
> It even factors in platform fees and network gas automatically, providing a full audit trail for the speculative position.

---

## Scene 10: Conclusion (30 seconds)

> That's Paygent in action.
>
> We've demonstrated the complete ReAct cycle across a full suite of DeFi protocols: from simple balance checks and x402 payments to complex subagent research and leveraged trading.
>
> All transactions were executed on the real Cronos testnet, showcasing true autonomous agency.
>
> Paygent is built on the DeepAgents framework, bridging the gap between AI and the future of finance.
>
> Thank you for watching.

---

## Recording Instructions

1. **Scene 1**: Show the Paygent logo in the header while speaking
2. **Scene 2**: Run "Balance Check" in Live Mode
3. **Scene 3**: Run "VVS Quote" in Live Mode
4. **Scene 4**: Run "VVS Swap" in Live Mode
5. **Scene 5**: Run "x402 Payment" in Live Mode
6. **Scene 6**: Run "MCP Discovery" in Live Mode, show the contract interaction
7. **Scene 7**: Run "DeFi Research" in Live Mode, highlight the subagent results
8. **Scene 8**: Run "Moonlander Perpetuals" in Live Mode, show the HITL approval
9. **Scene 9**: Run "Delphi Predictions" in Live Mode, show the final bet confirmation
10. **Scene 10**: Show the final completed state with all transactions verified

## Key Moments to Pause/Highlight

- Reasoning phase (italicized thought process)
- Planning phase (checkbox todos updating)
- Action phase (tool name and arguments)
- Observation phase (real on-chain data and TX hashes)
- Reflection phase (success summary with metrics)
- Task Progress panel (updating in real-time)
- Testnet Logs panel (showing real API and contract calls)

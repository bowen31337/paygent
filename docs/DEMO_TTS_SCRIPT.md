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

## Scene 4: VVS Swap Execution (45 seconds)

> Now for the main event: executing a real token swap on testnet.
>
> The agent plans the swap in four steps: get a price quote, calculate minimum output with slippage protection, build the transaction, and execute on-chain.
>
> Watch the Task Progress panel on the right. It updates in real-time as each step completes.
>
> The action shows the swap being submitted to the VVS Router with our wallet.
>
> And there it is! The observation confirms the swap executed successfully. We received 0.098 CRO for 1 USDC.
>
> The transaction hash is displayed, and you can verify this on the Cronos testnet explorer.
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
> Next, it constructs the x402 payment header, including the recipient address, amount, and network details.
>
> The action shows the payment being submitted through the x402 facilitator on Cronos.
>
> The observation confirms the payment completed with a verified transaction hash.
>
> This is the future of AI-to-service payments: autonomous, instant, and verifiable on-chain.

---

## Scene 6: Conclusion (25 seconds)

> That's Paygent in action.
>
> We demonstrated the complete ReAct cycle: Reasoning, Planning, Action, Observation, and Reflection.
>
> All transactions were executed on the real Cronos testnet, not simulated.
>
> Paygent is built on the DeepAgents framework with integration to the Crypto.com AI Agent SDK and x402 payment protocol.
>
> Thank you for watching. Check out our GitHub repository for more details.

---

## Recording Instructions

1. **Scene 1**: Show the Paygent logo in the header while speaking
2. **Scene 2**: Run "Balance Check" in Live Mode, pause at key moments
3. **Scene 3**: Run "VVS Quote" in Live Mode, highlight the quote data
4. **Scene 4**: Run "VVS Swap" in Live Mode, show the full execution
5. **Scene 5**: Run "x402 Payment" in Live Mode, demonstrate the payment flow
6. **Scene 6**: Show the final completed state with all green checkmarks

## Key Moments to Pause/Highlight

- Reasoning phase (italicized thought process)
- Planning phase (checkbox todos updating)
- Action phase (tool name and arguments)
- Observation phase (balance/quote/swap results)
- Reflection phase (success summary with metrics)
- Task Progress panel (updating in real-time)
- Testnet Logs panel (showing real API calls)

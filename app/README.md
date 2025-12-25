# Vercel Workflow Integration

This directory contains the Vercel Workflow implementation for durable agent execution with human-in-the-loop approvals.

## Overview

The Vercel Workflow integration provides:

- **Durable Execution**: Workflows survive deployments and crashes with deterministic replays
- **Human Approvals**: Pause workflows for user approval and resume after decision
- **Sleep Support**: Wait for hours/days without consuming compute (e.g., subscription renewals)
- **Hook System**: Wait for external events (webhooks, user approvals, x402 settlements)
- **Built-in Observability**: Track runs, trace failures, analyze performance

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Request  │    │    Workflow      │    │   x402 Payment  │
│                 │    │   (TypeScript)   │    │   Step         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Agent         │    │   Approval Hook  │    │   Payment       │
│   Execution     │    │   (awaiting)     │    │   Verification  │
│   (Python)      │    └──────────────────┘    └─────────────────┘
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   User Approval │
│   (Webhook)     │
└─────────────────┘
```

## Workflows

### 1. Agent Payment Workflow (`agent-payment-workflow.ts`)

Handles AI agent payment execution with human approval:

- Parses natural language commands
- Creates execution plans with approval requirements
- Executes steps with retry logic
- Pauses for human approval on sensitive operations
- Resumes after approval decision

**Key Features:**
- Automatic approval detection based on command content
- Step-by-step execution with error handling
- Exponential backoff for retries
- Integration with Python backend

### 2. Subscription Renewal Workflow (`subscription-renewal-workflow.ts`)

Demonstrates long-running operations with sleep support:

- Sleeps for hours/days without consuming compute
- Executes periodic renewals
- Handles payment failures gracefully
- Updates progress and sends notifications

**Key Features:**
- Time-based execution with `sleep()`
- Integration with x402 payment steps
- Failure handling and notifications
- Database progress tracking

## Steps

### x402 Payment Step (`x402-payment.ts`)

Durable x402 payment execution with retries:

- HTTP 402 handling with automatic retry logic
- EIP-712 signature generation
- Settlement verification on Cronos blockchain
- Exponential backoff for failed payments

**Key Features:**
- 5 retry attempts with increasing delays
- Settlement time tracking
- Integration with Python wallet management
- Error handling and logging

## API Endpoints

### Approval Resume (`/api/approvals/[requestId]/approve`)

Handles approval decisions from users:

- **POST**: Resume workflow with approval decision
- **GET**: Check approval request status
- **DELETE**: Cancel pending approval request

**Request Format:**
```json
{
  "decision": "approved|rejected|edited",
  "editedArgs": { /* optional edited parameters */ }
}
```

## Integration with Python Backend

The workflows integrate with the Python FastAPI backend:

- **Environment Variables**:
  - `PYTHON_BACKEND_URL`: URL of the Python API
  - `WORKFLOW_TOKEN`: Authentication token for API calls

- **API Endpoints Used**:
  - `/api/v1/agent/execute-step`: Execute individual steps
  - `/api/v1/payments/status/{txHash}`: Check payment status
  - `/api/v1/wallet/sign-eip712`: Generate EIP-712 signatures
  - `/api/v1/notifications/*`: Send notifications

## Usage

### Starting a Workflow

```typescript
import { agentPaymentWorkflow } from '@/workflows';

// Start agent payment workflow
const result = await agentPaymentWorkflow(
  "Pay 0.10 USDC to access the market data API",
  "session-123"
);
```

### Handling Approvals

1. Workflow creates approval hook with unique token
2. User receives approval request via notification
3. User approves via webhook endpoint
4. Workflow resumes with approval decision

### Sleep Operations

```typescript
// Sleep for 24 hours
await sleep(24 * 60 * 60); // seconds

// Sleep for 30 days
await sleep(30 * 24 * 60 * 60); // seconds
```

## Monitoring and Observability

Vercel provides built-in workflow monitoring:

- **Workflow Runs**: View all workflow executions
- **Step Traces**: See individual step execution
- **Error Analysis**: Debug failed workflows
- **Performance Metrics**: Monitor execution times

## Deployment

The workflows are automatically deployed with the main application:

1. TypeScript files are compiled during build
2. Workflows are registered with Vercel
3. API routes are configured in `vercel.json`
4. Environment variables are configured in Vercel Dashboard

## Development

### Local Testing

1. Install dependencies: `pnpm install`
2. Build workflows: `pnpm run build`
3. Test with local backend: Set `PYTHON_BACKEND_URL` to local server

### Environment Setup

Required environment variables:
- `PYTHON_BACKEND_URL`: URL of Python FastAPI backend
- `WORKFLOW_TOKEN`: Authentication token
- `VERCEL_WORKFLOW_TOKEN`: Vercel workflow token

## Error Handling

The workflows include comprehensive error handling:

- **Retry Logic**: Automatic retries with exponential backoff
- **Timeout Handling**: Fallbacks for approval timeouts
- **Error Propagation**: Clear error messages to users
- **Logging**: Detailed logging for debugging

## Security

- **Authentication**: All API calls require valid tokens
- **Input Validation**: Approval decisions are validated
- **Signature Verification**: EIP-712 signatures for payments
- **Rate Limiting**: Built-in protection against abuse
// app/workflows/agent-payment-workflow.ts
// Durable AI agent workflow with human approval for Vercel Workflow integration

import { defineHook, sleep } from 'workflow';

interface ApprovalEvent {
  decision: 'approved' | 'rejected' | 'edited';
  editedArgs?: Record<string, any>;
}

interface Step {
  id: string;
  name: string;
  requiresApproval: boolean;
  args: Record<string, any>;
}

interface Plan {
  steps: Step[];
}

const approvalHook = defineHook<ApprovalEvent>();

/**
 * Durable agent payment workflow with human approval support
 * This workflow survives deployments and crashes with deterministic replays
 */
export async function agentPaymentWorkflow(command: string, sessionId: string) {
  'use workflow';

  try {
    // Step 1: Parse command and create plan
    const plan: Plan = await parseCommandAndPlan(command);

    // Step 2: Execute each planned step
    for (const step of plan.steps) {
      if (step.requiresApproval) {
        // Wait for human approval (can take minutes/hours without consuming compute)
        const events = approvalHook.create({
          token: `${sessionId}-${step.id}`,
          metadata: {
            stepName: step.name,
            sessionId: sessionId,
            timestamp: new Date().toISOString()
          }
        });

        let approved = false;
        for await (const event of events) {
          if (event.decision === 'approved') {
            await executeStep(step);
            approved = true;
            break;
          } else if (event.decision === 'edited') {
            // Apply user edits to step arguments
            const editedStep = { ...step, args: event.editedArgs };
            await executeStep(editedStep);
            approved = true;
            break;
          } else if (event.decision === 'rejected') {
            throw new Error(`Step rejected by user: ${step.name}`);
          }
        }

        if (!approved) {
          throw new Error(`Approval timeout for step: ${step.name}`);
        }
      } else {
        // Execute step directly without approval
        await executeStep(step);
      }
    }

    return {
      success: true,
      sessionId: sessionId,
      message: 'Workflow completed successfully'
    };

  } catch (error) {
    return {
      success: false,
      sessionId: sessionId,
      error: error.message
    };
  }
}

/**
 * Parse natural language command and create execution plan
 */
async function parseCommandAndPlan(command: string): Promise<Plan> {
  'use step';

  // Determine if approval is needed based on command content and amount
  const needsApproval = command.includes('large') ||
                       command.includes('high-value') ||
                       command.includes('expensive') ||
                       command.includes('$50') ||
                       command.includes('$100') ||
                       command.includes('0.5') ||
                       command.includes('1.0');

  // Create plan based on command type
  if (command.includes('pay') || command.includes('send')) {
    return {
      steps: [
        {
          id: 'parse-payment',
          name: 'Parse payment command',
          requiresApproval: false,
          args: { command }
        },
        {
          id: 'check-balance',
          name: 'Check wallet balance',
          requiresApproval: false,
          args: {}
        },
        {
          id: 'execute-payment',
          name: 'Execute payment',
          requiresApproval: needsApproval,
          args: { command }
        }
      ]
    };
  } else if (command.includes('swap') || command.includes('trade')) {
    return {
      steps: [
        {
          id: 'parse-swap',
          name: 'Parse swap command',
          requiresApproval: false,
          args: { command }
        },
        {
          id: 'get-quote',
          name: 'Get price quote',
          requiresApproval: false,
          args: {}
        },
        {
          id: 'execute-swap',
          name: 'Execute swap',
          requiresApproval: needsApproval,
          args: { command }
        }
      ]
    };
  } else {
    return {
      steps: [
        {
          id: 'parse-command',
          name: 'Parse command',
          requiresApproval: false,
          args: { command }
        }
      ]
    };
  }
}

/**
 * Execute individual step with retry logic
 */
async function executeStep(step: Step): Promise<void> {
  'use step';

  const maxRetries = 3;
  let lastError: Error;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      // Log step execution
      console.log(`Executing step ${step.id}: ${step.name} (attempt ${attempt})`);

      // Simulate step execution - in reality this would call the Python backend
      const result = await executeStepInBackend(step);

      if (result.success) {
        console.log(`Step ${step.id} completed successfully`);
        return;
      } else {
        throw new Error(`Step failed: ${result.error}`);
      }

    } catch (error) {
      lastError = error as Error;
      console.log(`Step ${step.id} failed on attempt ${attempt}: ${error.message}`);

      if (attempt === maxRetries) {
        throw lastError;
      }

      // Exponential backoff
      const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
      await sleep(delay);
    }
  }
}

/**
 * Execute step in the Python backend via API call
 */
async function executeStepInBackend(step: Step): Promise<{ success: boolean; error?: string }> {
  'use step';

  try {
    const response = await fetch(`${process.env.PYTHON_BACKEND_URL}/api/v1/agent/execute-step`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.WORKFLOW_TOKEN}`
      },
      body: JSON.stringify({
        stepId: step.id,
        stepName: step.name,
        args: step.args
      })
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    const result = await response.json();
    return result;

  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}
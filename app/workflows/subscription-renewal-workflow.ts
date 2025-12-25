// app/workflows/subscription-renewal-workflow.ts
// Vercel Workflow with sleep support for long-running operations like subscription renewals

import { sleep } from 'workflow';

interface Subscription {
  id: string;
  userId: string;
  serviceId: string;
  amount: string;
  token: string;
  renewalInterval: number; // days
  nextRenewalDate: string;
  status: 'active' | 'paused' | 'cancelled';
}

interface WorkflowContext {
  subscriptionId: string;
  currentRenewalDate: string;
  renewalCount: number;
  maxRenewals: number;
}

/**
 * Subscription renewal workflow with sleep support
 * Demonstrates how to wait for hours/days without consuming compute
 */
export async function subscriptionRenewalWorkflow(context: WorkflowContext) {
  'use workflow';

  let renewalCount = context.renewalCount || 0;
  let currentRenewalDate = new Date(context.currentRenewalDate);

  try {
    while (renewalCount < context.maxRenewals) {
      // Calculate time until next renewal
      const now = new Date();
      const timeUntilRenewal = currentRenewalDate.getTime() - now.getTime();

      if (timeUntilRenewal > 0) {
        // Sleep until renewal time (can be hours or days)
        console.log(`Sleeping for ${timeUntilRenewal}ms until next renewal at ${currentRenewalDate.toISOString()}`);

        // Convert milliseconds to seconds for sleep function
        const sleepSeconds = Math.floor(timeUntilRenewal / 1000);
        await sleep(sleepSeconds);

        console.log(`Woke up for renewal ${renewalCount + 1}`);
      }

      // Execute renewal payment
      const renewalResult = await executeRenewalPayment(context.subscriptionId);

      if (renewalResult.success) {
        console.log(`Renewal ${renewalCount + 1} successful: ${renewalResult.txHash}`);

        // Update for next renewal
        renewalCount++;
        currentRenewalDate.setDate(currentRenewalDate.getDate() + 30); // Next month

        // Save progress (this would update database)
        await saveRenewalProgress({
          subscriptionId: context.subscriptionId,
          renewalCount,
          nextRenewalDate: currentRenewalDate.toISOString()
        });

      } else {
        console.error(`Renewal ${renewalCount + 1} failed: ${renewalResult.error}`);

        // Handle failed renewal - could trigger notification or retry logic
        await handleRenewalFailure(context.subscriptionId, renewalResult.error);

        // For this example, we'll continue to next renewal
        renewalCount++;
        currentRenewalDate.setDate(currentRenewalDate.getDate() + 30);
      }
    }

    return {
      success: true,
      subscriptionId: context.subscriptionId,
      renewalsCompleted: renewalCount,
      finalRenewalDate: currentRenewalDate.toISOString(),
      message: `All ${context.maxRenewals} renewals completed successfully`
    };

  } catch (error) {
    return {
      success: false,
      subscriptionId: context.subscriptionId,
      renewalsCompleted: renewalCount,
      error: error.message
    };
  }
}

/**
 * Execute single renewal payment
 */
async function executeRenewalPayment(subscriptionId: string) {
  'use step';

  try {
    // Get subscription details from backend
    const response = await fetch(`${process.env.PYTHON_BACKEND_URL}/api/v1/payments/subscription/${subscriptionId}`, {
      headers: {
        'Authorization': `Bearer ${process.env.WORKFLOW_TOKEN}`
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to get subscription: ${response.status}`);
    }

    const subscription: Subscription = await response.json();

    // Execute payment using x402 payment step
    const { executeX402Payment } = await import('@/steps/x402-payment');

    const paymentResult = await executeX402Payment({
      serviceUrl: subscription.serviceId,
      amount: subscription.amount,
      token: subscription.token,
      recipient: subscription.serviceId,
      sessionId: `renewal-${subscriptionId}-${Date.now()}`
    });

    if (paymentResult.success) {
      // Mark renewal as successful
      await markRenewalSuccessful(subscriptionId, paymentResult.txHash);

      return {
        success: true,
        txHash: paymentResult.txHash,
        settlementTime: paymentResult.settlementTime
      };
    } else {
      throw new Error(paymentResult.error);
    }

  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Save renewal progress to database
 */
async function saveRenewalProgress(progress: {
  subscriptionId: string;
  renewalCount: number;
  nextRenewalDate: string;
}) {
  'use step';

  const response = await fetch(`${process.env.PYTHON_BACKEND_URL}/api/v1/payments/subscription/progress`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.WORKFLOW_TOKEN}`
    },
    body: JSON.stringify(progress)
  });

  if (!response.ok) {
    throw new Error(`Failed to save progress: ${response.status}`);
  }
}

/**
 * Handle renewal failure
 */
async function handleRenewalFailure(subscriptionId: string, error: string) {
  'use step';

  // Send notification to user
  await sendRenewalFailureNotification(subscriptionId, error);

  // Log failure for monitoring
  console.error(`Renewal failure for subscription ${subscriptionId}: ${error}`);
}

/**
 * Mark renewal as successful in database
 */
async function markRenewalSuccessful(subscriptionId: string, txHash: string) {
  'use step';

  const response = await fetch(`${process.env.PYTHON_BACKEND_URL}/api/v1/payments/subscription/${subscriptionId}/success`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.WORKFLOW_TOKEN}`
    },
    body: JSON.stringify({
      txHash,
      renewalDate: new Date().toISOString()
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to mark renewal successful: ${response.status}`);
  }
}

/**
 * Send notification about renewal failure
 */
async function sendRenewalFailureNotification(subscriptionId: string, error: string) {
  'use step';

  const response = await fetch(`${process.env.PYTHON_BACKEND_URL}/api/v1/notifications/renewal-failure`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.WORKFLOW_TOKEN}`
    },
    body: JSON.stringify({
      subscriptionId,
      error,
      timestamp: new Date().toISOString()
    })
  });

  if (!response.ok) {
    console.error(`Failed to send notification: ${response.status}`);
  }
}
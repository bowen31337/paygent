// app/steps/x402-payment.ts
// Durable x402 payment step with retries for Vercel Workflow integration

interface PaymentRequest {
  serviceUrl: string;
  amount: string;
  token: string;
  recipient: string;
  sessionId: string;
}

interface PaymentResult {
  success: boolean;
  txHash?: string;
  error?: string;
  settlementTime?: number;
}

/**
 * Execute x402 payment with retry logic and durability
 * Each execution is a durable step that can be retried
 */
export async function executeX402Payment(paymentRequest: PaymentRequest): Promise<PaymentResult> {
  'use step';

  const maxRetries = 5;
  const initialDelay = 1000; // 1 second
  let lastError: string;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`x402 payment attempt ${attempt}/${maxRetries} for ${paymentRequest.amount} ${paymentRequest.token}`);

      // Make payment request to the service
      const response = await fetch(paymentRequest.serviceUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.PAYMENT_TOKEN}`
        },
        body: JSON.stringify({
          amount: paymentRequest.amount,
          token: paymentRequest.token,
          recipient: paymentRequest.recipient,
          sessionId: paymentRequest.sessionId
        })
      });

      if (response.status === 402) {
        // HTTP 402 - Payment Required, need to handle x402 payment
        const paymentData = await response.json();

        // Execute x402 payment flow
        const paymentResult = await processX402Payment(paymentData);

        if (paymentResult.success) {
          // Verify settlement
          const settlementResult = await verifySettlement(paymentResult.txHash);

          if (settlementResult.success) {
            console.log(`x402 payment successful: ${paymentResult.txHash}`);
            return {
              success: true,
              txHash: paymentResult.txHash,
              settlementTime: settlementResult.settlementTime
            };
          } else {
            throw new Error(`Settlement verification failed: ${settlementResult.error}`);
          }
        } else {
          throw new Error(`x402 payment failed: ${paymentResult.error}`);
        }
      } else if (response.ok) {
        // Payment not required, return success
        const data = await response.json();
        console.log('Service processed without payment');
        return {
          success: true,
          txHash: data.txHash,
          settlementTime: 0
        };
      } else {
        throw new Error(`Service error: ${response.status} ${response.statusText}`);
      }

    } catch (error) {
      lastError = error.message;
      console.log(`x402 payment attempt ${attempt} failed: ${error.message}`);

      if (attempt === maxRetries) {
        break;
      }

      // Calculate delay with exponential backoff
      const delay = Math.min(initialDelay * Math.pow(2, attempt - 1), 30000); // Max 30 seconds

      console.log(`Waiting ${delay}ms before retry...`);
      await sleep(delay);
    }
  }

  return {
    success: false,
    error: `Payment failed after ${maxRetries} attempts. Last error: ${lastError}`
  };
}

/**
 * Process x402 payment flow with EIP-712 signatures
 */
async function processX402Payment(paymentData: any): Promise<{ success: boolean; txHash?: string; error?: string }> {
  'use step';

  try {
    // Extract payment details from 402 response
    const { amount, token, recipient, paymentUrl } = paymentData;

    // Generate EIP-712 signature for payment
    const signature = await generateEIP712Signature(paymentData);

    // Submit payment with signature
    const paymentResponse = await fetch(paymentUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        signature,
        amount,
        token,
        recipient
      })
    });

    if (!paymentResponse.ok) {
      throw new Error(`Payment submission failed: ${paymentResponse.status}`);
    }

    const result = await paymentResponse.json();
    return {
      success: true,
      txHash: result.txHash
    };

  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Generate EIP-712 signature for x402 payment authorization
 */
async function generateEIP712Signature(paymentData: any): Promise<string> {
  'use step';

  // In a real implementation, this would use the wallet private key
  // For Vercel Workflow, this would be handled by the backend
  const signatureResponse = await fetch(`${process.env.PYTHON_BACKEND_URL}/api/v1/wallet/sign-eip712`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.WORKFLOW_TOKEN}`
    },
    body: JSON.stringify({
      domain: paymentData.domain,
      types: paymentData.types,
      message: paymentData.message
    })
  });

  if (!signatureResponse.ok) {
    throw new Error(`Signature generation failed: ${signatureResponse.status}`);
  }

  const result = await signatureResponse.json();
  return result.signature;
}

/**
 * Verify payment settlement on Cronos blockchain
 */
async function verifySettlement(txHash: string): Promise<{ success: boolean; settlementTime?: number; error?: string }> {
  'use step';

  const startTime = Date.now();

  try {
    // Poll for transaction confirmation
    const maxAttempts = 60; // 60 seconds max wait
    const pollInterval = 1000; // 1 second intervals

    for (let i = 0; i < maxAttempts; i++) {
      const response = await fetch(`${process.env.PYTHON_BACKEND_URL}/api/v1/payments/status/${txHash}`, {
        headers: {
          'Authorization': `Bearer ${process.env.WORKFLOW_TOKEN}`
        }
      });

      if (!response.ok) {
        throw new Error(`Status check failed: ${response.status}`);
      }

      const status = await response.json();

      if (status.confirmed) {
        const settlementTime = Date.now() - startTime;
        return {
          success: true,
          settlementTime
        };
      }

      if (status.failed) {
        return {
          success: false,
          error: 'Transaction failed'
        };
      }

      // Wait before next poll
      await sleep(pollInterval);
    }

    return {
      success: false,
      error: 'Settlement timeout'
    };

  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}
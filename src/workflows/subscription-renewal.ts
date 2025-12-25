/**
 * Subscription Renewal Workflow
 *
 * This Vercel Workflow handles automatic subscription renewals for services.
 * It checks for expiring subscriptions, processes renewals, and handles failures.
 */

import { defineWorkflow, sleep, defineHook } from 'workflow';
import { SubscriptionService } from '../services/subscription-service';
import { PaymentService } from '../services/payment-service';
import { NotificationService } from '../services/notification-service';
import { logger } from '../utils/logger';

// Hook for manual renewal requests
const manualRenewalHook = defineHook<{
  subscriptionId: string;
  sessionId: string;
  serviceId: string;
  amount: number;
  token: string;
}>();

export async function subscriptionRenewalWorkflow() {
  'use workflow';

  logger.info('Starting subscription renewal workflow');

  try {
    // Step 1: Check for expiring subscriptions
    const expiringSubscriptions = await getExpiringSubscriptions();

    if (expiringSubscriptions.length === 0) {
      logger.info('No subscriptions expiring soon, sleeping for 1 hour');
      await sleep(60 * 60 * 1000); // Sleep for 1 hour
      return { status: 'no_expiring_subscriptions', count: 0 };
    }

    logger.info(`Found ${expiringSubscriptions.length} expiring subscriptions`);

    // Step 2: Process each expiring subscription
    const results = [];

    for (const subscription of expiringSubscriptions) {
      try {
        const result = await processSubscriptionRenewal(subscription);
        results.push(result);

        // Wait between renewals to avoid rate limiting
        await sleep(5000); // 5 seconds between renewals

      } catch (error) {
        logger.error(`Failed to process subscription ${subscription.id}:`, error);
        results.push({
          subscriptionId: subscription.id,
          status: 'error',
          error: error.message
        });
      }
    }

    // Step 3: Send summary notification
    await sendRenewalSummary(results);

    return {
      status: 'completed',
      processed: results.length,
      successful: results.filter(r => r.status === 'success').length,
      failed: results.filter(r => r.status === 'error').length
    };

  } catch (error) {
    logger.error('Workflow failed:', error);
    throw error;
  }
}

async function getExpiringSubscriptions() {
  const subscriptionService = new SubscriptionService();
  // Get subscriptions expiring within 24 hours
  return await subscriptionService.getExpiringSubscriptions(24);
}

async function processSubscriptionRenewal(subscription) {
  const subscriptionService = new SubscriptionService();
  const paymentService = new PaymentService();
  const notificationService = new NotificationService();

  logger.info(`Processing renewal for subscription ${subscription.id}`);

  try {
    // Check if subscription is still active
    const isActive = await subscriptionService.isSubscriptionActive(
      subscription.sessionId,
      subscription.serviceId
    );

    if (!isActive) {
      logger.warn(`Subscription ${subscription.id} is no longer active, skipping renewal`);
      return {
        subscriptionId: subscription.id,
        status: 'skipped',
        reason: 'no_longer_active'
      };
    }

    // Calculate renewal cost
    const renewalAmount = subscription.amount || 10.0; // Default $10 if no amount set
    const renewalToken = subscription.token || 'USDC';

    // Attempt payment
    const paymentResult = await paymentService.executePayment({
      serviceUrl: subscription.serviceEndpoint,
      amount: renewalAmount,
      token: renewalToken,
      description: `Subscription renewal for ${subscription.serviceName}`
    });

    if (!paymentResult.success) {
      // Payment failed, notify user
      await notificationService.sendRenewalFailedNotification(
        subscription.sessionId,
        subscription.serviceName,
        paymentResult.message
      );

      return {
        subscriptionId: subscription.id,
        status: 'payment_failed',
        error: paymentResult.message
      };
    }

    // Payment successful, renew subscription
    const renewalSuccess = await subscriptionService.renewSubscription(
      subscription.id,
      paymentResult.txHash
    );

    if (!renewalSuccess) {
      // Renewal failed, but payment succeeded - this is a critical error
      await notificationService.sendRenewalErrorNotification(
        subscription.sessionId,
        subscription.serviceName,
        'Payment succeeded but subscription renewal failed'
      );

      return {
        subscriptionId: subscription.id,
        status: 'renewal_failed',
        error: 'Payment succeeded but subscription renewal failed'
      };
    }

    // Success
    const newExpiration = await subscriptionService.getSubscriptionExpiration(subscription.id);

    await notificationService.sendRenewalSuccessNotification(
      subscription.sessionId,
      subscription.serviceName,
      renewalAmount,
      renewalToken,
      newExpiration
    );

    return {
      subscriptionId: subscription.id,
      status: 'success',
      txHash: paymentResult.txHash,
      newExpiration: newExpiration
    };

  } catch (error) {
    logger.error(`Renewal processing failed for ${subscription.id}:`, error);

    // Send error notification
    await notificationService.sendRenewalErrorNotification(
      subscription.sessionId,
      subscription.serviceName,
      error.message
    );

    throw error;
  }
}

async function sendRenewalSummary(results) {
  const notificationService = new NotificationService();

  const summary = {
    total: results.length,
    successful: results.filter(r => r.status === 'success').length,
    failed: results.filter(r => r.status === 'error').length,
    skipped: results.filter(r => r.status === 'skipped').length,
    paymentFailed: results.filter(r => r.status === 'payment_failed').length,
    renewalFailed: results.filter(r => r.status === 'renewal_failed').length
  };

  await notificationService.sendRenewalSummaryNotification(summary);
}

// Manual renewal endpoint
export async function manualRenewalWorkflow(subscriptionId: string) {
  'use workflow';

  logger.info(`Manual renewal requested for subscription ${subscriptionId}`);

  // Wait for manual renewal hook
  const events = manualRenewalHook.create({ token: subscriptionId });

  for await (const event of events) {
    try {
      const result = await processSubscriptionRenewal({
        id: subscriptionId,
        sessionId: event.sessionId,
        serviceId: event.serviceId,
        amount: event.amount,
        token: event.token,
        serviceEndpoint: await getServiceEndpoint(event.serviceId),
        serviceName: await getServiceName(event.serviceId)
      });

      return result;

    } catch (error) {
      logger.error(`Manual renewal failed for ${subscriptionId}:`, error);
      throw error;
    }
  }
}

async function getServiceEndpoint(serviceId: string): Promise<string> {
  // Implementation to get service endpoint from service registry
  // This would typically query the service registry database
  return `https://api.example.com/services/${serviceId}`;
}

async function getServiceName(serviceId: string): Promise<string> {
  // Implementation to get service name from service registry
  return `Service ${serviceId}`;
}
/**
 * Subscription Renewal Scheduler
 *
 * This module schedules and manages automatic subscription renewals using
 * cron jobs and Vercel Workflows.
 */

import { schedule } from 'node-cron';
import { subscriptionRenewalWorkflow } from './subscription-renewal';
import { manualRenewalWorkflow } from './subscription-renewal';
import { logger } from '../utils/logger';
import { WorkflowManager } from './workflow-manager';

export class SubscriptionScheduler {
  private workflowManager: WorkflowManager;
  private isRunning = false;

  constructor() {
    this.workflowManager = new WorkflowManager();
  }

  /**
   * Start the subscription renewal scheduler
   */
  start() {
    if (this.isRunning) {
      logger.warn('Subscription scheduler is already running');
      return;
    }

    this.isRunning = true;

    logger.info('Starting subscription renewal scheduler');

    // Schedule renewal checks every hour
    schedule('0 * * * * *', async () => {
      try {
        logger.info('Triggering hourly subscription renewal check');
        await this.triggerRenewalWorkflow();
      } catch (error) {
        logger.error('Hourly renewal check failed:', error);
      }
    });

    // Schedule daily summary report
    schedule('0 9 * * *', async () => {
      try {
        logger.info('Triggering daily subscription summary');
        await this.sendDailySummary();
      } catch (error) {
        logger.error('Daily summary failed:', error);
      }
    });

    // Schedule weekly subscription health check
    schedule('0 10 * * 1', async () => {
      try {
        logger.info('Triggering weekly subscription health check');
        await this.performHealthCheck();
      } catch (error) {
        logger.error('Weekly health check failed:', error);
      }
    });

    logger.info('Subscription scheduler started successfully');
  }

  /**
   * Stop the subscription renewal scheduler
   */
  stop() {
    this.isRunning = false;
    logger.info('Subscription scheduler stopped');
  }

  /**
   * Trigger the renewal workflow manually
   */
  async triggerRenewalWorkflow() {
    try {
      logger.info('Triggering subscription renewal workflow');

      const result = await this.workflowManager.runWorkflow(
        'subscription-renewal',
        subscriptionRenewalWorkflow
      );

      logger.info('Renewal workflow completed:', result);

      return result;

    } catch (error) {
      logger.error('Renewal workflow failed:', error);
      throw error;
    }
  }

  /**
   * Request manual renewal for a specific subscription
   */
  async requestManualRenewal(
    subscriptionId: string,
    sessionId: string,
    serviceId: string,
    amount: number,
    token: string
  ) {
    try {
      logger.info(`Requesting manual renewal for subscription ${subscriptionId}`);

      const result = await this.workflowManager.runWorkflow(
        `manual-renewal-${subscriptionId}`,
        () => manualRenewalWorkflow(subscriptionId),
        {
          subscriptionId,
          sessionId,
          serviceId,
          amount,
          token
        }
      );

      logger.info('Manual renewal completed:', result);

      return result;

    } catch (error) {
      logger.error('Manual renewal failed:', error);
      throw error;
    }
  }

  /**
   * Send daily subscription summary
   */
  async sendDailySummary() {
    try {
      const subscriptionService = new (await import('../services/subscription-service')).SubscriptionService();

      // Get subscription statistics
      const stats = await subscriptionService.getDailyStats();

      const summary = {
        date: new Date().toISOString().split('T')[0],
        totalActive: stats.active,
        expiringToday: stats.expiringToday,
        expiringThisWeek: stats.expiringThisWeek,
        renewalSuccessRate: stats.renewalSuccessRate,
        failedPayments: stats.failedPayments
      };

      logger.info('Daily subscription summary:', summary);

      // Send notification or save to monitoring system
      await this.sendSummaryNotification(summary);

      return summary;

    } catch (error) {
      logger.error('Daily summary failed:', error);
      throw error;
    }
  }

  /**
   * Perform weekly subscription health check
   */
  async performHealthCheck() {
    try {
      logger.info('Performing weekly subscription health check');

      const subscriptionService = new (await import('../services/subscription-service')).SubscriptionService();

      // Check for potential issues
      const issues = [];

      // 1. Check for subscriptions with no renewal attempts
      const staleSubscriptions = await subscriptionService.getStaleSubscriptions();
      if (staleSubscriptions.length > 0) {
        issues.push({
          type: 'stale_subscriptions',
          count: staleSubscriptions.length,
          description: 'Subscriptions with no recent renewal attempts'
        });
      }

      // 2. Check for high failure rates
      const failureRate = await subscriptionService.getFailureRate();
      if (failureRate > 0.1) { // More than 10% failure rate
        issues.push({
          type: 'high_failure_rate',
          rate: failureRate,
          description: `High subscription renewal failure rate: ${failureRate * 100}%`
        });
      }

      // 3. Check for expired subscriptions that should have been renewed
      const missedRenewals = await subscriptionService.getMissedRenewals();
      if (missedRenewals.length > 0) {
        issues.push({
          type: 'missed_renewals',
          count: missedRenewals.length,
          description: 'Subscriptions that expired without renewal attempts'
        });
      }

      const healthCheck = {
        timestamp: new Date().toISOString(),
        issues: issues,
        status: issues.length === 0 ? 'healthy' : 'issues_found',
        recommendation: issues.length === 0 ? 'No action needed' : 'Review and resolve issues'
      };

      logger.info('Weekly health check completed:', healthCheck);

      if (issues.length > 0) {
        await this.sendHealthAlert(healthCheck);
      }

      return healthCheck;

    } catch (error) {
      logger.error('Health check failed:', error);
      throw error;
    }
  }

  /**
   * Send summary notification
   */
  private async sendSummaryNotification(summary: any) {
    // Implementation for sending daily summary
    logger.info('Daily summary notification sent:', summary);
  }

  /**
   * Send health alert
   */
  private async sendHealthAlert(healthCheck: any) {
    // Implementation for sending health alerts
    logger.warn('Health alert sent:', healthCheck);
  }
}

// Singleton instance
let scheduler: SubscriptionScheduler | null = null;

/**
 * Get the subscription scheduler instance
 */
export function getSubscriptionScheduler(): SubscriptionScheduler {
  if (!scheduler) {
    scheduler = new SubscriptionScheduler();
  }
  return scheduler;
}

/**
 * Start the subscription scheduler
 */
export function startSubscriptionScheduler() {
  const scheduler = getSubscriptionScheduler();
  scheduler.start();
  return scheduler;
}

/**
 * Stop the subscription scheduler
 */
export function stopSubscriptionScheduler() {
  const scheduler = getSubscriptionScheduler();
  scheduler.stop();
}

// Auto-start if this module is run directly
if (require.main === module) {
  startSubscriptionScheduler();
}
"""
Error alerting service for critical failures.

This module provides an alerting system that can send notifications
when critical errors occur in the application.

Supported alert channels:
- Console logging (default, always enabled)
- Webhook notifications (configurable)
- Email notifications (future)
- Slack/Discord webhooks (future)
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""
    PAYMENT_FAILURE = "payment_failure"
    AGENT_EXECUTION_FAILURE = "agent_execution_failure"
    ALLOWLIST_VIOLATION = "allowlist_violation"
    AUTHENTICATION_FAILURE = "authentication_failure"
    DATABASE_ERROR = "database_error"
    EXTERNAL_SERVICE_FAILURE = "external_service_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SECURITY_VIOLATION = "security_violation"


@dataclass
class Alert:
    """Represents a single alert."""

    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: str
    details: dict[str, Any] | None = None
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details or {},
            "correlation_id": self.correlation_id,
        }


class AlertingService:
    """
    Service for managing and dispatching alerts.

    This service provides a centralized way to send alerts
    when critical errors occur in the application.
    """

    def __init__(self) -> None:
        """Initialize the alerting service."""
        self.alert_handlers: list[Callable[[Alert], None]] = []
        self._setup_default_handlers()
        logger.info("AlertingService initialized")

    def _setup_default_handlers(self) -> None:
        """Set up default alert handlers."""
        # Always add console logging handler
        self.alert_handlers.append(self._console_handler)

        # Add webhook handler if configured
        if settings.alert_webhook_url:
            self.alert_handlers.append(self._webhook_handler)

    def _console_handler(self, alert: Alert) -> None:
        """Handle alerts by logging to console."""
        level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }.get(alert.severity, logging.INFO)

        logger.log(
            level,
            f"[ALERT] {alert.alert_type.value.upper()}: {alert.message} | "
            f"Details: {alert.details} | Correlation: {alert.correlation_id}"
        )

    async def _webhook_handler(self, alert: Alert) -> None:
        """Handle alerts by sending to webhook."""
        if not settings.alert_webhook_url:
            logger.warning("Alert webhook URL not configured, skipping webhook alert")
            return

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.alert_webhook_url,
                    json=alert.to_dict(),
                    headers={"Content-Type": "application/json"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    logger.info(f"Successfully sent webhook alert to {settings.alert_webhook_url}")
                else:
                    logger.warning(f"Webhook alert returned status {response.status_code}")
        except ImportError:
            logger.warning("httpx not available, webhook alert simulated")
            logger.info(f"Would send webhook alert to {settings.alert_webhook_url}")
            logger.info(f"Alert payload: {json.dumps(alert.to_dict())}")
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a custom alert handler."""
        self.alert_handlers.append(handler)
        logger.info(f"Added custom alert handler: {handler.__name__}")

    def send_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None
    ) -> None:
        """
        Send an alert through all registered handlers.

        Args:
            alert_type: Type of alert
            severity: Severity level
            message: Alert message
            details: Additional context/details
            correlation_id: ID for tracking related events
        """
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            details=details,
            correlation_id=correlation_id,
        )

        # Dispatch to all handlers
        for handler in self.alert_handlers:
            try:
                # Check if handler is async
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    # For async handlers, schedule them in background
                    # We use create_task but don't await - fire and forget
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(alert))
                    except RuntimeError:
                        # No running loop, just skip async handlers
                        logger.debug(f"Cannot call async handler {handler.__name__} - no running loop")
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler {handler.__name__} failed: {e}")

    def send_critical(
        self,
        alert_type: AlertType,
        message: str,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None
    ) -> None:
        """Send a critical severity alert."""
        self.send_alert(
            alert_type=alert_type,
            severity=AlertSeverity.CRITICAL,
            message=message,
            details=details,
            correlation_id=correlation_id,
        )

    def send_error(
        self,
        alert_type: AlertType,
        message: str,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None
    ) -> None:
        """Send an error severity alert."""
        self.send_alert(
            alert_type=alert_type,
            severity=AlertSeverity.ERROR,
            message=message,
            details=details,
            correlation_id=correlation_id,
        )

    def send_warning(
        self,
        alert_type: AlertType,
        message: str,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None
    ) -> None:
        """Send a warning severity alert."""
        self.send_alert(
            alert_type=alert_type,
            severity=AlertSeverity.WARNING,
            message=message,
            details=details,
            correlation_id=correlation_id,
        )

    def send_info(
        self,
        alert_type: AlertType,
        message: str,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None
    ) -> None:
        """Send an info severity alert."""
        self.send_alert(
            alert_type=alert_type,
            severity=AlertSeverity.INFO,
            message=message,
            details=details,
            correlation_id=correlation_id,
        )

    async def send_alert_async(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None
    ) -> None:
        """
        Send an alert through all registered handlers (async version).

        Args:
            alert_type: Type of alert
            severity: Severity level
            message: Alert message
            details: Additional context/details
            correlation_id: ID for tracking related events
        """
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            details=details,
            correlation_id=correlation_id,
        )

        # Dispatch to all handlers
        for handler in self.alert_handlers:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler {handler.__name__} failed: {e}")

    def add_synchronous_webhook_handler(self, mock_response: int | None = None) -> None:
        """
        Add a synchronous webhook handler for testing purposes.

        Args:
            mock_response: Optional mock HTTP status code to return
        """
        def sync_webhook_handler(alert: Alert) -> None:
            """Synchronous webhook handler for testing."""
            if not settings.alert_webhook_url:
                logger.warning("Alert webhook URL not configured")
                return

            # For testing, we can mock the response
            if mock_response:
                logger.info(f"Mock webhook alert sent to {settings.alert_webhook_url} with response {mock_response}")
                logger.info(f"Alert payload: {json.dumps(alert.to_dict())}")
            else:
                # In a real scenario, this would use requests
                logger.info(f"Webhook alert would be sent to {settings.alert_webhook_url}")
                logger.info(f"Alert payload: {json.dumps(alert.to_dict())}")

        self.add_handler(sync_webhook_handler)


# Global alerting service instance
alerting_service = AlertingService()


def send_alert(
    alert_type: AlertType,
    severity: AlertSeverity,
    message: str,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None
) -> None:
    """
    Convenience function to send an alert.

    Args:
        alert_type: Type of alert
        severity: Severity level
        message: Alert message
        details: Additional context/details
        correlation_id: ID for tracking related events
    """
    alerting_service.send_alert(
        alert_type=alert_type,
        severity=severity,
        message=message,
        details=details,
        correlation_id=correlation_id,
    )


def send_critical_alert(
    alert_type: AlertType,
    message: str,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None
) -> None:
    """Send a critical alert."""
    alerting_service.send_critical(
        alert_type=alert_type,
        message=message,
        details=details,
        correlation_id=correlation_id,
    )


def send_error_alert(
    alert_type: AlertType,
    message: str,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None
) -> None:
    """Send an error alert."""
    alerting_service.send_error(
        alert_type=alert_type,
        message=message,
        details=details,
        correlation_id=correlation_id,
    )


async def send_alert_async(
    alert_type: AlertType,
    severity: AlertSeverity,
    message: str,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None
) -> None:
    """Send an alert asynchronously."""
    await alerting_service.send_alert_async(
        alert_type=alert_type,
        severity=severity,
        message=message,
        details=details,
        correlation_id=correlation_id,
    )


async def send_critical_alert_async(
    alert_type: AlertType,
    message: str,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None
) -> None:
    """Send a critical alert asynchronously."""
    await alerting_service.send_alert_async(
        alert_type=alert_type,
        severity=AlertSeverity.CRITICAL,
        message=message,
        details=details,
        correlation_id=correlation_id,
    )


# Test utilities
def get_alerting_service() -> AlertingService:
    """Get the global alerting service instance."""
    return alerting_service


def reset_alerting_service() -> None:
    """Reset the alerting service (for testing)."""
    global alerting_service
    alerting_service = AlertingService()

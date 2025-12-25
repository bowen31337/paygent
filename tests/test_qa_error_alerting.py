"""
QA Integration Tests for Error Alerting on Critical Failures.

This test verifies that the error alerting system:
1. Can be configured with a webhook URL
2. Triggers alerts on critical error conditions
3. Calls the webhook handler when configured
4. Includes error details in alert payloads
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from src.main import app
from src.core.database import get_db
from src.services.alerting_service import (
    AlertingService,
    AlertType,
    AlertSeverity,
    Alert,
    alerting_service,
    send_critical_alert,
    reset_alerting_service,
    get_alerting_service,
)
from src.core.errors import general_exception_handler
from src.core.config import settings


class TestAlertingServiceConfiguration:
    """Test that alerting service can be properly configured."""

    def test_alerting_service_initialization(self):
        """Verify alerting service initializes with default handlers."""
        service = AlertingService()

        # Should have at least console handler
        assert len(service.alert_handlers) >= 1

        # Console handler should always be present
        assert service._console_handler in service.alert_handlers

    def test_webhook_handler_added_when_url_configured(self):
        """Verify webhook handler is added when webhook URL is configured."""
        original_url = settings.alert_webhook_url

        try:
            # Set webhook URL
            settings.alert_webhook_url = "https://example.com/webhook"

            service = AlertingService()

            # Should have console + webhook handlers
            assert len(service.alert_handlers) >= 2
            assert service._webhook_handler in service.alert_handlers
        finally:
            settings.alert_webhook_url = original_url

    def test_webhook_handler_not_added_when_url_not_configured(self):
        """Verify webhook handler is not added when no URL is configured."""
        original_url = settings.alert_webhook_url

        try:
            # Clear webhook URL
            settings.alert_webhook_url = None

            service = AlertingService()

            # Should only have console handler
            assert len(service.alert_handlers) == 1
            assert service._webhook_handler not in service.alert_handlers
        finally:
            settings.alert_webhook_url = original_url


class TestAlertCreation:
    """Test that alerts are properly created with correct structure."""

    def test_alert_to_dict(self):
        """Verify alert converts to dictionary correctly."""
        alert = Alert(
            alert_type=AlertType.PAYMENT_FAILURE,
            severity=AlertSeverity.CRITICAL,
            message="Payment failed",
            timestamp="2024-01-01T00:00:00",
            details={"amount": 100, "currency": "USDC"},
            correlation_id="test-123"
        )

        alert_dict = alert.to_dict()

        assert alert_dict["alert_type"] == "payment_failure"
        assert alert_dict["severity"] == "critical"
        assert alert_dict["message"] == "Payment failed"
        assert alert_dict["timestamp"] == "2024-01-01T00:00:00"
        assert alert_dict["details"] == {"amount": 100, "currency": "USDC"}
        assert alert_dict["correlation_id"] == "test-123"

    def test_alert_with_no_details(self):
        """Verify alert works without optional details."""
        alert = Alert(
            alert_type=AlertType.DATABASE_ERROR,
            severity=AlertSeverity.ERROR,
            message="Database error",
            timestamp="2024-01-01T00:00:00"
        )

        alert_dict = alert.to_dict()

        assert alert_dict["details"] == {}
        assert alert_dict["correlation_id"] is None


class TestAlertHandlers:
    """Test that alert handlers work correctly."""

    def test_console_handler_logs_correctly(self, caplog):
        """Verify console handler logs alerts properly."""
        service = AlertingService()

        alert = Alert(
            alert_type=AlertType.PAYMENT_FAILURE,
            severity=AlertSeverity.CRITICAL,
            message="Test alert",
            timestamp="2024-01-01T00:00:00",
            details={"test": "value"},
            correlation_id="test-123"
        )

        service._console_handler(alert)

        # Check that log was created
        assert "[ALERT]" in caplog.text
        assert "PAYMENT_FAILURE" in caplog.text
        assert "Test alert" in caplog.text

    def test_custom_handler_can_be_added(self):
        """Verify custom handlers can be added to service."""
        service = AlertingService()
        initial_count = len(service.alert_handlers)

        captured_alerts = []

        def custom_handler(alert: Alert):
            captured_alerts.append(alert)

        service.add_handler(custom_handler)

        assert len(service.alert_handlers) == initial_count + 1

        # Test that handler is called
        test_alert = Alert(
            alert_type=AlertType.DATABASE_ERROR,
            severity=AlertSeverity.INFO,
            message="Test",
            timestamp="2024-01-01T00:00:00"
        )
        service.send_alert(
            alert_type=AlertType.DATABASE_ERROR,
            severity=AlertSeverity.INFO,
            message="Test"
        )

        # Handler should have been called (via send_alert)
        assert len(captured_alerts) == 1

    def test_synchronous_webhook_handler(self, caplog):
        """Verify synchronous webhook handler for testing."""
        original_url = settings.alert_webhook_url

        try:
            settings.alert_webhook_url = "https://example.com/webhook"

            service = AlertingService()
            service.add_synchronous_webhook_handler(mock_response=200)

            # Send an alert
            service.send_alert(
                alert_type=AlertType.PAYMENT_FAILURE,
                severity=AlertSeverity.CRITICAL,
                message="Test payment failure",
                details={"amount": 100}
            )

            # Check logs
            assert "Mock webhook alert sent" in caplog.text
            assert "https://example.com/webhook" in caplog.text
        finally:
            settings.alert_webhook_url = original_url


class TestAlertSending:
    """Test sending alerts through the service."""

    def test_send_critical_alert(self, caplog):
        """Verify critical alert is sent correctly."""
        reset_alerting_service()
        service = get_alerting_service()

        # Add a capture handler
        captured = []
        def capture(alert: Alert):
            captured.append(alert)
        service.add_handler(capture)

        send_critical_alert(
            alert_type=AlertType.EXTERNAL_SERVICE_FAILURE,
            message="External service failed",
            details={"service": "redis"},
            correlation_id="req-123"
        )

        assert len(captured) == 1
        assert captured[0].severity == AlertSeverity.CRITICAL
        assert captured[0].alert_type == AlertType.EXTERNAL_SERVICE_FAILURE
        assert captured[0].message == "External service failed"
        assert captured[0].details == {"service": "redis"}
        assert captured[0].correlation_id == "req-123"

    @pytest.mark.asyncio
    async def test_send_alert_async(self):
        """Verify async alert sending works."""
        service = AlertingService()

        captured = []
        def capture(alert: Alert):
            captured.append(alert)
        service.add_handler(capture)

        await service.send_alert_async(
            alert_type=AlertType.DATABASE_ERROR,
            severity=AlertSeverity.CRITICAL,
            message="Async test alert"
        )

        assert len(captured) == 1
        assert captured[0].message == "Async test alert"

    def test_alert_with_no_webhook_url(self, caplog):
        """Verify alerting works gracefully without webhook URL."""
        original_url = settings.alert_webhook_url

        try:
            settings.alert_webhook_url = None
            reset_alerting_service()

            service = get_alerting_service()

            # Should only have console handler
            assert len(service.alert_handlers) == 1

            # Send alert - should not crash
            service.send_alert(
                alert_type=AlertType.DATABASE_ERROR,
                severity=AlertSeverity.INFO,
                message="Test"
            )
        finally:
            settings.alert_webhook_url = original_url
            reset_alerting_service()


class TestWebhookHandler:
    """Test the webhook handler functionality."""

    @pytest.mark.asyncio
    async def test_webhook_handler_with_url(self, caplog):
        """Verify webhook handler sends to configured URL."""
        original_url = settings.alert_webhook_url

        try:
            settings.alert_webhook_url = "https://example.com/webhook"

            service = AlertingService()

            alert = Alert(
                alert_type=AlertType.PAYMENT_FAILURE,
                severity=AlertSeverity.CRITICAL,
                message="Test",
                timestamp="2024-01-01T00:00:00"
            )

            # Call webhook handler (it will log since httpx might not be available)
            await service._webhook_handler(alert)

            # Should log about sending
            assert "webhook alert" in caplog.text.lower()
        finally:
            settings.alert_webhook_url = original_url

    @pytest.mark.asyncio
    async def test_webhook_handler_without_url(self, caplog):
        """Verify webhook handler skips when no URL configured."""
        original_url = settings.alert_webhook_url

        try:
            settings.alert_webhook_url = None

            service = AlertingService()

            alert = Alert(
                alert_type=AlertType.DATABASE_ERROR,
                severity=AlertSeverity.INFO,
                message="Test",
                timestamp="2024-01-01T00:00:00"
            )

            await service._webhook_handler(alert)

            # Should warn about missing URL
            assert "not configured" in caplog.text
        finally:
            settings.alert_webhook_url = original_url


class TestIntegrationWithExceptionHandler:
    """Test that error handlers trigger alerts correctly."""

    @pytest.mark.asyncio
    async def test_general_exception_handler_sends_alert(self, caplog):
        """Verify general exception handler sends critical alert."""
        from fastapi.requests import Request
        from unittest.mock import Mock

        # Configure webhook URL
        original_url = settings.alert_webhook_url
        settings.alert_webhook_url = "https://example.com/webhook"

        # Reset service and add capture
        reset_alerting_service()
        service = get_alerting_service()

        captured = []
        def capture(alert: Alert):
            captured.append(alert)
        service.add_handler(capture)

        try:
            # Create mock request
            mock_request = Mock(spec=Request)
            mock_request.url.path = "/api/test"
            mock_request.method = "POST"

            # Create exception
            exc = Exception("Critical failure with sensitive data")

            # Call handler
            response = await general_exception_handler(mock_request, exc)

            # Verify alert was captured
            assert len(captured) == 1
            assert captured[0].severity == AlertSeverity.CRITICAL
            assert captured[0].alert_type == AlertType.EXTERNAL_SERVICE_FAILURE
            assert "Critical failure" in captured[0].message or "Unhandled exception" in captured[0].message

        finally:
            settings.alert_webhook_url = original_url
            reset_alerting_service()

    def test_alerting_service_global_instance(self):
        """Verify global alerting service instance works."""
        service = get_alerting_service()
        assert service is not None
        assert isinstance(service, AlertingService)

    def test_reset_alerting_service(self):
        """Verify reset creates fresh service instance."""
        service1 = get_alerting_service()
        reset_alerting_service()
        service2 = get_alerting_service()

        # Should be different instances
        assert service1 is not service2


class TestAlertTypesAndSeverities:
    """Test all alert types and severities are properly defined."""

    def test_all_alert_types_exist(self):
        """Verify all expected alert types are defined."""
        expected_types = [
            "PAYMENT_FAILURE",
            "AGENT_EXECUTION_FAILURE",
            "ALLOWLIST_VIOLATION",
            "AUTHENTICATION_FAILURE",
            "DATABASE_ERROR",
            "EXTERNAL_SERVICE_FAILURE",
            "RESOURCE_EXHAUSTION",
            "SECURITY_VIOLATION",
        ]

        for alert_type in expected_types:
            assert hasattr(AlertType, alert_type)
            # Should be able to get value
            assert getattr(AlertType, alert_type).value is not None

    def test_all_severity_levels_exist(self):
        """Verify all severity levels are defined."""
        expected_severities = ["INFO", "WARNING", "ERROR", "CRITICAL"]

        for severity in expected_severities:
            assert hasattr(AlertSeverity, severity)
            assert getattr(AlertSeverity, severity).value is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

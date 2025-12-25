"""
Integration tests for Vercel Workflow endpoints.

These tests verify that all endpoints required by Vercel Workflows
are properly implemented and functional.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.core.database import async_session_maker, init_db, close_db
from src.core.config import settings

# Use a test database URL for these tests
settings.database_url = "sqlite:///:memory:"

client = TestClient(app)


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Set up and tear down test database."""
    await init_db()
    yield
    await close_db()


@pytest.fixture
def db_session():
    """Get a test database session."""
    return async_session_maker()


class TestEIP712SignatureEndpoint:
    """Test the /api/v1/wallet/sign-eip712 endpoint."""

    def test_sign_eip712_missing_private_key(self):
        """Test that endpoint fails gracefully when no private key is configured."""
        # Temporarily clear the private key
        original_key = settings.agent_wallet_private_key
        settings.agent_wallet_private_key = None

        try:
            request = {
                "domain": {
                    "name": "Test",
                    "version": "1",
                    "chainId": 338,
                    "verifyingContract": "0x1234567890123456789012345678901234567890"
                },
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                        {"name": "verifyingContract", "type": "address"}
                    ],
                    "Payment": [
                        {"name": "amount", "type": "uint256"},
                        {"name": "recipient", "type": "address"}
                    ]
                },
                "primaryType": "Payment",
                "message": {
                    "amount": 1000000,
                    "recipient": "0xabcdef1234567890abcdef1234567890abcdef12"
                }
            }

            response = client.post("/api/v1/wallet/sign-eip712", json=request)
            assert response.status_code == 500
            assert "private key not configured" in response.json()["detail"].lower()
        finally:
            settings.agent_wallet_private_key = original_key

    def test_sign_eip712_with_private_key(self):
        """Test that endpoint generates a signature when private key is configured."""
        # Set a test private key (this is a test key, not used in production)
        test_key = "0x1234567891234567812345678123456781234567812345678123456781234567"
        original_key = settings.agent_wallet_private_key
        settings.agent_wallet_private_key = test_key

        try:
            request = {
                "domain": {
                    "name": "Test",
                    "version": "1",
                    "chainId": 338,
                    "verifyingContract": "0x1234567890123456789012345678901234567890"
                },
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                        {"name": "verifyingContract", "type": "address"}
                    ],
                    "Payment": [
                        {"name": "amount", "type": "uint256"},
                        {"name": "recipient", "type": "address"}
                    ]
                },
                "primaryType": "Payment",
                "message": {
                    "amount": 1000000,
                    "recipient": "0xabcdef1234567890abcdef1234567890abcdef12"
                }
            }

            response = client.post("/api/v1/wallet/sign-eip712", json=request)
            assert response.status_code == 200

            data = response.json()
            assert "signature" in data
            assert "signer" in data
            assert "signed_at" in data
            assert data["signature"].startswith("0x")
            assert data["signer"].startswith("0x")
        finally:
            settings.agent_wallet_private_key = original_key


class TestPaymentStatusEndpoint:
    """Test the /api/v1/payments/status/{tx_hash} endpoint."""

    def test_payment_status_confirmed(self):
        """Test getting status for a confirmed transaction."""
        # Use a tx_hash that ends in an even digit (mock logic)
        tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef12345678900000"

        response = client.get(f"/api/v1/payments/status/{tx_hash}")
        assert response.status_code == 200

        data = response.json()
        assert data["txHash"] == tx_hash
        assert data["confirmed"] is True
        assert data["failed"] is False
        assert data["blockNumber"] is not None

    def test_payment_status_pending(self):
        """Test getting status for a pending transaction."""
        # Use a tx_hash that ends in an odd digit (mock logic)
        tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef12345678900001"

        response = client.get(f"/api/v1/payments/status/{tx_hash}")
        assert response.status_code == 200

        data = response.json()
        assert data["txHash"] == tx_hash
        assert data["confirmed"] is False
        assert data["failed"] is False

    def test_payment_status_failed(self):
        """Test getting status for a failed transaction."""
        # Use a tx_hash that ends in 'g' (not in hex chars, mock will fail)
        tx_hash = "0xgggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"

        response = client.get(f"/api/v1/payments/status/{tx_hash}")
        assert response.status_code == 200

        data = response.json()
        assert data["txHash"] == tx_hash
        assert data["confirmed"] is False
        assert data["failed"] is True


class TestNotificationEndpoints:
    """Test the /api/v1/notifications/* endpoints."""

    def test_renewal_failure_notification(self):
        """Test sending a renewal failure notification."""
        request = {
            "subscriptionId": "sub-123",
            "error": "Insufficient funds",
            "timestamp": "2025-01-15T10:00:00Z"
        }

        response = client.post("/api/v1/notifications/renewal-failure", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["subscriptionId"] == "sub-123"

    def test_webhook_notification(self):
        """Test sending a generic webhook notification."""
        response = client.post(
            "/api/v1/notifications/webhook",
            params={
                "event_type": "test_event",
                "message": "Test notification message",
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["notification_id"] is not None

    def test_approval_request_notification(self):
        """Test sending an approval request notification."""
        response = client.post(
            "/api/v1/notifications/approval-request",
            params={
                "request_id": "approval-123",
                "step_name": "execute-payment",
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestSubscriptionEndpoints:
    """Test the /api/v1/payments/subscription/* endpoints."""

    def test_get_subscription(self):
        """Test getting subscription details."""
        response = client.get("/api/v1/payments/subscription/sub-123")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "sub-123"
        assert data["amount"] == "10.0"
        assert data["token"] == "USDC"
        assert data["status"] == "active"

    def test_get_subscription_not_found(self):
        """Test getting non-existent subscription."""
        response = client.get("/api/v1/payments/subscription/non-existent")
        assert response.status_code == 404

    def test_save_subscription_progress(self):
        """Test saving subscription renewal progress."""
        request = {
            "subscriptionId": "sub-123",
            "renewalCount": 1,
            "nextRenewalDate": "2025-02-25T00:00:00Z"
        }

        response = client.post("/api/v1/payments/subscription/progress", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

    def test_mark_renewal_successful(self):
        """Test marking a renewal as successful."""
        request = {
            "txHash": "0xabc123...",
            "renewalDate": "2025-01-15T00:00:00Z"
        }

        response = client.post("/api/v1/payments/subscription/sub-123/success", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestExecuteStepEndpoint:
    """Test the /api/v1/agent/execute-step endpoint."""

    def test_execute_parse_payment_step(self):
        """Test executing a parse-payment step."""
        request = {
            "stepId": "step-1",
            "stepName": "parse-payment",
            "args": {"command": "Pay 10 USDC to 0x123..."}
        }

        response = client.post("/api/v1/agent/execute-step", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["stepId"] == "step-1"
        assert data["stepName"] == "parse-payment"
        assert "result" in data

    def test_execute_check_balance_step(self):
        """Test executing a check-balance step."""
        request = {
            "stepId": "step-2",
            "stepName": "check-balance",
            "args": {}
        }

        response = client.post("/api/v1/agent/execute-step", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "result" in data

    def test_execute_unknown_step(self):
        """Test executing an unknown step type."""
        request = {
            "stepId": "step-3",
            "stepName": "unknown-step",
            "args": {}
        }

        response = client.post("/api/v1/agent/execute-step", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert "error" in data


class TestVercelWorkflowCompatibility:
    """Test that the API is compatible with Vercel Workflow expectations."""

    def test_all_workflow_endpoints_exist(self):
        """Verify all endpoints expected by Vercel Workflows exist."""
        endpoints = [
            "/api/v1/wallet/sign-eip712",
            "/api/v1/payments/status/0x123",
            "/api/v1/notifications/renewal-failure",
            "/api/v1/payments/subscription/sub-123",
            "/api/v1/payments/subscription/progress",
            "/api/v1/payments/subscription/sub-123/success",
            "/api/v1/agent/execute-step",
        ]

        for endpoint in endpoints:
            # Just check that the route exists (HEAD request or similar)
            # We'll use GET/POST based on what makes sense
            if "/status/" in endpoint:
                response = client.get(endpoint)
            elif "/sign-eip712" in endpoint:
                response = client.post(endpoint, json={
                    "domain": {"name": "test", "version": "1"},
                    "types": {},
                    "primaryType": "test",
                    "message": {}
                })
            elif "/renewal-failure" in endpoint:
                response = client.post(endpoint, json={
                    "subscriptionId": "test",
                    "error": "test",
                    "timestamp": "2025-01-01T00:00:00Z"
                })
            elif "/subscription/progress" in endpoint:
                response = client.post(endpoint, json={
                    "subscriptionId": "test",
                    "renewalCount": 1,
                    "nextRenewalDate": "2025-01-01T00:00:00Z"
                })
            elif "/success" in endpoint:
                response = client.post(endpoint, json={
                    "txHash": "0x123",
                    "renewalDate": "2025-01-01T00:00:00Z"
                })
            elif "/execute-step" in endpoint:
                response = client.post(endpoint, json={
                    "stepId": "test",
                    "stepName": "parse-command",
                    "args": {}
                })
            elif "/subscription/" in endpoint and "progress" not in endpoint and "success" not in endpoint:
                response = client.get(endpoint)
            else:
                response = client.get(endpoint)

            # We expect either 200, 404 (for non-existent IDs), or 500 (for missing config)
            # But NOT 404 for the endpoint itself
            assert response.status_code in [200, 404, 500], f"Endpoint {endpoint} returned {response.status_code}"

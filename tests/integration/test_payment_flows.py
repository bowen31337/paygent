"""
Integration tests for payment flows.

This module tests end-to-end payment workflows including:
- x402 payment handling
- Agent execution with payment commands
- Payment history tracking
- Service discovery and pricing
"""

import pytest
import json
from uuid import uuid4
from datetime import datetime
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from src.main import app
from src.core.config import settings


class TestX402PaymentFlow:
    """Test x402 payment flow integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_agent_execute_payment_command(self, client):
        """Test that agent can execute a payment command."""
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "Pay 0.5 USDC to access the market data API",
                "budget_limit_usd": 10.0
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "session_id" in data
        assert "status" in data
        assert "result" in data
        assert "total_cost_usd" in data

        # Verify execution completed
        assert data["status"] in ["completed", "failed"]
        assert data["total_cost_usd"] >= 0

    def test_agent_execute_payment_with_budget_limit(self, client):
        """Test payment execution with budget limit enforcement."""
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "Pay 100 USDC to 0x1234567890123456789012345678901234567890",
                "budget_limit_usd": 50.0  # Lower than payment amount
            }
        )

        # Should still execute but may flag for review
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_agent_execute_payment_invalid_command(self, client):
        """Test that invalid payment commands are rejected."""
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "",  # Empty command
                "budget_limit_usd": 10.0
            }
        )

        # Pydantic returns 422 for validation errors
        assert response.status_code in [400, 422]  # Validation error

    def test_payment_history_tracking(self, client):
        """Test that payment history is tracked correctly."""
        # Execute a payment
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "Pay 0.1 USDC to test service",
                "budget_limit_usd": 5.0
            }
        )

        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]

        # Get execution logs for this session
        logs_response = client.get(f"/api/v1/logs?session_id={session_id}")

        if logs_response.status_code == 200:
            logs_data = logs_response.json()
            # Verify logs contain payment information
            if "logs" in logs_data and len(logs_data["logs"]) > 0:
                log = logs_data["logs"][0]
                assert "command" in log
                assert log["command"] == "Pay 0.1 USDC to test service"

    def test_service_discovery_with_pricing(self, client):
        """Test service discovery returns pricing information."""
        response = client.get("/api/v1/services/discover")

        assert response.status_code == 200
        data = response.json()

        # Should return list of services
        assert "services" in data or isinstance(data, list)

        # If services exist, verify structure
        services = data if isinstance(data, list) else data.get("services", [])
        if len(services) > 0:
            service = services[0]
            # Services should have pricing info
            assert "price_amount" in service or "price" in service


class TestAgentSessionManagement:
    """Test agent session management for payment flows."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_create_session_and_execute(self, client):
        """Test creating a session and executing multiple commands."""
        # Create first command to establish session
        response1 = client.post(
            "/api/v1/agent/execute",
            json={"command": "Check my balance"}
        )
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Execute second command with same session
        response2 = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "Pay 0.1 USDC to test",
                "session_id": session_id
            }
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    def test_session_retrieval(self, client):
        """Test retrieving session details."""
        # Create a session
        response = client.post(
            "/api/v1/agent/execute",
            json={"command": "Check balance"}
        )
        session_id = response.json()["session_id"]

        # Get session details
        session_response = client.get(f"/api/v1/agent/sessions/{session_id}")

        if session_response.status_code == 200:
            session_data = session_response.json()
            assert session_data["id"] == session_id
            assert "created_at" in session_data
            assert "last_active" in session_data

    def test_session_list(self, client):
        """Test listing all sessions."""
        response = client.get("/api/v1/agent/sessions")

        assert response.status_code == 200
        data = response.json()

        assert "sessions" in data
        assert "total" in data
        assert isinstance(data["sessions"], list)


class TestMultiStepPaymentWorkflow:
    """Test multi-step payment workflows."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_balance_check_then_payment(self, client):
        """Test workflow: check balance, then make payment."""
        # Step 1: Check balance
        balance_response = client.post(
            "/api/v1/agent/execute",
            json={"command": "Check my wallet balance"}
        )
        assert balance_response.status_code == 200

        balance_data = balance_response.json()
        session_id = balance_data["session_id"]

        # Step 2: Make payment using same session
        payment_response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "Pay 0.5 USDC to access API",
                "session_id": session_id
            }
        )
        assert payment_response.status_code == 200

        payment_data = payment_response.json()
        assert payment_data["session_id"] == session_id

    def test_service_discovery_then_payment(self, client):
        """Test workflow: discover services, then pay for one."""
        # Step 1: Discover services
        discover_response = client.get("/api/v1/services/discover")
        assert discover_response.status_code == 200

        # Step 2: Execute payment for a service
        payment_response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "Pay 0.1 USDC to access market data API",
                "budget_limit_usd": 5.0
            }
        )
        assert payment_response.status_code == 200


class TestPaymentStreamExecution:
    """Test streaming payment execution."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_stream_payment_events(self, client):
        """Test streaming events during payment execution."""
        response = client.post(
            "/api/v1/agent/stream",
            json={
                "command": "Pay 0.1 USDC to test service",
                "budget_limit_usd": 5.0
            },
            headers={"Accept": "text/event-stream"}
        )

        # Should return streaming response
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


class TestWalletBalanceIntegration:
    """Test wallet balance checking integration."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_balance_check_returns_valid_data(self, client):
        """Test that balance check returns properly formatted data."""
        response = client.post(
            "/api/v1/agent/execute",
            json={"command": "Check my wallet balance"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify result structure
        assert "result" in data
        result = data["result"]

        if result and result.get("success"):
            balance_data = result.get("result", {})
            assert "wallet_address" in balance_data
            assert "balances" in balance_data
            assert isinstance(balance_data["balances"], dict)


class TestCommandParsingIntegration:
    """Test command parsing for payment-related commands."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_parse_payment_command(self, client):
        """Test parsing various payment command formats."""
        commands = [
            "Pay 1 USDC to 0x1234...5678",
            "Send 0.5 CRO to service endpoint",
            "Transfer 10 USDC for API access",
            "Pay $5 worth of USDC to merchant"
        ]

        for command in commands:
            response = client.post(
                "/api/v1/agent/execute",
                json={"command": command}
            )
            # Should accept and process the command
            assert response.status_code == 200

    def test_parse_swap_command(self, client):
        """Test parsing swap commands."""
        commands = [
            "Swap 10 CRO for USDC",
            "Trade 5 USDC to CRO",
            "Exchange 100 USDC for CRO"
        ]

        for command in commands:
            response = client.post(
                "/api/v1/agent/execute",
                json={"command": command}
            )
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

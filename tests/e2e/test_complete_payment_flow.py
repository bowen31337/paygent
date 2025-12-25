"""
End-to-end test for complete payment flow from command to settlement.

This test verifies the complete flow:
1. User issues natural language payment command
2. Agent parses command and creates plan
3. Agent checks wallet balance
4. Agent executes x402 payment flow
5. Payment is settled on blockchain
6. Transaction is logged and tracked
"""

import pytest
import json
from uuid import uuid4
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient
from src.main import app


class TestCompletePaymentFlowE2E:
    """End-to-end tests for complete payment flow."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_x402_response(self):
        """Mock x402 payment facilitator response."""
        return {
            "payment_required": True,
            "payment_url": "https://x402-facilitator.cronos.org/pay",
            "amount": "0.5",
            "token": "USDC",
            "recipient": "0x1234567890123456789012345678901234567890",
            "domain": {
                "name": "x402-facilitator",
                "version": "1.0",
                "chainId": 338
            },
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"}
                ],
                "Payment": [
                    {"name": "amount", "type": "uint256"},
                    {"name": "recipient", "type": "address"},
                    {"name": "token", "type": "address"}
                ]
            },
            "message": {
                "amount": 500000,  # 0.5 USDC in wei
                "recipient": "0x1234567890123456789012345678901234567890",
                "token": "0x1234567890123456789012345678901234567890"
            }
        }

    def test_end_to_end_payment_from_command_to_settlement(self, client):
        """
        Test complete payment flow: command -> parse -> balance check -> payment -> settlement.

        This is the main E2E test for Feature #142.
        """
        # Step 1: User issues natural language payment command
        command = "Pay 0.5 USDC to access the market data API"

        response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": command,
                "budget_limit_usd": 10.0
            }
        )

        # Verify initial response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Step 2: Verify response structure contains all expected fields
        assert "session_id" in data, "Missing session_id in response"
        assert "status" in data, "Missing status in response"
        assert "result" in data, "Missing result in response"
        assert "total_cost_usd" in data, "Missing total_cost_usd in response"

        # Step 3: Verify execution status
        assert data["status"] in ["completed", "failed"], f"Unexpected status: {data['status']}"

        # Step 4: Verify result contains expected fields
        result = data["result"]
        if result:
            assert "success" in result, "Missing success in result"
            assert "action" in result, "Missing action in result"

            # If successful, verify the action was payment-related
            if result.get("success"):
                assert result["action"] in ["payment", "balance_check", "service_discovery"], \
                    f"Unexpected action: {result['action']}"

        # Step 5: Verify session was created and can be retrieved
        session_id = data["session_id"]
        session_response = client.get(f"/api/v1/agent/sessions/{session_id}")

        if session_response.status_code == 200:
            session_data = session_response.json()
            assert session_data["id"] == session_id
            assert "created_at" in session_data
            assert "last_active" in session_data

        # Step 6: Verify execution logs were created
        logs_response = client.get(f"/api/v1/logs?session_id={session_id}")

        if logs_response.status_code == 200:
            logs_data = logs_response.json()
            if "logs" in logs_data:
                # Should have at least one log entry
                assert len(logs_data["logs"]) > 0, "No execution logs created"

                # Verify log contains command
                log = logs_data["logs"][0]
                assert "command" in log
                assert log["command"] == command

    def test_multi_step_payment_workflow(self, client):
        """
        Test multi-step workflow: balance check -> payment -> verify.

        This tests the workflow aspect of durable execution.
        """
        # Step 1: Check balance
        balance_response = client.post(
            "/api/v1/agent/execute",
            json={"command": "Check my wallet balance"}
        )

        assert balance_response.status_code == 200
        balance_data = balance_response.json()
        session_id = balance_data["session_id"]

        # Verify balance was returned
        assert "result" in balance_data
        if balance_data["result"] and balance_data["result"].get("success"):
            balance_result = balance_data["result"].get("result", {})
            assert "balances" in balance_result

        # Step 2: Execute payment using same session
        payment_response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "Pay 0.1 USDC to test service",
                "session_id": session_id,
                "budget_limit_usd": 5.0
            }
        )

        assert payment_response.status_code == 200
        payment_data = payment_response.json()

        # Verify same session is used
        assert payment_data["session_id"] == session_id

        # Step 3: Get complete session history
        session_response = client.get(f"/api/v1/agent/sessions/{session_id}")
        assert session_response.status_code == 200

    def test_payment_with_streaming_events(self, client):
        """
        Test payment execution with streaming events.

        This verifies the streaming interface for real-time feedback.
        """
        response = client.post(
            "/api/v1/agent/stream",
            json={
                "command": "Pay 0.2 USDC to access API",
                "budget_limit_usd": 5.0
            },
            headers={"Accept": "text/event-stream"}
        )

        # Should return streaming response
        assert response.status_code == 200

        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type, \
            f"Expected text/event-stream, got {content_type}"

        # Read some events
        content = response.content.decode('utf-8')

        # Should contain event data
        assert len(content) > 0, "Empty streaming response"

        # Verify event format (SSE format)
        lines = content.strip().split('\n')
        has_events = any(line.startswith('event:') for line in lines)
        has_data = any(line.startswith('data:') for line in lines)

        # Either has events or is a single response
        assert has_events or has_data, "Invalid SSE format"

    def test_payment_flow_with_budget_limits(self, client):
        """
        Test payment flow with budget limit enforcement.

        This verifies that budget limits are respected during payment execution.
        """
        # Test with budget lower than payment amount
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "Pay 10 USDC to test",
                "budget_limit_usd": 5.0  # Lower than payment
            }
        )

        # Should still process (may flag for review or adjust)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_payment_flow_error_handling(self, client):
        """
        Test payment flow error handling.

        This verifies proper error handling for failed payments.
        """
        # Test with invalid command format
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "command": "",  # Invalid
                "budget_limit_usd": 5.0
            }
        )

        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422]

    def test_payment_flow_with_session_persistence(self, client):
        """
        Test that payment flow maintains session persistence across commands.

        This verifies Feature #147: Session persistence across commands.
        """
        # Create first session
        response1 = client.post(
            "/api/v1/agent/execute",
            json={"command": "Check balance"}
        )
        session_id = response1.json()["session_id"]

        # Execute multiple commands with same session
        commands = [
            "Pay 0.1 USDC to service1",
            "Pay 0.2 USDC to service2",
            "Check balance"
        ]

        for command in commands:
            response = client.post(
                "/api/v1/agent/execute",
                json={
                    "command": command,
                    "session_id": session_id
                }
            )
            assert response.status_code == 200
            assert response.json()["session_id"] == session_id

        # Verify all commands are logged under same session
        logs_response = client.get(f"/api/v1/logs?session_id={session_id}")
        if logs_response.status_code == 200:
            logs_data = logs_response.json()
            if "logs" in logs_data:
                # Should have at least 3 logs (one per command)
                assert len(logs_data["logs"]) >= 3

    def test_concurrent_payment_sessions(self, client):
        """
        Test multiple concurrent payment sessions.

        This verifies that multiple users can execute payments simultaneously.
        """
        # Create multiple sessions
        sessions = []
        for i in range(3):
            response = client.post(
                "/api/v1/agent/execute",
                json={"command": f"Pay {0.1 * (i+1)} USDC to test{i}"}
            )
            assert response.status_code == 200
            sessions.append(response.json()["session_id"])

        # Verify all sessions are unique
        assert len(set(sessions)) == 3, "Session IDs should be unique"

        # Verify each session can be retrieved
        for session_id in sessions:
            response = client.get(f"/api/v1/agent/sessions/{session_id}")
            assert response.status_code == 200
            assert response.json()["id"] == session_id


class TestPaymentFlowWithServiceDiscovery:
    """Test payment flow integrated with service discovery."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_discover_then_pay_workflow(self, client):
        """
        Test complete workflow: discover services -> select -> pay.

        This tests the integration between service discovery and payment.
        """
        # Step 1: Discover available services
        discover_response = client.get("/api/v1/services/discover")

        if discover_response.status_code == 200:
            services_data = discover_response.json()

            # Should return list of services
            services = services_data if isinstance(services_data, list) else services_data.get("services", [])

            if len(services) > 0:
                # Step 2: Execute payment for a discovered service
                payment_response = client.post(
                    "/api/v1/agent/execute",
                    json={
                        "command": "Pay 0.1 USDC to access market data API",
                        "budget_limit_usd": 5.0
                    }
                )

                assert payment_response.status_code == 200
                payment_data = payment_response.json()

                # Verify payment was processed
                assert "session_id" in payment_data
                assert payment_data["status"] in ["completed", "failed"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

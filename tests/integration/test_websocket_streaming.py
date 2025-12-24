"""
Test WebSocket streaming functionality for real-time agent execution.

This module tests the WebSocket endpoints for:
- Real-time agent execution streaming
- HITL approval workflows
- Subagent event streaming
- Error handling and cancellation
"""
import asyncio
import json
import pytest
from typing import Any, Dict
from uuid import UUID, uuid4
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from src.main import app
from src.core.database import async_session_maker
from src.models.agent_sessions import AgentSession, ExecutionLog
from src.models.payments import Payment
from src.services.agent_service import AgentService


class TestWebSocketStreaming:
    """Test suite for WebSocket streaming functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        with TestClient(app) as client:
            yield client

    @pytest.fixture
    async def test_session(self):
        """Create test session using the app's database."""
        # Use the app's database session
        async with async_session_maker() as session:
            session_id = uuid4()
            new_session = AgentSession(
                id=session_id,
                user_id=uuid4(),
                wallet_address=None,
                config={"test": True}
            )
            session.add(new_session)
            await session.commit()
            await session.refresh(new_session)
            return new_session

    def test_websocket_connection(self, client, test_session):
        """Test WebSocket connection establishment."""
        # Test connection without authentication (should work in debug mode)
        with client.websocket_connect(f"/ws?session_id={test_session.id}") as websocket:
            # Receive connection established event
            data = websocket.receive_text()
            message = json.loads(data)

            assert message["type"] == "connected"
            assert message["data"]["session_id"] == str(test_session.id)

    def test_error_handling(self, client, test_session):
        """Test error handling in WebSocket communication."""
        with client.websocket_connect(f"/ws?session_id={test_session.id}") as websocket:
            # First, receive connection established event
            websocket.receive_text()

            # Send invalid message
            invalid_message = {
                "type": "invalid_type",
                "data": {}
            }
            websocket.send_text(json.dumps(invalid_message))

            # Receive error event
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "error"
            assert "Unknown message type" in message["data"]["message"]

    def test_invalid_session(self, client):
        """Test WebSocket connection with invalid session."""
        # Use a non-existent session ID
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws?session_id=invalid-session-id") as websocket:
                pass

    def test_missing_session(self, client):
        """Test WebSocket connection without session ID."""
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws") as websocket:
                pass


class TestWebSocketEventCreation:
    """Test WebSocket event creation functions."""

    def test_create_thinking_event(self):
        """Test thinking event creation."""
        from src.schemas.websocket import create_thinking_event

        event = create_thinking_event(
            session_id="test-session",
            command="Test command",
            step=1,
            total_steps=5,
            thought_process="Thinking about the command"
        )

        assert event.type == "thinking"
        assert event.data["session_id"] == "test-session"
        assert event.data["command"] == "Test command"
        assert event.data["step"] == 1
        assert event.data["total_steps"] == 5
        assert event.data["thought_process"] == "Thinking about the command"

    def test_create_tool_call_event(self):
        """Test tool call event creation."""
        from src.schemas.websocket import create_tool_call_event

        event = create_tool_call_event(
            session_id="test-session",
            tool_name="get_wallet_balance",
            tool_args={"tokens": ["USDC", "CRO"]},
            tool_id="tool-123"
        )

        assert event.type == "tool_call"
        assert event.data["session_id"] == "test-session"
        assert event.data["tool_name"] == "get_wallet_balance"
        assert event.data["tool_args"] == {"tokens": ["USDC", "CRO"]}
        assert event.data["tool_id"] == "tool-123"

    def test_create_tool_result_event(self):
        """Test tool result event creation."""
        from src.schemas.websocket import create_tool_result_event

        event = create_tool_result_event(
            session_id="test-session",
            tool_id="tool-123",
            result={"balance": "100.00"},
            success=True,
            error=None
        )

        assert event.type == "tool_result"
        assert event.data["session_id"] == "test-session"
        assert event.data["tool_id"] == "tool-123"
        assert event.data["result"] == {"balance": "100.00"}
        assert event.data["success"] is True
        assert event.data["error"] is None

    def test_create_approval_required_event(self):
        """Test approval required event creation."""
        from src.schemas.websocket import create_approval_required_event
        from uuid import uuid4

        request_id = uuid4()
        event = create_approval_required_event(
            session_id="test-session",
            request_id=request_id,
            tool_name="execute_payment",
            tool_args={"amount": 100, "token": "USDC", "recipient": "example.com"},
            reason="High-value payment requires approval",
            amount="100",
            currency="USDC",
            estimated_cost="100 USDC"
        )

        assert event.type == "approval_required"
        assert event.data["session_id"] == "test-session"
        assert event.data["request_id"] == str(request_id)
        assert event.data["tool_name"] == "execute_payment"
        assert event.data["reason"] == "High-value payment requires approval"
        assert event.data["amount"] == "100"
        assert event.data["currency"] == "USDC"
        assert event.data["estimated_cost"] == "100 USDC"

    def test_create_complete_event(self):
        """Test complete event creation."""
        from src.schemas.websocket import create_complete_event
        from uuid import uuid4

        execution_id = uuid4()
        event = create_complete_event(
            session_id="test-session",
            execution_id=execution_id,
            result={"message": "Command executed successfully"},
            success=True,
            total_cost="0.10 USDC",
            duration_ms=1500,
            tool_calls=[{"name": "get_wallet_balance", "args": {}}]
        )

        assert event.type == "complete"
        assert event.data["session_id"] == "test-session"
        assert event.data["execution_id"] == str(execution_id)
        assert event.data["result"] == {"message": "Command executed successfully"}
        assert event.data["success"] is True
        assert event.data["total_cost"] == "0.10 USDC"
        assert event.data["duration_ms"] == 1500
        assert event.data["tool_calls"] == [{"name": "get_wallet_balance", "args": {}}]

    def test_create_error_event(self):
        """Test error event creation."""
        from src.schemas.websocket import create_error_event
        from uuid import uuid4

        execution_id = uuid4()
        event = create_error_event(
            message="Test error occurred",
            session_id="test-session",
            execution_id=execution_id,
            error_type="ValidationError",
            details={"field": "amount", "message": "Invalid amount"}
        )

        assert event.type == "error"
        assert event.data["message"] == "Test error occurred"
        assert event.data["session_id"] == "test-session"
        assert event.data["execution_id"] == str(execution_id)
        assert event.data["error_type"] == "ValidationError"
        assert event.data["details"] == {"field": "amount", "message": "Invalid amount"}

    def test_create_subagent_start_event(self):
        """Test subagent start event creation."""
        from src.schemas.websocket import create_subagent_start_event

        event = create_subagent_start_event(
            session_id="test-session",
            subagent_id="subagent-123",
            subagent_type="Moonlander Trader",
            task="Open perpetual position",
            parent_agent="Main Agent"
        )

        assert event.type == "subagent_start"
        assert event.data["session_id"] == "test-session"
        assert event.data["subagent_id"] == "subagent-123"
        assert event.data["subagent_type"] == "Moonlander Trader"
        assert event.data["task"] == "Open perpetual position"
        assert event.data["parent_agent"] == "Main Agent"

    def test_create_subagent_end_event(self):
        """Test subagent end event creation."""
        from src.schemas.websocket import create_subagent_end_event

        event = create_subagent_end_event(
            session_id="test-session",
            subagent_id="subagent-123",
            result={"position_id": "pos-456", "status": "open"},
            success=True,
            duration_ms=2000,
            error=None
        )

        assert event.type == "subagent_end"
        assert event.data["session_id"] == "test-session"
        assert event.data["subagent_id"] == "subagent-123"
        assert event.data["result"] == {"position_id": "pos-456", "status": "open"}
        assert event.data["success"] is True
        assert event.data["duration_ms"] == 2000
        assert event.data["error"] is None

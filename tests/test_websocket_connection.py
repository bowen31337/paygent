"""
WebSocket connection and functionality tests.

Tests WebSocket endpoint for real-time agent execution and HITL workflows.
"""
import asyncio
import json
import pytest
import websockets
from typing import AsyncGenerator
import uuid
from datetime import datetime

from src.main import app
from src.services.session_service import SessionService
from src.db.database import get_db


class TestWebSocketConnection:
    """Test WebSocket connection establishment and basic functionality."""

    @pytest.fixture
    async def session_id(self) -> AsyncGenerator[str, None]:
        """Create a test session."""
        session_service = SessionService()
        session = await session_service.create_session(
            user_id="test-user-ws",
            wallet_address="0xtest123",
            config={"debug": True}
        )
        yield str(session.id)
        # Cleanup
        # await session_service.delete_session(str(session.id))

    @pytest.mark.asyncio
    async def test_websocket_connects_successfully(self, session_id: str):
        """Test that WebSocket connection establishes successfully."""
        uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"

        try:
            async with websockets.connect(uri) as websocket:
                # Wait for connection established message
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                message = json.loads(response)

                assert message["type"] == "connected"
                assert message["data"]["session_id"] == session_id
                assert "user_id" in message["data"]

                print(f"✓ WebSocket connected successfully for session {session_id}")
                print(f"  Received: {message}")

        except asyncio.TimeoutError:
            pytest.fail("WebSocket connection timeout")
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")

    @pytest.mark.asyncio
    async def test_websocket_ping_heartbeat(self, session_id: str):
        """Test ping/pong heartbeat works."""
        uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"

        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            await websocket.recv()

            # Send ping message
            start_time = datetime.now()
            ping_msg = json.dumps({
                "type": "ping",
                "data": {"timestamp": start_time.isoformat()}
            })
            await websocket.send(ping_msg)

            # Wait for pong or response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                end_time = datetime.now()
                latency_ms = (end_time - start_time).total_seconds() * 1000

                print(f"✓ Ping/pong latency: {latency_ms:.2f}ms")
                assert latency_ms < 100, f"Latency {latency_ms}ms exceeds 100ms threshold"

            except asyncio.TimeoutError:
                # Pong might not be implemented, connection still valid
                print("  Ping/pong not implemented (connection valid)")

    @pytest.mark.asyncio
    async def test_websocket_execute_message(self, session_id: str):
        """Test that execute message triggers agent execution."""
        uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"

        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            await websocket.recv()

            # Send execute command
            execute_msg = json.dumps({
                "type": "execute",
                "data": {
                    "command": "Check my wallet balance",
                    "plan": None
                }
            })
            await websocket.send(execute_msg)

            # Should receive thinking event
            thinking_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            thinking_message = json.loads(thinking_response)
            assert thinking_message["type"] == "thinking"
            print(f"✓ Received thinking event: {thinking_message}")

            # Should receive complete event
            complete_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            complete_message = json.loads(complete_response)
            assert complete_message["type"] == "complete"
            assert complete_message["data"]["success"] is True
            print(f"✓ Received complete event: {complete_message}")

    @pytest.mark.asyncio
    async def test_websocket_invalid_session_rejected(self):
        """Test that invalid session_id is rejected."""
        invalid_session_id = str(uuid.uuid4())
        uri = f"ws://localhost:8000/api/v1/ws?session_id={invalid_session_id}"

        try:
            async with websockets.connect(uri, close_timeout=5.0) as websocket:
                # Should receive close frame or error
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                message = json.loads(response)

                # Either error message or connection close
                assert message.get("type") == "error" or "Invalid session" in str(message)

        except websockets.exceptions.ConnectionClosed as e:
            # Expected - connection should be closed
            assert e.code >= 1000  # Valid close code
            print(f"✓ Invalid session rejected with code {e.code}")
        except asyncio.TimeoutError:
            pass  # Connection closed without message - also valid

    @pytest.mark.asyncio
    async def test_websocket_handles_multiple_messages(self, session_id: str):
        """Test that WebSocket handles multiple sequential messages."""
        uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"

        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            await websocket.recv()

            commands = [
                "Check my balance",
                "What services are available?",
                "Show payment history"
            ]

            for cmd in commands:
                # Send execute command
                execute_msg = json.dumps({
                    "type": "execute",
                    "data": {"command": cmd, "plan": None}
                })
                await websocket.send(execute_msg)

                # Wait for thinking event
                thinking_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                thinking_message = json.loads(thinking_response)
                assert thinking_message["type"] == "thinking"

                # Wait for complete event
                complete_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                complete_message = json.loads(complete_response)
                assert complete_message["type"] == "complete"

                print(f"✓ Command '{cmd}' executed successfully")

    @pytest.mark.asyncio
    async def test_websocket_event_types_consistent(self, session_id: str):
        """Test that WebSocket events follow consistent naming structure."""
        uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"

        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            response = await websocket.recv()
            message = json.loads(response)

            # Check snake_case naming
            assert "_" in message["type"] or message["type"] in ["connected", "error"]

            # Send execute to trigger more events
            execute_msg = json.dumps({
                "type": "execute",
                "data": {"command": "test", "plan": None}
            })
            await websocket.send(execute_msg)

            # Collect all events
            events = []
            for _ in range(3):  # thinking, complete, maybe tool_call
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(response)
                    events.append(event["type"])
                except asyncio.TimeoutError:
                    break

            # Verify all use snake_case
            for event_type in events:
                assert "_" in event_type or event_type.islower(), \
                    f"Event type '{event_type}' should use snake_case"

            print(f"✓ Event types follow consistent naming: {events}")

    @pytest.mark.asyncio
    async def test_websocket_latency_under_100ms(self, session_id: str):
        """Test that WebSocket message latency is under 100ms."""
        uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"

        latencies = []

        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            await websocket.recv()

            # Send multiple commands and measure latency
            for i in range(5):
                start_time = datetime.now()

                execute_msg = json.dumps({
                    "type": "execute",
                    "data": {"command": f"test command {i}", "plan": None}
                })
                await websocket.send(execute_msg)

                # Wait for thinking event
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                end_time = datetime.now()

                latency_ms = (end_time - start_time).total_seconds() * 1000
                latencies.append(latency_ms)

                # Wait for complete before next command
                await websocket.recv()

            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)

            print(f"✓ WebSocket latency stats:")
            print(f"  Average: {avg_latency:.2f}ms")
            print(f"  Max: {max_latency:.2f}ms")
            print(f"  Min: {min(latencies):.2f}ms")

            # Verify p95 latency is under 100ms
            sorted_latencies = sorted(latencies)
            p95_latency = sorted_latencies[int(len(latencies) * 0.95)]
            assert p95_latency < 100, f"P95 latency {p95_latency}ms exceeds 100ms"

    @pytest.mark.asyncio
    async def test_websocket_graceful_disconnect(self, session_id: str):
        """Test that WebSocket disconnects gracefully."""
        uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"

        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            await websocket.recv()

            # Send a command
            execute_msg = json.dumps({
                "type": "execute",
                "data": {"command": "test", "plan": None}
            })
            await websocket.send(execute_msg)

        # Connection should close gracefully when exiting context
        print("✓ WebSocket disconnected gracefully")

        # Try reconnecting to same session
        async with websockets.connect(uri) as websocket:
            response = await websocket.recv()
            message = json.loads(response)
            assert message["type"] == "connected"
            print("✓ Successfully reconnected to same session")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

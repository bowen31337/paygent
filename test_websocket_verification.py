#!/usr/bin/env python3
"""
WebSocket Verification Tests for Paygent Platform

Tests the following features:
- Feature 98: WebSocket connection establishes successfully
- Feature 99: WebSocket execute message triggers agent execution
- Feature 101: WebSocket approve message resumes execution
- Feature 102: WebSocket cancel message stops execution
- Feature 170: WebSocket event types follow consistent naming

This script verifies that the WebSocket implementation works correctly
with proper database session handling and event streaming.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import websockets
from websockets.exceptions import WebSocketException

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket endpoint configuration
WS_URL = "ws://localhost:8000/api/v1/ws"
TEST_SESSION_ID = str(uuid4())
TEST_USER_ID = "test-user-123"
TEST_COMMAND = "Check my wallet balance"
TEST_TOKEN = "test-token-123"  # Optional token for auth


class WebSocketTester:
    """Test WebSocket functionality."""

    def __init__(self, ws_url: str, session_id: str, user_id: str):
        self.ws_url = ws_url
        self.session_id = session_id
        self.user_id = user_id
        self.websocket = None
        self.received_messages = []
        self.connection_established = False

    async def connect(self, token: Optional[str] = None) -> bool:
        """Test WebSocket connection establishment."""
        try:
            # Build URL with session_id
            url = f"{self.ws_url}?session_id={self.session_id}"
            if token:
                url += f"&token={token}"

            logger.info(f"Connecting to WebSocket: {url}")
            self.websocket = await websockets.connect(url, timeout=10)
            logger.info("WebSocket connection established successfully")

            # Wait for connection established event
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=5)
                event = json.loads(message)
                logger.info(f"Received initial event: {event}")

                if event.get("type") == "connected":
                    self.connection_established = True
                    self.received_messages.append(event)
                    logger.info("✓ Connection established event received")
                    return True
                else:
                    logger.warning(f"Unexpected initial event type: {event.get('type')}")
                    return False

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for connection established event")
                return False

        except WebSocketException as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            return False

    async def send_execute_message(self, command: str) -> bool:
        """Test sending execute message."""
        if not self.websocket:
            logger.error("No active WebSocket connection")
            return False

        try:
            message = {
                "type": "execute",
                "data": {
                    "command": command,
                    "plan": None
                }
            }

            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent execute message: {command}")

            # Wait for thinking event
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                event = json.loads(message)
                self.received_messages.append(event)
                logger.info(f"Received event: {event}")

                if event.get("type") == "thinking":
                    logger.info("✓ Thinking event received")
                    return True
                else:
                    logger.warning(f"Unexpected event type after execute: {event.get('type')}")
                    return False

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for thinking event")
                return False

        except Exception as e:
            logger.error(f"Error sending execute message: {e}")
            return False

    async def send_approve_message(self, request_id: UUID) -> bool:
        """Test sending approve message."""
        if not self.websocket:
            logger.error("No active WebSocket connection")
            return False

        try:
            message = {
                "type": "approve",
                "data": {
                    "request_id": str(request_id)
                }
            }

            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent approve message for request: {request_id}")

            # Wait for approval event
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                event = json.loads(message)
                self.received_messages.append(event)
                logger.info(f"Received event: {event}")

                if event.get("type") in ["approved", "edit_approved"]:
                    logger.info("✓ Approval event received")
                    return True
                else:
                    logger.warning(f"Unexpected event type after approve: {event.get('type')}")
                    return False

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for approval event")
                return False

        except Exception as e:
            logger.error(f"Error sending approve message: {e}")
            return False

    async def send_cancel_message(self, execution_id: UUID) -> bool:
        """Test sending cancel message."""
        if not self.websocket:
            logger.error("No active WebSocket connection")
            return False

        try:
            message = {
                "type": "cancel",
                "data": {
                    "execution_id": str(execution_id)
                }
            }

            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent cancel message for execution: {execution_id}")

            # Wait for cancellation event
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                event = json.loads(message)
                self.received_messages.append(event)
                logger.info(f"Received event: {event}")

                if event.get("type") == "cancelled":
                    logger.info("✓ Cancellation event received")
                    return True
                else:
                    logger.warning(f"Unexpected event type after cancel: {event.get('type')}")
                    return False

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for cancellation event")
                return False

        except Exception as e:
            logger.error(f"Error sending cancel message: {e}")
            return False

    async def listen_for_events(self, timeout: int = 30) -> bool:
        """Listen for events for a specified time."""
        if not self.websocket:
            logger.error("No active WebSocket connection")
            return False

        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                    event = json.loads(message)
                    self.received_messages.append(event)
                    logger.info(f"Received event: {event.get('type')}")

                    # Check for specific event types
                    if event.get("type") == "thinking":
                        logger.info("✓ Thinking event received")
                    elif event.get("type") == "tool_call":
                        logger.info("✓ Tool call event received")
                    elif event.get("type") == "tool_result":
                        logger.info("✓ Tool result event received")
                    elif event.get("type") == "approval_required":
                        logger.info("✓ Approval required event received")
                    elif event.get("type") == "complete":
                        logger.info("✓ Complete event received")
                    elif event.get("type") == "error":
                        logger.info("✓ Error event received")
                    elif event.get("type") == "subagent_start":
                        logger.info("✓ Subagent start event received")
                    elif event.get("type") == "subagent_end":
                        logger.info("✓ Subagent end event received")
                    elif event.get("type") == "connected":
                        logger.info("✓ Connected event received")
                    elif event.get("type") == "cancelled":
                        logger.info("✓ Cancelled event received")
                    elif event.get("type") == "approved":
                        logger.info("✓ Approved event received")
                    elif event.get("type") == "rejected":
                        logger.info("✓ Rejected event received")
                    elif event.get("type") == "edit_approved":
                        logger.info("✓ Edit approved event received")

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    break

            return True

        except Exception as e:
            logger.error(f"Error listening for events: {e}")
            return False

    async def disconnect(self):
        """Close WebSocket connection."""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

    def verify_event_naming(self) -> bool:
        """Verify all event types follow consistent naming."""
        expected_events = {
            "connected", "thinking", "tool_call", "tool_result",
            "approval_required", "complete", "error", "subagent_start",
            "subagent_end", "approved", "rejected", "edit_approved",
            "cancelled"
        }

        received_event_types = set()
        for event in self.received_messages:
            event_type = event.get("type")
            if event_type:
                received_event_types.add(event_type)

        # Check if all received event types are in expected set
        unexpected_events = received_event_types - expected_events
        if unexpected_events:
            logger.error(f"Unexpected event types: {unexpected_events}")
            return False

        # Check for snake_case naming (all lowercase with underscores)
        for event_type in received_event_types:
            if not event_type.islower() or not all(c.isalnum() or c == '_' for c in event_type):
                logger.error(f"Event type '{event_type}' does not follow snake_case naming")
                return False

        logger.info("✓ All event types follow consistent snake_case naming")
        return True

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("WEBSOCKET VERIFICATION SUMMARY")
        print("="*60)
        print(f"Session ID: {self.session_id}")
        print(f"User ID: {self.user_id}")
        print(f"Total messages received: {len(self.received_messages)}")

        # Count event types
        event_counts = {}
        for event in self.received_messages:
            event_type = event.get("type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        print("\nEvent types received:")
        for event_type, count in event_counts.items():
            print(f"  - {event_type}: {count}")

        print("\nTest Results:")
        print(f"✓ Connection established: {self.connection_established}")
        print(f"✓ Event naming consistent: {self.verify_event_naming()}")
        print("="*60)


async def test_websocket_connection():
    """Test WebSocket connection establishment (Feature 98)."""
    print("\n🧪 Testing WebSocket Connection Establishment...")

    tester = WebSocketTester(WS_URL, TEST_SESSION_ID, TEST_USER_ID)

    try:
        # Test connection establishment
        success = await tester.connect(TEST_TOKEN)
        if success:
            print("✅ Feature 98 PASSED: WebSocket connection establishes successfully")
            return True
        else:
            print("❌ Feature 98 FAILED: WebSocket connection failed")
            return False

    except Exception as e:
        logger.error(f"Error testing WebSocket connection: {e}")
        return False
    finally:
        await tester.disconnect()


async def test_websocket_execute():
    """Test WebSocket execute message (Feature 99)."""
    print("\n🧪 Testing WebSocket Execute Message...")

    tester = WebSocketTester(WS_URL, str(uuid4()), TEST_USER_ID)

    try:
        # Connect first
        connected = await tester.connect(TEST_TOKEN)
        if not connected:
            print("❌ Feature 99 FAILED: Could not establish connection")
            return False

        # Send execute message
        success = await tester.send_execute_message(TEST_COMMAND)
        if success:
            print("✅ Feature 99 PASSED: WebSocket execute message triggers agent execution")
            return True
        else:
            print("❌ Feature 99 FAILED: Execute message did not trigger execution")
            return False

    except Exception as e:
        logger.error(f"Error testing WebSocket execute: {e}")
        return False
    finally:
        await tester.disconnect()


async def test_websocket_approve():
    """Test WebSocket approve message (Feature 101)."""
    print("\n🧪 Testing WebSocket Approve Message...")

    tester = WebSocketTester(WS_URL, str(uuid4()), TEST_USER_ID)

    try:
        # Connect first
        connected = await tester.connect(TEST_TOKEN)
        if not connected:
            print("❌ Feature 101 FAILED: Could not establish connection")
            return False

        # Send approve message
        test_request_id = uuid4()
        success = await tester.send_approve_message(test_request_id)
        if success:
            print("✅ Feature 101 PASSED: WebSocket approve message resumes execution")
            return True
        else:
            print("❌ Feature 101 FAILED: Approve message did not resume execution")
            return False

    except Exception as e:
        logger.error(f"Error testing WebSocket approve: {e}")
        return False
    finally:
        await tester.disconnect()


async def test_websocket_cancel():
    """Test WebSocket cancel message (Feature 102)."""
    print("\n🧪 Testing WebSocket Cancel Message...")

    tester = WebSocketTester(WS_URL, str(uuid4()), TEST_USER_ID)

    try:
        # Connect first
        connected = await tester.connect(TEST_TOKEN)
        if not connected:
            print("❌ Feature 102 FAILED: Could not establish connection")
            return False

        # Send cancel message
        test_execution_id = uuid4()
        success = await tester.send_cancel_message(test_execution_id)
        if success:
            print("✅ Feature 102 PASSED: WebSocket cancel message stops execution")
            return True
        else:
            print("❌ Feature 102 FAILED: Cancel message did not stop execution")
            return False

    except Exception as e:
        logger.error(f"Error testing WebSocket cancel: {e}")
        return False
    finally:
        await tester.disconnect()


async def test_websocket_event_naming():
    """Test WebSocket event naming consistency (Feature 170)."""
    print("\n🧪 Testing WebSocket Event Naming Consistency...")

    tester = WebSocketTester(WS_URL, str(uuid4()), TEST_USER_ID)

    try:
        # Connect and listen for events
        connected = await tester.connect(TEST_TOKEN)
        if not connected:
            print("❌ Feature 170 FAILED: Could not establish connection")
            return False

        # Send a few messages to generate events
        await tester.send_execute_message("Check balance")
        await asyncio.sleep(2)

        # Listen for more events
        await tester.listen_for_events(5)

        # Verify naming consistency
        success = tester.verify_event_naming()
        if success:
            print("✅ Feature 170 PASSED: WebSocket event types follow consistent naming")
            return True
        else:
            print("❌ Feature 170 FAILED: Event naming inconsistent")
            return False

    except Exception as e:
        logger.error(f"Error testing WebSocket event naming: {e}")
        return False
    finally:
        await tester.disconnect()


async def run_all_tests():
    """Run all WebSocket verification tests."""
    print("🚀 Starting WebSocket Verification Tests")
    print(f"Server URL: {WS_URL}")
    print(f"Test Session: {TEST_SESSION_ID}")

    results = []

    # Test individual features
    results.append(("Feature 98", await test_websocket_connection()))
    results.append(("Feature 99", await test_websocket_execute()))
    results.append(("Feature 101", await test_websocket_approve()))
    results.append(("Feature 102", await test_websocket_cancel()))
    results.append(("Feature 170", await test_websocket_event_naming()))

    # Print summary
    print("\n" + "="*60)
    print("FINAL TEST RESULTS")
    print("="*60)

    passed = 0
    total = len(results)

    for feature, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{feature}: {status}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 All WebSocket features verified successfully!")
        return True
    else:
        print(f"⚠️  {total-passed} features need attention")
        return False


if __name__ == "__main__":
    # Check if websockets package is available
    try:
        import websockets
    except ImportError:
        print("❌ websockets package not found. Install with: pip install websockets")
        sys.exit(1)

    # Run the tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
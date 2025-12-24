"""
Test script for WebSocket functionality.

This script tests the WebSocket endpoint to verify that:
1. WebSocket connections can be established
2. Execute commands work
3. Events are properly streamed
"""
import asyncio
import json
import websockets
from uuid import uuid4


async def test_websocket_connection():
    """Test WebSocket connection and basic functionality."""
    uri = "ws://localhost:8000/ws?session_id=test-session-123"

    try:
        print("Testing WebSocket connection...")

        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connected successfully")

            # Test 1: Execute a simple command
            print("\nTest 1: Executing command...")
            execute_message = {
                "type": "execute",
                "data": {
                    "command": "test command",
                    "plan": []
                }
            }

            await websocket.send(json.dumps(execute_message))
            print("✓ Execute message sent")

            # Wait for responses
            for i in range(5):  # Wait for up to 5 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    message = json.loads(response)
                    print(f"✓ Received message: {message['type']}")

                    if message['type'] == 'complete':
                        print("✓ Command execution completed")
                        break

                except asyncio.TimeoutError:
                    print("No more messages received")
                    break

            print("\n✓ WebSocket test completed successfully!")

    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket_connection())
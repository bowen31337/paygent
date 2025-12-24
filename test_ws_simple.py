#!/usr/bin/env python3
"""Simple WebSocket test script."""
import asyncio
import json
import sys
import uuid
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

import websockets
from src.core.database import get_db
from src.services.session_service import SessionService


async def test_websocket():
    """Test WebSocket connection."""
    print("=" * 60)
    print("WebSocket Connection Test")
    print("=" * 60)

    # Create a test session
    print("\n1. Creating test session...")
    async for db in get_db():
        session_service = SessionService(db)
        session = await session_service.create_session(
            user_id=uuid.uuid4(),
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            config={"debug": True}
        )
        await db.commit()
        session_id = str(session.id)
        print(f"   Session ID: {session_id}")
        break

    # Connect to WebSocket
    uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"
    print(f"\n2. Connecting to WebSocket: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("   ✓ Connection established")

            # Wait for connection message
            print("\n3. Waiting for connection event...")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            message = json.loads(response)
            print(f"   Received: {message}")

            if message["type"] == "connected":
                print("   ✓ Connection event received")
            else:
                print(f"   ✗ Unexpected message type: {message['type']}")
                return False

            # Send execute command
            print("\n4. Sending execute command...")
            execute_msg = json.dumps({
                "type": "execute",
                "data": {
                    "command": "Check my wallet balance",
                    "plan": None
                }
            })
            await websocket.send(execute_msg)
            print("   ✓ Command sent")

            # Wait for thinking event
            print("\n5. Waiting for thinking event...")
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            message = json.loads(response)
            print(f"   Received: {message}")

            if message["type"] == "thinking":
                print("   ✓ Thinking event received")
            else:
                print(f"   ✗ Unexpected message type: {message['type']}")
                return False

            # Wait for complete event
            print("\n6. Waiting for complete event...")
            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            message = json.loads(response)
            print(f"   Received: {message}")

            if message["type"] == "complete":
                print("   ✓ Complete event received")
                print(f"   Success: {message['data'].get('success')}")
                return True
            elif message["type"] == "approval_required":
                print("   ✓ Approval required event received (expected for high-value)")
                return True
            else:
                print(f"   ✗ Unexpected message type: {message['type']}")
                return False

    except asyncio.TimeoutError:
        print("   ✗ Timeout waiting for message")
        return False
    except websockets.exceptions.InvalidStatus as e:
        print(f"   ✗ Connection rejected: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_latency():
    """Test WebSocket latency."""
    print("\n" + "=" * 60)
    print("WebSocket Latency Test")
    print("=" * 60)

    # Create a test session
    async for db in get_db():
        session_service = SessionService(db)
        session = await session_service.create_session(
            user_id=uuid.uuid4(),
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            config={"debug": True}
        )
        await db.commit()
        session_id = str(session.id)
        break

    uri = f"ws://localhost:8000/api/v1/ws?session_id={session_id}"

    latencies = []

    async with websockets.connect(uri) as websocket:
        # Wait for connection
        await websocket.recv()

        for i in range(3):
            start_time = datetime.now()

            execute_msg = json.dumps({
                "type": "execute",
                "data": {"command": f"test {i}", "plan": None}
            })
            await websocket.send(execute_msg)

            # Wait for thinking
            await asyncio.wait_for(websocket.recv(), timeout=10.0)
            end_time = datetime.now()

            latency_ms = (end_time - start_time).total_seconds() * 1000
            latencies.append(latency_ms)
            print(f"   Request {i+1}: {latency_ms:.2f}ms")

            # Wait for complete
            await asyncio.wait_for(websocket.recv(), timeout=30.0)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"\n   Average: {avg_latency:.2f}ms")
        print(f"   Max: {max_latency:.2f}ms")

        return max_latency < 100


async def main():
    """Run all tests."""
    print("\nStarting WebSocket QA tests...\n")

    # Test 1: Connection
    result1 = await test_websocket()

    # Test 2: Latency
    result2 = await test_latency()

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"WebSocket Connection: {'PASS' if result1 else 'FAIL'}")
    print(f"WebSocket Latency: {'PASS' if result2 else 'FAIL'}")
    print("=" * 60)

    return result1 and result2


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

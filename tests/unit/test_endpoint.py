"""
Simple test to check if the WebSocket endpoint is accessible.
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import requests


def test_websocket_endpoint():
    """Test if WebSocket endpoint is accessible."""
    try:
        # Test if the endpoint exists
        response = requests.get("http://localhost:8000/ws", timeout=5)
        print(f"HTTP GET to /ws: Status {response.status_code}")
        print(f"Response: {response.text[:100]}...")

    except requests.exceptions.ConnectionError:
        print("✗ Server not running or not accessible")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_websocket_endpoint()

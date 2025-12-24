#!/usr/bin/env python3
"""
Test script for Paygent agent execution.

This script tests the agent execution endpoint to ensure it works correctly.
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, Optional

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Import the FastAPI app
from src.main import app

# Import database models
from src.models import Base
from src.core.config import settings


async def setup_test_database():
    """Set up a test database for testing."""
    # Create test database engine
    test_url = settings.effective_database_url.replace("sqlite://", "sqlite+aiosqlite://")

    engine = create_async_engine(
        test_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


async def test_agent_execution():
    """Test the agent execution endpoint."""
    print("🧪 Testing Paygent Agent Execution...")

    # Set up test database
    engine = await setup_test_database()

    # Create test client
    client = TestClient(app)

    try:
        # Test 1: Health check
        print("✅ Test 1: Health check")
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        print(f"   Health check passed: {data}")

        # Test 2: Agent execution with payment command
        print("✅ Test 2: Agent execution - Payment command")
        payment_request = {
            "command": "Pay 0.10 USDC to access the market data API",
            "budget_limit_usd": 10.0
        }

        response = client.post("/api/v1/agent/execute", json=payment_request)
        print(f"   Response status: {response.status_code}")
        print(f"   Response body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Agent execution response: {data}")
            assert "session_id" in data
            assert "status" in data
            assert "success" in data
            print("   ✅ Payment command executed successfully")
        else:
            print(f"   ❌ Agent execution failed with status {response.status_code}")
            return False

        # Test 3: Agent execution with swap command
        print("✅ Test 3: Agent execution - Swap command")
        swap_request = {
            "command": "Swap 100 USDC for CRO on VVS Finance",
            "budget_limit_usd": 100.0
        }

        response = client.post("/api/v1/agent/execute", json=swap_request)
        print(f"   Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Swap command response: {data}")
            assert "session_id" in data
            assert "status" in data
            print("   ✅ Swap command executed successfully")
        else:
            print(f"   ❌ Swap execution failed with status {response.status_code}")
            return False

        # Test 4: Agent execution with balance check
        print("✅ Test 4: Agent execution - Balance check")
        balance_request = {
            "command": "Check my CRO and USDC balance"
        }

        response = client.post("/api/v1/agent/execute", json=balance_request)
        print(f"   Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Balance check response: {data}")
            assert "session_id" in data
            assert "status" in data
            print("   ✅ Balance check executed successfully")
        else:
            print(f"   ❌ Balance check failed with status {response.status_code}")
            return False

        print("\n🎉 All tests passed! Agent execution is working correctly.")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up
        await engine.dispose()


async def test_api_documentation():
    """Test that API documentation is accessible."""
    print("📄 Testing API Documentation...")

    client = TestClient(app)

    # Test OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_data = response.json()
    assert "paths" in openapi_data
    assert "/api/v1/agent/execute" in openapi_data["paths"]
    print("   ✅ OpenAPI schema is accessible")

    # Test Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text
    print("   ✅ Swagger UI is accessible")

    # Test ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "ReDoc" in response.text
    print("   ✅ ReDoc is accessible")

    print("   📚 All API documentation tests passed!")


async def main():
    """Main test function."""
    print("🚀 Starting Paygent Agent Tests...\n")

    # Test API documentation
    await test_api_documentation()
    print()

    # Test agent execution
    success = await test_agent_execution()

    if success:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("The Paygent agent execution system is working correctly.")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
"""
Test Vercel KV cache operations.

This test verifies that cache operations work correctly using fakeredis.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from fakeredis import FakeAsyncRedis


async def test_cache_operations():
    """Test cache set, get, delete operations."""

    # Set up mock Redis environment
    os.environ["USE_MOCK_REDIS"] = "true"

    # Import after setting env var
    from src.core.cache import cache_client

    print("=" * 60)
    print("Testing Vercel KV Cache Operations")
    print("=" * 60)

    # Step 1: Initialize cache
    print("\nStep 1: Initializing mock Redis cache...")
    success = await cache_client.connect()
    assert success, "Failed to connect to mock Redis"
    print("✓ Mock Redis connected successfully")

    # Step 2: Test SET operation
    print("\nStep 2: Testing SET operation...")
    test_key = f"test_key_{int(time.time())}"
    test_value = {"data": "test_value", "timestamp": time.time()}

    success = await cache_client.set(test_key, str(test_value), ttl=60)
    assert success, "SET operation failed"
    print(f"✓ Set key: {test_key}")

    # Step 3: Test GET operation
    print("\nStep 3: Testing GET operation...")
    retrieved_value = await cache_client.get(test_key)
    assert retrieved_value is not None, "GET operation failed - key not found"
    print(f"✓ Got value: {retrieved_value}")

    # Step 4: Verify value matches
    print("\nStep 4: Verifying value matches...")
    assert str(test_value) == retrieved_value, "Retrieved value doesn't match"
    print("✓ Value matches!")

    # Step 5: Test DELETE operation
    print("\nStep 5: Testing DELETE operation...")
    success = await cache_client.delete(test_key)
    assert success, "DELETE operation failed"
    print(f"✓ Deleted key: {test_key}")

    # Step 6: Verify deletion
    print("\nStep 6: Verifying deletion...")
    retrieved_value = await cache_client.get(test_key)
    assert retrieved_value is None, "Key still exists after deletion"
    print("✓ Key successfully deleted")

    # Step 7: Test TTL expiration
    print("\nStep 7: Testing TTL expiration...")
    ttl_key = f"ttl_key_{int(time.time())}"
    ttl_value = "expires_soon"

    # Set with 2 second TTL
    await cache_client.set(ttl_key, ttl_value, ttl=2)
    print(f"✓ Set key with 2 second TTL: {ttl_key}")

    # Immediately retrieve (should exist)
    retrieved_value = await cache_client.get(ttl_key)
    assert retrieved_value is not None, "Key should exist immediately after setting"
    print(f"✓ Key exists immediately: {retrieved_value}")

    # Wait for TTL to expire
    print("  Waiting 3 seconds for TTL to expire...")
    await asyncio.sleep(3)

    # Retrieve again (should be gone)
    retrieved_value = await cache_client.get(ttl_key)
    assert retrieved_value is None, "Key should have expired"
    print("✓ Key successfully expired after TTL")

    # Cleanup
    await cache_client.close()

    print("\n" + "=" * 60)
    print("✓ ALL CACHE TESTS PASSED!")
    print("=" * 60)

    return True


async def test_cache_api_endpoints():
    """Test cache API endpoints."""

    print("\n" + "=" * 60)
    print("Testing Cache API Endpoints")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test 1: Set value via API
        print("\nTest 1: Testing POST /api/v1/cache/test/set")
        test_key = f"api_test_{int(time.time())}"
        test_value = {"api": "test", "data": [1, 2, 3]}

        response = await client.post(
            "http://localhost:8000/api/v1/cache/test/set",
            json={"key": test_key, "value": test_value, "ttl_seconds": 60},
        )

        assert response.status_code == 200, f"Set endpoint failed: {response.text}"
        set_result = response.json()
        print(f"✓ Set via API: {set_result}")

        # Test 2: Get value via API
        print("\nTest 2: Testing GET /api/v1/cache/test/get/{key}")
        response = await client.get(
            f"http://localhost:8000/api/v1/cache/test/get/{test_key}"
        )

        assert response.status_code == 200, f"Get endpoint failed: {response.text}"
        get_result = response.json()
        print(f"✓ Got via API: {get_result}")

        # Test 3: Delete value via API
        print("\nTest 3: Testing DELETE /api/v1/cache/test/delete/{key}")
        response = await client.delete(
            f"http://localhost:8000/api/v1/cache/test/delete/{test_key}"
        )

        assert response.status_code == 200, f"Delete endpoint failed: {response.text}"
        delete_result = response.json()
        print(f"✓ Deleted via API: {delete_result}")

        # Test 4: Verify deletion
        print("\nTest 4: Verifying deletion via API")
        response = await client.get(
            f"http://localhost:8000/api/v1/cache/test/get/{test_key}"
        )

        assert response.status_code == 200
        get_result = response.json()
        assert not get_result["found"], "Key should not exist after deletion"
        print(f"✓ Verified deletion: {get_result}")

        # Test 5: Test TTL endpoint
        print("\nTest 5: Testing POST /api/v1/cache/test/ttl")
        response = await client.post(
            "http://localhost:8000/api/v1/cache/test/ttl", params={"ttl_seconds": 2}
        )

        assert response.status_code == 200, f"TTL endpoint failed: {response.text}"
        ttl_result = response.json()
        print(f"✓ TTL test result: {ttl_result}")

    print("\n" + "=" * 60)
    print("✓ ALL CACHE API TESTS PASSED!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Vercel KV Cache Operations Test Suite")
    print("=" * 60)

    # Test 1: Direct cache operations
    result1 = asyncio.run(test_cache_operations())

    # Test 2: API endpoints
    result2 = asyncio.run(test_cache_api_endpoints())

    if result1 and result2:
        print("\n" + "=" * 60)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("=" * 60)
        sys.exit(1)

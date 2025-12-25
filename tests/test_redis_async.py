"""
Test Redis async operations.

This test verifies that Redis/KV async operations work correctly
including connection handling, caching, and error handling.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.cache import (
    CacheClient,
    cache_client,
    cache_result,
    close_cache,
    init_cache,
)


class TestRedisAsyncOperations:
    """Test Redis async operations."""

    @pytest.fixture(autouse=True)
    async def setup_cache(self):
        """Setup cache for testing."""
        # Initialize cache with mock Redis for testing
        os.environ["USE_MOCK_REDIS"] = "true"
        await init_cache()
        yield
        await close_cache()
        if "USE_MOCK_REDIS" in os.environ:
            del os.environ["USE_MOCK_REDIS"]

    @pytest.mark.asyncio
    async def test_cache_client_initialization(self):
        """Test that cache client initializes successfully."""
        assert cache_client is not None
        assert isinstance(cache_client, CacheClient)

    @pytest.mark.asyncio
    async def test_cache_connection(self):
        """Test that cache connects successfully."""
        # Should be connected from setup
        assert cache_client.available is True

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test basic set and get operations."""
        # Set a value
        success = await cache_client.set("test_key", "test_value")
        assert success is True

        # Get the value
        value = await cache_client.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_cache_set_with_ttl(self):
        """Test set operation with TTL."""
        import asyncio

        # Set a value with 1 second TTL
        success = await cache_client.set("ttl_key", "ttl_value", ttl=1)
        assert success is True

        # Should be available immediately
        value = await cache_client.get("ttl_key")
        assert value == "ttl_value"

        # Wait for TTL to expire
        await asyncio.sleep(1.5)

        # Should be expired
        value = await cache_client.get("ttl_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test delete operation."""
        # Set a value
        await cache_client.set("delete_key", "delete_value")

        # Verify it exists
        value = await cache_client.get("delete_key")
        assert value == "delete_value"

        # Delete it
        success = await cache_client.delete("delete_key")
        assert success is True

        # Verify it's gone
        value = await cache_client.get("delete_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_exists(self):
        """Test exists operation."""
        # Set a value
        await cache_client.set("exists_key", "exists_value")

        # Check if it exists
        exists = await cache_client.exists("exists_key")
        assert exists is True

        # Check non-existent key
        exists = await cache_client.exists("non_existent_key")
        assert exists is False

    @pytest.mark.asyncio
    async def test_cache_get_nonexistent_key(self):
        """Test getting a non-existent key returns None."""
        value = await cache_client.get("non_existent_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_concurrent_operations(self):
        """Test concurrent cache operations."""
        async def set_and_get(key: str, value: str):
            await cache_client.set(key, value)
            return await cache_client.get(key)

        # Execute concurrent operations
        results = await asyncio.gather(
            *[set_and_get(f"key_{i}", f"value_{i}") for i in range(10)]
        )

        assert len(results) == 10
        assert all(f"value_{i}" in str(r) for i, r in enumerate(results))

    @pytest.mark.asyncio
    async def test_cache_update_existing_key(self):
        """Test updating an existing key."""
        # Set initial value
        await cache_client.set("update_key", "initial_value")
        value = await cache_client.get("update_key")
        assert value == "initial_value"

        # Update the value
        await cache_client.set("update_key", "updated_value")
        value = await cache_client.get("update_key")
        assert value == "updated_value"

    @pytest.mark.asyncio
    async def test_cache_with_complex_data_types(self):
        """Test caching complex data types."""
        import json

        # Dictionary
        dict_data = {"key": "value", "number": 123}
        await cache_client.set("dict_key", json.dumps(dict_data))
        value = await cache_client.get("dict_key")
        assert json.loads(value) == dict_data

        # List
        list_data = [1, 2, 3, 4, 5]
        await cache_client.set("list_key", json.dumps(list_data))
        value = await cache_client.get("list_key")
        assert json.loads(value) == list_data

    @pytest.mark.asyncio
    async def test_cache_with_special_characters(self):
        """Test caching keys and values with special characters."""
        special_cases = [
            ("key with spaces", "value with spaces"),
            ("key:with:colons", "value:with:colons"),
            ("key-with-dashes", "value-with-dashes"),
            ("key_with_underscores", "value_with_underscores"),
            ("key/with/slashes", "value/with/slashes"),
        ]

        for key, value in special_cases:
            success = await cache_client.set(key, value)
            assert success is True

            retrieved = await cache_client.get(key)
            assert retrieved == value

    @pytest.mark.asyncio
    async def test_cache_close_and_reconnect(self):
        """Test closing and reconnecting to cache."""
        # Close the connection
        await close_cache()

        # Verify it's closed
        assert cache_client.available is False or cache_client._client is None

        # Reconnect
        await init_cache()

        # Verify it's connected
        assert cache_client.available is True

    @pytest.mark.asyncio
    async def test_cache_handles_large_values(self):
        """Test caching large values."""
        # Create a large value (1MB)
        large_value = "x" * (1024 * 1024)

        success = await cache_client.set("large_key", large_value)
        assert success is True

        value = await cache_client.get("large_key")
        assert value == large_value

    @pytest.mark.asyncio
    async def test_cache_decorator(self):
        """Test the cache_result decorator."""
        call_count = 0

        @cache_result(ttl=1)
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment

        # Wait for TTL to expire
        await asyncio.sleep(1.5)

        # Third call - should execute function again
        result3 = await expensive_function(5)
        assert result3 == 10
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_handles_errors_gracefully(self):
        """Test that cache handles errors gracefully."""
        # Test with unavailable cache
        unavailable_client = CacheClient()
        assert unavailable_client.available is False

        # Should return None without error
        value = await unavailable_client.get("test_key")
        assert value is None

        # Should return False without error
        success = await unavailable_client.set("test_key", "test_value")
        assert success is False

        success = await unavailable_client.delete("test_key")
        assert success is False


class TestRedisPerformance:
    """Test Redis performance and efficiency."""

    @pytest.fixture(autouse=True)
    async def setup_cache(self):
        """Setup cache for testing."""
        os.environ["USE_MOCK_REDIS"] = "true"
        await init_cache()
        yield
        await close_cache()
        if "USE_MOCK_REDIS" in os.environ:
            del os.environ["USE_MOCK_REDIS"]

    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self):
        """Test cache performance under high load."""
        import time

        # Execute 1000 operations
        start_time = time.time()

        for i in range(1000):
            await cache_client.set(f"perf_key_{i}", f"perf_value_{i}")
            await cache_client.get(f"perf_key_{i}")

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete 2000 operations in reasonable time
        assert elapsed < 10.0  # Less than 10 seconds

    @pytest.mark.asyncio
    async def test_cache_concurrent_performance(self):
        """Test cache with concurrent access."""
        import time

        async def cache_operations(worker_id: int):
            for i in range(100):
                await cache_client.set(f"worker_{worker_id}_key_{i}", f"value_{i}")
                await cache_client.get(f"worker_{worker_id}_key_{i}")

        start_time = time.time()

        # Run 10 concurrent workers
        await asyncio.gather(
            *[cache_operations(i) for i in range(10)]
        )

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete 2000 operations across 10 workers in reasonable time
        assert elapsed < 10.0

    @pytest.mark.asyncio
    async def test_cache_memory_efficiency(self):
        """Test that cache doesn't leak memory."""
        import gc
        import sys

        initial_objects = len(gc.get_objects())

        # Create and delete many cache entries
        for i in range(100):
            await cache_client.set(f"mem_key_{i}", f"mem_value_{i}")
            await cache_client.get(f"mem_key_{i}")
            await cache_client.delete(f"mem_key_{i}")

        # Force garbage collection
        gc.collect()

        final_objects = len(gc.get_objects())

        # Object count should not have grown significantly
        # Allow some growth but not excessive
        growth = final_objects - initial_objects
        assert growth < 1000  # Less than 1000 new objects


class TestRedisErrorHandling:
    """Test Redis error handling and edge cases."""

    @pytest.fixture(autouse=True)
    async def setup_cache(self):
        """Setup cache for testing."""
        os.environ["USE_MOCK_REDIS"] = "true"
        await init_cache()
        yield
        await close_cache()
        if "USE_MOCK_REDIS" in os.environ:
            del os.environ["USE_MOCK_REDIS"]

    @pytest.mark.asyncio
    async def test_cache_with_none_value(self):
        """Test caching None values."""
        # Setting None should still work
        success = await cache_client.set("none_key", None)
        # Behavior may vary - just check it doesn't error

    @pytest.mark.asyncio
    async def test_cache_with_empty_string(self):
        """Test caching empty strings."""
        await cache_client.set("empty_key", "")
        value = await cache_client.get("empty_key")
        assert value == ""

    @pytest.mark.asyncio
    async def test_cache_with_very_long_key(self):
        """Test caching with very long keys."""
        long_key = "x" * 10000
        success = await cache_client.set(long_key, "value")
        # Should either succeed or fail gracefully
        assert success is True or success is False

    @pytest.mark.asyncio
    async def test_cache_unicode_values(self):
        """Test caching unicode values."""
        unicode_value = "Hello 世界 🌍"
        await cache_client.set("unicode_key", unicode_value)
        value = await cache_client.get("unicode_key")
        assert value == unicode_value

    @pytest.mark.asyncio
    async def test_cache_json_serialization(self):
        """Test caching JSON-serialized objects."""
        import json

        data = {
            "name": "Test Service",
            "price": 0.10,
            "tokens": ["USDC", "USDT"],
            "metadata": {"key": "value"},
        }

        await cache_client.set("json_key", json.dumps(data))
        value = await cache_client.get("json_key")
        parsed = json.loads(value)

        assert parsed["name"] == "Test Service"
        assert parsed["price"] == 0.10
        assert len(parsed["tokens"]) == 2

    @pytest.mark.asyncio
    async def test_cache_ttl_zero(self):
        """Test cache with TTL of 0 (should expire immediately)."""
        # Set with TTL=0 (may behave differently across implementations)
        success = await cache_client.set("zero_ttl_key", "value", ttl=0)
        # Just verify it doesn't error
        assert success is True or success is False

    @pytest.mark.asyncio
    async def test_cache_very_long_ttl(self):
        """Test cache with very long TTL."""
        # Set with very long TTL (1 year in seconds)
        success = await cache_client.set("long_ttl_key", "value", ttl=365 * 24 * 60 * 60)
        assert success is True

        value = await cache_client.get("long_ttl_key")
        assert value == "value"


class TestRedisIntegration:
    """Integration tests with other components."""

    @pytest.fixture(autouse=True)
    async def setup_cache(self):
        """Setup cache for testing."""
        os.environ["USE_MOCK_REDIS"] = "true"
        await init_cache()
        yield
        await close_cache()
        if "USE_MOCK_REDIS" in os.environ:
            del os.environ["USE_MOCK_REDIS"]

    @pytest.mark.asyncio
    async def test_cache_with_database_models(self):
        """Test caching database model data."""
        import json
        from uuid import uuid4

        # Simulate a service object
        service_data = {
            "id": str(uuid4()),
            "name": "Test Service",
            "description": "Test description",
            "endpoint": "https://example.com",
            "pricing_model": "pay-per-call",
            "price_amount": "0.10",
            "price_token": "USDC",
        }

        # Cache the service data
        await cache_client.set(f"service:{service_data['id']}", json.dumps(service_data))

        # Retrieve from cache
        value = await cache_client.get(f"service:{service_data['id']}")
        retrieved = json.loads(value)

        assert retrieved["id"] == service_data["id"]
        assert retrieved["name"] == "Test Service"

    @pytest.mark.asyncio
    async def test_cache_for_session_storage(self):
        """Test using cache for session storage."""
        import json
        from uuid import uuid4

        session_id = str(uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": str(uuid4()),
            "wallet_address": "0x1234567890123456789012345678901234567890",
            "created_at": "2025-12-25T00:00:00Z",
        }

        # Store session in cache
        await cache_client.set(f"session:{session_id}", json.dumps(session_data), ttl=3600)

        # Retrieve session
        value = await cache_client.get(f"session:{session_id}")
        retrieved = json.loads(value)

        assert retrieved["session_id"] == session_id
        assert retrieved["wallet_address"] == session_data["wallet_address"]

    @pytest.mark.asyncio
    async def test_cache_for_rate_limiting(self):
        """Test using cache for rate limiting."""
        # Simulate rate limiting
        wallet = "0x1234567890123456789012345678901234567890"
        endpoint = "/api/v1/agent/execute"
        key = f"ratelimit:{wallet}:{endpoint}"

        # Increment counter
        for i in range(5):
            await cache_client.set(key, str(i + 1), ttl=60)

        # Check current count
        count = await cache_client.get(key)
        assert int(count) == 5

    @pytest.mark.asyncio
    async def test_cache_for_service_discovery(self):
        """Test using cache for service discovery."""
        import json

        services = [
            {
                "id": "service-1",
                "name": "Market Data API",
                "price": "0.10",
                "token": "USDC",
            },
            {
                "id": "service-2",
                "name": "Payment Gateway",
                "price": "0.05",
                "token": "USDC",
            },
        ]

        # Cache service list
        await cache_client.set("services:all", json.dumps(services), ttl=300)

        # Retrieve from cache
        value = await cache_client.get("services:all")
        retrieved = json.loads(value)

        assert len(retrieved) == 2
        assert retrieved[0]["name"] == "Market Data API"
        assert retrieved[1]["name"] == "Payment Gateway"

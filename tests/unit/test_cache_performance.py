"""
Unit tests for cache layer performance.

Tests that the service cache returns results within 100ms target.
"""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_service_cache_performance_under_100ms():
    """Test that cached service discovery returns results within 100ms."""
    from src.core.database import init_db

    # Initialize database
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First request to populate cache
        start = time.time()
        response1 = await client.get("/api/v1/services/discover")
        first_request_time = (time.time() - start) * 1000  # Convert to ms

        assert response1.status_code == 200
        data1 = response1.json()
        services_count = len(data1.get("services", []))
        print(f"\nFirst request (cache miss): {first_request_time:.2f}ms - {services_count} services")

        # Second request should hit cache
        start = time.time()
        response2 = await client.get("/api/v1/services/discover")
        cache_hit_time = (time.time() - start) * 1000

        assert response2.status_code == 200
        data2 = response2.json()
        print(f"Second request (cache hit): {cache_hit_time:.2f}ms")

        # Verify cache hit is under 100ms
        assert cache_hit_time < 100, f"Cache hit took {cache_hit_time:.2f}ms, exceeds 100ms target"

        # Third request to confirm consistency
        start = time.time()
        response3 = await client.get("/api/v1/services/discover")
        third_request_time = (time.time() - start) * 1000

        assert response3.status_code == 200
        print(f"Third request (cache hit): {third_request_time:.2f}ms")

        # All cache hits should be under 100ms
        assert third_request_time < 100, f"Third request took {third_request_time:.2f}ms, exceeds 100ms target"

        print("\n✓ Cache performance test passed!")
        print(f"  - First request (miss): {first_request_time:.2f}ms")
        print(f"  - Cache hits: {cache_hit_time:.2f}ms, {third_request_time:.2f}ms")
        print("  - Target: <100ms ✓")


@pytest.mark.asyncio
async def test_service_cache_with_filters_performance():
    """Test that cached filtered service discovery returns results within 100ms."""
    from src.core.database import init_db

    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test with specific filter
        params = {"min_reputation": 3.0}

        # First request (miss)
        start = time.time()
        response1 = await client.get("/api/v1/services/discover", params=params)
        first_time = (time.time() - start) * 1000

        assert response1.status_code == 200
        print(f"\nFirst filtered request: {first_time:.2f}ms")

        # Second request (hit)
        start = time.time()
        response2 = await client.get("/api/v1/services/discover", params=params)
        cache_time = (time.time() - start) * 1000

        assert response2.status_code == 200
        print(f"Second filtered request (cached): {cache_time:.2f}ms")

        # Verify cache performance
        assert cache_time < 100, f"Filtered cache hit took {cache_time:.2f}ms, exceeds 100ms"

        print("✓ Filtered cache performance test passed!")


@pytest.mark.asyncio
async def test_service_pricing_cache_performance():
    """Test that pricing cache returns results within 100ms."""
    from src.core.database import init_db

    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Get a service ID first
        response = await client.get("/api/v1/services/discover")
        assert response.status_code == 200
        services = response.json().get("services", [])

        if services:
            service_id = services[0]["id"]

            # First pricing request (miss)
            start = time.time()
            response1 = await client.get(f"/api/v1/services/{service_id}/pricing")
            first_time = (time.time() - start) * 1000

            assert response1.status_code == 200
            print(f"\nFirst pricing request: {first_time:.2f}ms")

            # Second pricing request (hit)
            start = time.time()
            response2 = await client.get(f"/api/v1/services/{service_id}/pricing")
            cache_time = (time.time() - start) * 1000

            assert response2.status_code == 200
            print(f"Second pricing request (cached): {cache_time:.2f}ms")

            # Verify cache performance
            assert cache_time < 100, f"Pricing cache hit took {cache_time:.2f}ms, exceeds 100ms"

            print("✓ Pricing cache performance test passed!")


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        print("=" * 60)
        print("Cache Performance Tests")
        print("=" * 60)

        print("\n[Test 1] Basic service discovery cache performance")
        await test_service_cache_performance_under_100ms()

        print("\n[Test 2] Filtered service discovery cache performance")
        await test_service_cache_with_filters_performance()

        print("\n[Test 3] Service pricing cache performance")
        await test_service_pricing_cache_performance()

        print("\n" + "=" * 60)
        print("All cache performance tests passed! ✓")
        print("=" * 60)

    asyncio.run(run_tests())

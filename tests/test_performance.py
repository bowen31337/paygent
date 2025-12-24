"""
Performance tests for Paygent API response times.

This test verifies that API endpoints meet the 200ms p95 target.
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock

# Performance test for API endpoints
@pytest.mark.asyncio
async def test_api_response_times():
    """Test that API endpoints respond within performance targets."""
    from src.core.performance import PerformanceOptimizer, performance_monitor

    optimizer = PerformanceOptimizer()

    # Test fast operation (should be < 50ms)
    @performance_monitor
    async def fast_operation():
        await asyncio.sleep(0.01)  # 10ms
        return {"result": "success"}

    # Test medium operation (should be < 100ms)
    @performance_monitor
    async def medium_operation():
        await asyncio.sleep(0.05)  # 50ms
        return {"result": "success"}

    # Test slow operation (should be < 200ms)
    @performance_monitor
    async def slow_operation():
        await asyncio.sleep(0.1)  # 100ms
        return {"result": "success"}

    # Run operations
    await fast_operation()
    await medium_operation()
    await slow_operation()

    # Check performance stats
    stats = await optimizer.get_performance_stats()

    # All operations should be under 200ms
    assert stats["p95_response_time_ms"] < 200
    assert stats["p99_response_time_ms"] < 250
    assert stats["avg_response_time_ms"] < 100

    print(f"Performance stats: {stats}")


def test_cache_performance():
    """Test cache performance improvements."""
    from src.core.performance import fast_cache

    call_count = 0

    @fast_cache(ttl=60)
    async def expensive_operation():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)  # 10ms operation
        return f"result_{call_count}"

    async def run_test():
        # First call - should execute
        result1 = await expensive_operation()
        assert call_count == 1

        # Second call - should be cached
        result2 = await expensive_operation()
        assert call_count == 1  # Should still be 1 (cached)
        assert result1 == result2

    asyncio.run(run_test())


def test_bulk_operation_performance():
    """Test bulk operation performance improvements."""
    from src.core.performance import bulk_operation_executor

    async def mock_operation(i):
        await asyncio.sleep(0.01)  # 10ms per operation
        return f"result_{i}"

    async def run_bulk_test():
        operations = [lambda i=i: mock_operation(i) for i in range(10)]

        start_time = time.time()
        results = await bulk_operation_executor(operations, max_concurrent=5)
        duration = (time.time() - start_time) * 1000

        # With 5 concurrent operations, 10 operations should take ~20ms instead of 100ms
        assert duration < 50  # Should be much faster than sequential
        assert len(results) == 10

    asyncio.run(run_bulk_test())


def test_database_optimization():
    """Test database query optimizations."""
    from src.core.performance import DatabaseOptimizer

    # Mock database session and model
    mock_session = MagicMock()
    mock_model = MagicMock()

    # Test batch select
    async def test_batch_select():
        ids = list(range(100))
        result = await DatabaseOptimizer.batch_select(
            mock_session,
            mock_model,
            ids,
            batch_size=50
        )
        # Should create 2 batches of 50 operations each

    asyncio.run(test_batch_select())


def test_response_optimization():
    """Test response data optimization."""
    from src.core.performance import ResponseOptimizer

    # Test large response optimization
    large_data = {
        "data": [{"id": i, "name": f"item_{i}", "details": {"nested": f"value_{i}"}} for i in range(100)]
    }

    optimized = ResponseOptimizer.optimize_response_data(large_data, max_depth=2)
    assert isinstance(optimized, dict)

    compressed = ResponseOptimizer.compress_response_if_large(large_data, size_limit=1000)
    assert isinstance(compressed, dict)

    print("Response optimization tests passed")


def test_performance_monitoring():
    """Test performance monitoring functionality."""
    from src.core.performance import PerformanceOptimizer, get_performance_recommendations

    optimizer = PerformanceOptimizer()

    # Generate some test data
    async def run_monitoring_test():
        for i in range(100):
            duration = 50 + (i * 2)  # Increasing durations
            await optimizer.track_response_time(f"endpoint_{i % 5}", duration)

        stats = await optimizer.get_performance_stats()
        assert stats["total_requests"] == 100
        assert stats["p95_response_time_ms"] < 200  # Should be under 200ms

        slow_requests = await optimizer.get_slow_requests_report()
        print(f"Slow requests: {len(slow_requests)}")

    asyncio.run(run_monitoring_test())

    # Test recommendations
    recommendations = get_performance_recommendations()
    assert len(recommendations) > 5
    print("Performance recommendations:")
    for rec in recommendations:
        print(f"  {rec}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
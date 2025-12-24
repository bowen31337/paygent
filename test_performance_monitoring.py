#!/usr/bin/env python3
"""
Test script for performance monitoring and execution time tracking.

This script tests the performance monitoring system to ensure it works
correctly and provides accurate metrics.
"""

import asyncio
import time
import random
from src.core.monitoring import performance_monitor, Timer, PerformanceRegistry
from src.core.metrics import time_operation, track_performance


async def test_performance_monitoring():
    """Test the performance monitoring system."""
    print("🔍 Testing Performance Monitoring System")
    print("=" * 50)

    # Start monitoring
    performance_monitor.start_monitoring()

    # Test 1: Basic metrics recording
    print("\n1. Testing basic metrics recording...")

    # Record some API calls
    performance_monitor.record_api_call("/api/v1/agent/execute", "POST", 200, 150.5)
    performance_monitor.record_api_call("/api/v1/agent/execute", "POST", 500, 2000.0)
    performance_monitor.record_api_call("/api/v1/services", "GET", 200, 50.2)
    performance_monitor.record_api_call("/api/v1/wallet/balance", "GET", 404, 25.1)

    # Record some agent executions
    performance_monitor.record_agent_execution("session123", "pay 0.10 USDC", 1200.0, True)
    performance_monitor.record_agent_execution("session456", "check balance", 300.0, True)
    performance_monitor.record_agent_execution("session789", "swap CRO to USDC", 2500.0, False)

    # Record some payment operations
    performance_monitor.record_payment_operation("VVS", "swap", 1800.0, True)
    performance_monitor.record_payment_operation("Moonlander", "open_position", 900.0, True)
    performance_monitor.record_payment_operation("Delphi", "place_prediction", 450.0, False)

    # Record some cache operations
    performance_monitor.record_cache_operation("get", "redis", True, 2.5)
    performance_monitor.record_cache_operation("set", "redis", False, 5.0)
    performance_monitor.record_cache_operation("get", "local", True, 1.0)

    print("   ✓ Basic metrics recorded")

    # Test 2: Timer functionality
    print("\n2. Testing timer functionality...")

    # Test manual timing
    with Timer(performance_monitor.registry, "test.operation", {"type": "manual"}):
        time.sleep(0.1)  # Simulate work

    # Test async timing
    async def async_operation():
        await asyncio.sleep(0.05)
        return "completed"

    start_time = time.perf_counter()
    result = await async_operation()
    duration_ms = (time.perf_counter() - start_time) * 1000

    performance_monitor.registry.timer("test.async_operation", duration_ms, {"type": "async"})

    print("   ✓ Timer functionality working")

    # Test 3: Performance report generation
    print("\n3. Testing performance report generation...")

    report = performance_monitor.get_performance_report()

    print(f"   Report timestamp: {report['timestamp']}")
    print(f"   Total API calls: {report['summary']['total_api_calls']}")
    print(f"   Total agent executions: {report['summary']['total_agent_executions']}")
    print(f"   Total payments: {report['summary']['total_payments']}")

    # Test API performance analysis
    api_perf = report['api_performance']
    print(f"   Error rate: {api_perf['error_rate_percent']:.2f}%")

    # Test agent performance analysis
    agent_perf = report['agent_performance']
    print(f"   Agent success rate: {agent_perf['success_rate_percent']:.2f}%")

    # Test cache performance analysis
    cache_perf = report['cache_performance']
    print(f"   Cache hit rate: {cache_perf['hit_rate_percent']:.2f}%")

    print("   ✓ Performance report generated")

    # Test 4: Manual timing decorator
    print("\n4. Testing manual timing decorator...")

    @track_performance("test.decorator")
    async def decorated_function():
        await asyncio.sleep(0.03)
        return "decorated"

    start_time = time.perf_counter()
    result = await decorated_function()
    duration_ms = (time.perf_counter() - start_time) * 1000

    print(f"   ✓ Decorated function executed in {duration_ms:.2f}ms")

    # Test 5: Registry functionality
    print("\n5. Testing registry functionality...")

    # Test different metric types
    registry = PerformanceRegistry()

    # Test counter
    registry.counter("test.counter", {"type": "increment"})
    registry.counter("test.counter", {"type": "increment"})
    counter_value = registry.get_counter("test.counter", {"type": "increment"})
    print(f"   Counter value: {counter_value}")

    # Test gauge
    registry.gauge("test.gauge", 42.5, {"type": "temperature"})
    gauge_value = registry.get_gauge("test.gauge", {"type": "temperature"})
    print(f"   Gauge value: {gauge_value}")

    # Test histogram
    registry.histogram("test.histogram", 100.0, {"type": "response_time"})
    registry.histogram("test.histogram", 200.0, {"type": "response_time"})
    registry.histogram("test.histogram", 150.0, {"type": "response_time"})
    hist_stats = registry.get_histogram_stats("test.histogram", {"type": "response_time"})
    print(f"   Histogram count: {hist_stats.count}")
    print(f"   Histogram average: {hist_stats.get_average():.2f}")

    # Test timer
    registry.timer("test.timer", 100.0, {"type": "operation"})
    registry.timer("test.timer", 200.0, {"type": "operation"})
    timer_stats = registry.get_timer_stats("test.timer", {"type": "operation"})
    print(f"   Timer count: {timer_stats.count}")
    print(f"   Timer average: {timer_stats.get_average():.2f}ms")

    print("   ✓ Registry functionality working")

    # Test 6: Performance thresholds and alerts
    print("\n6. Testing performance thresholds...")

    # Simulate high error rate
    for i in range(10):
        performance_monitor.record_api_call("/api/v1/test", "GET", 500, 100.0)

    for i in range(90):
        performance_monitor.record_api_call("/api/v1/test", "GET", 200, 50.0)

    # Generate health check
    health_report = performance_monitor.get_performance_report()
    print("   ✓ Health check generated")

    # Test 7: Metrics export
    print("\n7. Testing metrics export...")

    raw_metrics = performance_monitor.registry.get_all_metrics()

    print(f"   Counters: {len(raw_metrics['counters'])} entries")
    print(f"   Gauges: {len(raw_metrics['gauges'])} entries")
    print(f"   Timers: {len(raw_metrics['timers'])} entries")
    print(f"   Labels: {len(raw_metrics['labels'])} entries")

    print("   ✓ Metrics export working")

    # Stop monitoring
    performance_monitor.stop_monitoring()

    print("\n" + "=" * 50)
    print("✅ Performance monitoring system test completed")


async def stress_test_performance_monitoring():
    """Stress test the performance monitoring system."""
    print("\n🧪 Running stress test...")

    start_time = time.time()

    # Simulate high load
    async def simulate_load():
        for i in range(100):
            # Simulate API calls
            performance_monitor.record_api_call(
                f"/api/v1/test{i % 10}",
                random.choice(["GET", "POST", "PUT"]),
                random.choice([200, 201, 400, 404, 500]),
                random.uniform(50, 2000)
            )

            # Simulate agent executions
            performance_monitor.record_agent_execution(
                f"session{i}",
                random.choice(["pay", "balance", "swap", "discover"]),
                random.uniform(100, 5000),
                random.choice([True, False])
            )

            # Simulate cache operations
            performance_monitor.record_cache_operation(
                random.choice(["get", "set", "delete"]),
                random.choice(["redis", "local"]),
                random.choice([True, False]),
                random.uniform(1, 50)
            )

            await asyncio.sleep(0.001)  # Small delay

    # Run concurrent load simulation
    tasks = [simulate_load() for _ in range(5)]
    await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    print(f"   Stress test completed in {elapsed:.2f} seconds")

    # Generate final report
    report = performance_monitor.get_performance_report()
    print(f"   Total API calls recorded: {report['summary']['total_api_calls']}")
    print(f"   Total agent executions: {report['summary']['total_agent_executions']}")


if __name__ == "__main__":
    asyncio.run(test_performance_monitoring())
    asyncio.run(stress_test_performance_monitoring())
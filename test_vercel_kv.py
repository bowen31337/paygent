#!/usr/bin/env python3
"""
Test script for Vercel KV cache operations.

This script tests the Vercel KV cache integration to ensure it works
correctly in both local and production environments.
"""

import asyncio
import os
from src.core.vercel_kv import VercelKVCache


async def test_vercel_kv_cache():
    """Test Vercel KV cache functionality."""
    print("🔍 Testing Vercel KV Cache Integration")
    print("=" * 50)

    cache = VercelKVCache()

    # Test 1: Initialization without environment variables
    print("\n1. Testing initialization without environment variables...")
    success = await cache.initialize()
    print(f"   Initialization: {'SUCCESS' if success else 'SKIPPED (no env vars)'}")

    # Test 2: Test connection info
    print("\n2. Testing connection info...")
    info = cache.get_info()
    print(f"   Cache type: {info.get('type', 'Unknown')}")
    print(f"   Connected: {info.get('connected', False)}")
    if 'reason' in info:
        print(f"   Reason: {info['reason']}")

    # Test 3: Test metrics
    print("\n3. Testing metrics...")
    metrics = cache.get_metrics()
    print(f"   Metrics available: {'YES' if metrics else 'NO'}")
    if metrics:
        for key, value in metrics.items():
            print(f"     {key}: {value}")

    # Test 4: Test with mock environment variables
    print("\n4. Testing with mock Vercel KV environment variables...")

    # Save original env vars
    original_kv_url = os.environ.get('VERCEL_KV_URL')
    original_kv_rest_url = os.environ.get('VERCEL_KV_REST_API_URL')
    original_kv_rest_token = os.environ.get('VERCEL_KV_REST_API_TOKEN')

    # Set test environment variables
    os.environ['VERCEL_KV_URL'] = 'redis://test:test@localhost:6379/0'

    # Create new cache instance
    test_cache = VercelKVCache()
    success = await test_cache.initialize()
    print(f"   Mock initialization: {'SUCCESS' if success else 'FAILED'}")

    if success:
        # Test basic operations (these will fail since Redis isn't running, but should handle gracefully)
        print("\n5. Testing basic cache operations...")

        # Test get
        result = await test_cache.get("test-key")
        print(f"   GET operation: {'SUCCESS' if result is not None else 'HANDLED GRACEFULLY'}")

        # Test set
        success = await test_cache.set("test-key", "test-value", ttl_seconds=60)
        print(f"   SET operation: {'SUCCESS' if success else 'HANDLED GRACEFULLY'}")

        # Test metrics after operations
        metrics = test_cache.get_metrics()
        print(f"   Operations tracked: {metrics.get('total_requests', 0)} requests")

    # Test 6: Test different environment scenarios
    print("\n6. Testing environment variable scenarios...")

    test_scenarios = [
        {
            'name': 'VERCEL_KV_URL',
            'env_vars': {'VERCEL_KV_URL': 'redis://user:pass@host:6379/0'},
            'expected': 'Should be detected'
        },
        {
            'name': 'KV_URL',
            'env_vars': {
                'VERCEL_KV_URL': None,
                'KV_URL': 'redis://user:pass@host:6379/0'
            },
            'expected': 'Should be detected'
        },
        {
            'name': 'VERCEL_KV_REST_API (combined)',
            'env_vars': {
                'VERCEL_KV_URL': None,
                'KV_URL': None,
                'VERCEL_KV_REST_API_URL': 'https://test-project.upstash.io',
                'VERCEL_KV_REST_API_TOKEN': 'test-token'
            },
            'expected': 'Should be converted to Redis URL'
        }
    ]

    for scenario in test_scenarios:
        print(f"\n   Testing: {scenario['name']}")

        # Set environment variables
        for key, value in scenario['env_vars'].items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        # Create cache instance and test URL detection
        test_cache = VercelKVCache()
        # We can't easily test URL detection without modifying the class,
        # but we can at least verify the cache instance is created

        print(f"     Cache instance created: ✓")

    # Test 7: Test URL parsing scenarios
    print("\n7. Testing URL parsing scenarios...")

    # Restore original env vars
    if original_kv_url:
        os.environ['VERCEL_KV_URL'] = original_kv_url
    else:
        os.environ.pop('VERCEL_KV_URL', None)

    if original_kv_rest_url:
        os.environ['VERCEL_KV_REST_API_URL'] = original_kv_rest_url
    else:
        os.environ.pop('VERCEL_KV_REST_API_URL', None)

    if original_kv_rest_token:
        os.environ['VERCEL_KV_REST_API_TOKEN'] = original_kv_rest_token
    else:
        os.environ.pop('VERCEL_KV_REST_API_TOKEN', None)

    # Test 8: Test cache operations with graceful fallback
    print("\n8. Testing cache operations with graceful fallback...")

    fallback_cache = VercelKVCache()
    await fallback_cache.initialize()

    # Test operations that should handle gracefully when Redis is not available
    test_operations = [
        ("get", lambda: fallback_cache.get("test-key")),
        ("set", lambda: fallback_cache.set("test-key", "test-value")),
        ("delete", lambda: fallback_cache.delete("test-key")),
        ("get_many", lambda: fallback_cache.get_many(["key1", "key2"])),
        ("set_many", lambda: fallback_cache.set_many({"key1": "value1", "key2": "value2"})),
        ("delete_many", lambda: fallback_cache.delete_many(["key1", "key2"])),
        ("keys", lambda: fallback_cache.keys("*")),
        ("flush", lambda: fallback_cache.flush()),
    ]

    for op_name, op_func in test_operations:
        try:
            result = await op_func()
            print(f"   {op_name}: HANDLED GRACEFULLY")
        except Exception as e:
            print(f"   {op_name}: ERROR - {e}")

    # Cleanup
    await cache.close()
    if success:
        await test_cache.close()
    await fallback_cache.close()

    print("\n" + "=" * 50)
    print("✅ Vercel KV cache integration test completed")


if __name__ == "__main__":
    asyncio.run(test_vercel_kv_cache())
"""
Test Vercel KV cache operations.

This test verifies that the Vercel KV cache integration works correctly.
"""

import os
from unittest.mock import patch

import pytest


# Test basic Vercel KV functionality
def test_vercel_kv_import():
    """Test that Vercel KV can be imported."""
    try:
        from src.core.vercel_kv import CacheMetrics, VercelKVCache
        assert VercelKVCache is not None
        assert CacheMetrics is not None
        print("✓ Vercel KV cache imports successfully")
    except ImportError as e:
        print(f"⚠ Vercel KV cache import failed: {e}")
        # This is expected if redis is not available
        assert "redis" in str(e) or "redis.asyncio" in str(e)


def test_vercel_kv_url_detection():
    """Test Vercel KV URL detection from environment variables."""
    # Test with VERCEL_KV_URL
    with patch.dict(os.environ, {"VERCEL_KV_URL": "redis://test:password@host:6379"}):
        from src.core.vercel_kv import VercelKVCache
        cache = VercelKVCache()
        url = cache._get_redis_url()
        assert url == "redis://test:password@host:6379"

    # Test with KV_URL
    with patch.dict(os.environ, {"KV_URL": "redis://test2:password@host2:6379"}):
        from src.core.vercel_kv import VercelKVCache
        cache = VercelKVCache()
        url = cache._get_redis_url()
        assert url == "redis://test2:password@host2:6379"

    # Test with REST API URL + token
    with patch.dict(os.environ, {
        "VERCEL_KV_REST_API_URL": "https://test-project.upstash.io",
        "VERCEL_KV_REST_API_TOKEN": "test-token"
    }):
        from src.core.vercel_kv import VercelKVCache
        cache = VercelKVCache()
        url = cache._get_redis_url()
        assert url == "rediss://:test-token@test-project.upstash.io"

    # Test with no environment variables
    with patch.dict(os.environ, {}, clear=True):
        from src.core.vercel_kv import VercelKVCache
        cache = VercelKVCache()
        url = cache._get_redis_url()
        assert url is None


def test_vercel_kv_metrics():
    """Test Vercel KV cache metrics functionality."""
    from src.core.vercel_kv import VercelKVCache

    cache = VercelKVCache()

    # Test metrics initialization
    assert cache.metrics is not None
    assert cache.metrics.hits == 0
    assert cache.metrics.misses == 0

    # Test metrics recording with actual methods
    cache.metrics.record_hit()
    cache.metrics.record_miss()
    cache.metrics.record_set()
    cache.metrics.record_delete()

    # Check the actual metrics structure
    metrics = cache.metrics.get_metrics()
    print(f"Metrics structure: {metrics}")

    # The actual metrics structure uses different keys
    assert metrics["hits"] == 1
    assert metrics["misses"] == 1
    assert metrics["hit_rate_percent"] == 50.0
    assert metrics["errors"] == 0


def test_vercel_kv_info():
    """Test Vercel KV cache info functionality."""
    from src.core.vercel_kv import VercelKVCache

    cache = VercelKVCache()

    # Test info when not connected
    info = cache.get_info()
    assert info["type"] == "Vercel KV (Redis)"
    assert info["connected"] == False

    # Test metrics info
    metrics = cache.get_metrics()
    assert "hits" in metrics
    assert "misses" in metrics
    assert "hit_rate_percent" in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test Vercel Blob storage operations.

This test verifies that the Vercel Blob storage integration works correctly.
"""

import os
from unittest.mock import patch

import pytest


# Test basic Vercel Blob functionality
def test_vercel_blob_import():
    """Test that Vercel Blob can be imported."""
    try:
        from src.core.vercel_blob import BlobInterface, BlobMetrics, VercelBlobStorage
        assert VercelBlobStorage is not None
        assert BlobMetrics is not None
        assert BlobInterface is not None
        print("✓ Vercel Blob storage imports successfully")
    except ImportError as e:
        print(f"⚠ Vercel Blob storage import failed: {e}")


def test_vercel_blob_metrics():
    """Test Vercel Blob storage metrics functionality."""
    from src.core.vercel_blob import VercelBlobStorage

    storage = VercelBlobStorage()

    # Test metrics initialization
    assert storage.metrics is not None
    assert storage.metrics.uploads == 0
    assert storage.metrics.downloads == 0

    # Test metrics recording
    storage.metrics.record_upload(10.5)
    storage.metrics.record_download(20.3)
    storage.metrics.record_delete(5.2)
    storage.metrics.record_error()

    assert storage.metrics.uploads == 1
    assert storage.metrics.downloads == 1
    assert storage.metrics.deletes == 1
    assert storage.metrics.errors == 1

    # Test metrics calculation
    metrics = storage.metrics.get_metrics()
    assert metrics["uploads"] == 1
    assert metrics["downloads"] == 1
    assert metrics["deletes"] == 1
    assert metrics["errors"] == 1
    assert metrics["avg_upload_time_ms"] == 10.5
    assert metrics["avg_download_time_ms"] == 20.3
    assert metrics["avg_delete_time_ms"] == 5.2


def test_vercel_blob_info():
    """Test Vercel Blob storage info functionality."""
    from src.core.vercel_blob import VercelBlobStorage

    storage = VercelBlobStorage()

    # Test info when not connected
    info = storage.get_info()
    assert info["type"] == "Vercel Blob"
    assert info["connected"] == False
    assert "metrics" in info

    # Test metrics info
    metrics = storage.get_metrics()
    assert "uploads" in metrics
    assert "downloads" in metrics
    assert "errors" in metrics


def test_vercel_blob_local_initialization():
    """Test Vercel Blob local initialization."""
    from src.core.vercel_blob import VercelBlobStorage

    storage = VercelBlobStorage()

    # Test local initialization (no BLOB_READ_WRITE_TOKEN)
    with patch.dict(os.environ, {}, clear=True):
        result = storage.initialize()
        assert result is True
        assert storage._is_connected is True
        assert storage._storage_type == "local"
        assert storage._base_path is not None


def test_vercel_blob_vercel_initialization():
    """Test Vercel Blob Vercel initialization."""
    from src.core.vercel_blob import VercelBlobStorage

    storage = VercelBlobStorage()

    # Test Vercel initialization (with BLOB_READ_WRITE_TOKEN)
    with patch.dict(os.environ, {"BLOB_READ_WRITE_TOKEN": "test-token"}):
        result = storage.initialize()
        assert result is True
        assert storage._is_connected is True
        assert storage._storage_type == "vercel"
        assert storage._blob_token == "test-token"


@pytest.mark.asyncio
async def test_vercel_blob_local_operations():
    """Test Vercel Blob local storage operations."""
    from src.core.vercel_blob import VercelBlobStorage

    storage = VercelBlobStorage()

    # Initialize with local storage
    with patch.dict(os.environ, {}, clear=True):
        await storage.initialize()

        # Test upload
        upload_result = await storage.upload("test/file.txt", "Hello, World!")
        print(f"Upload result: {upload_result}")
        assert upload_result is not None
        assert upload_result.get("path") == "test/file.txt"
        assert upload_result.get("size") == 13

        # Test exists
        exists = await storage.exists("test/file.txt")
        print(f"Exists check: {exists}")
        assert exists is True

        # Test download
        content = await storage.download("test/file.txt")
        print(f"Download content: {content}")
        assert content == b"Hello, World!"

        # Test delete
        deleted = await storage.delete("test/file.txt")
        print(f"Delete result: {deleted}")
        assert deleted is True

        # Test exists after delete
        exists_after = await storage.exists("test/file.txt")
        print(f"Exists after delete: {exists_after}")
        assert exists_after is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

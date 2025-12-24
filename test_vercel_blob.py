#!/usr/bin/env python3
"""
Test script for Vercel Blob storage operations.

This script tests the Vercel Blob storage integration to ensure it works
correctly in both local and production environments.
"""

import asyncio
import os
import tempfile
from src.core.vercel_blob import VercelBlobStorage


async def test_vercel_blob_storage():
    """Test Vercel Blob storage functionality."""
    print("🔍 Testing Vercel Blob Storage Integration")
    print("=" * 50)

    blob = VercelBlobStorage()

    # Test 1: Initialization without environment variables
    print("\n1. Testing initialization without environment variables...")
    success = await blob.initialize()
    print(f"   Initialization: {'SUCCESS' if success else 'FAILED'}")

    # Test 2: Test connection info
    print("\n2. Testing connection info...")
    info = blob.get_info()
    print(f"   Storage type: {info.get('type', 'Unknown')}")
    print(f"   Connected: {info.get('connected', False)}")
    print(f"   Storage mode: {info.get('storage_type', 'Unknown')}")
    if info.get('local_path'):
        print(f"   Local path: {info['local_path']}")

    # Test 3: Test metrics
    print("\n3. Testing metrics...")
    metrics = blob.get_metrics()
    print(f"   Metrics available: {'YES' if metrics else 'NO'}")
    if metrics:
        for key, value in metrics.items():
            print(f"     {key}: {value}")

    # Test 4: Test basic operations
    print("\n4. Testing basic blob operations...")

    # Test upload
    test_content = "Hello, this is test content for blob storage!"
    upload_result = await blob.upload("test/agent-logs/session1.log", test_content, "text/plain")
    print(f"   Upload: {'SUCCESS' if upload_result.get('success', False) else 'FAILED'}")
    print(f"   Uploaded: {upload_result.get('path', 'Unknown')} ({upload_result.get('size', 0)} bytes)")

    # Test exists
    exists = await blob.exists("test/agent-logs/session1.log")
    print(f"   Exists check: {'SUCCESS' if exists else 'FAILED'}")

    # Test download
    downloaded_content = await blob.download("test/agent-logs/session1.log")
    if downloaded_content:
        content_str = downloaded_content.decode('utf-8')
        print(f"   Download: {'SUCCESS' if content_str == test_content else 'FAILED'}")
        print(f"   Content matches: {'YES' if content_str == test_content else 'NO'}")
    else:
        print("   Download: FAILED (returned None)")

    # Test URL generation
    url = await blob.get_url("test/agent-logs/session1.log")
    print(f"   URL generation: {'SUCCESS' if url else 'FAILED'}")
    if url:
        print(f"   URL: {url}")

    # Test list
    files = await blob.list("test/")
    print(f"   List operation: SUCCESS ({len(files)} files found)")
    for file in files:
        print(f"     - {file}")

    # Test 5: Test multiple files and operations
    print("\n5. Testing multiple files and operations...")

    test_files = [
        ("logs/agent1/execution.log", "Agent 1 execution log"),
        ("logs/agent2/execution.log", "Agent 2 execution log"),
        ("reports/session1/report.json", json.dumps({"session": "session1", "status": "completed"})),
        ("reports/session2/report.json", json.dumps({"session": "session2", "status": "in_progress"})),
    ]

    upload_results = []
    for path, content in test_files:
        result = await blob.upload(path, content, "application/json" if path.endswith(".json") else "text/plain")
        upload_results.append(result)

    successful_uploads = len([r for r in upload_results if r.get('success', False)])
    print(f"   Multiple uploads: {successful_uploads} successful")

    # List with prefix
    log_files = await blob.list("logs/")
    print(f"   Log files found: {len(log_files)}")
    for file in log_files:
        print(f"     - {file}")

    report_files = await blob.list("reports/")
    print(f"   Report files found: {len(report_files)}")
    for file in report_files:
        print(f"     - {file}")

    # Test 6: Test delete operations
    print("\n6. Testing delete operations...")

    # Delete one file
    deleted = await blob.delete("test/agent-logs/session1.log")
    print(f"   Delete single file: {'SUCCESS' if deleted else 'FAILED'}")

    exists_after_delete = await blob.exists("test/agent-logs/session1.log")
    print(f"   Exists after delete: {'NO' if not exists_after_delete else 'YES (should be NO)'}")

    # Test delete multiple files
    delete_count = 0
    for path, _ in test_files:
        if await blob.delete(path):
            delete_count += 1

    print(f"   Multiple deletes: {delete_count} files deleted")

    # Test 7: Test error handling
    print("\n7. Testing error handling...")

    # Test operations on non-existent files
    non_existent_download = await blob.download("non/existent/file.txt")
    print(f"   Download non-existent: {'HANDLED GRACEFULLY' if non_existent_download is None else 'FAILED'}")

    non_existent_delete = await blob.delete("non/existent/file.txt")
    print(f"   Delete non-existent: {'HANDLED GRACEFULLY' if not non_existent_delete else 'FAILED'}")

    # Test operations when not connected
    # (We can't easily test this without modifying the class, but we can at least verify the current state)

    # Test 8: Test with environment variables
    print("\n8. Testing with environment variables...")

    # Save original env vars
    original_token = os.environ.get('BLOB_READ_WRITE_TOKEN')
    original_local_path = os.environ.get('LOCAL_BLOB_PATH')

    # Test with Vercel token
    os.environ['BLOB_READ_WRITE_TOKEN'] = 'test-token'
    if original_local_path:
        os.environ['LOCAL_BLOB_PATH'] = original_local_path

    # Create new blob instance
    test_blob = VercelBlobStorage()
    success = await test_blob.initialize()
    print(f"   Vercel token initialization: {'SUCCESS' if success else 'FAILED'}")

    if success:
        info = test_blob.get_info()
        print(f"   Storage mode: {info.get('storage_type', 'Unknown')}")

    # Test with local path
    os.environ.pop('BLOB_READ_WRITE_TOKEN', None)
    os.environ['LOCAL_BLOB_PATH'] = tempfile.mkdtemp()

    test_blob2 = VercelBlobStorage()
    success2 = await test_blob2.initialize()
    print(f"   Local path initialization: {'SUCCESS' if success2 else 'FAILED'}")

    if success2:
        info2 = test_blob2.get_info()
        print(f"   Local path: {info2.get('local_path', 'Unknown')}")

    # Restore original env vars
    if original_token:
        os.environ['BLOB_READ_WRITE_TOKEN'] = original_token
    else:
        os.environ.pop('BLOB_READ_WRITE_TOKEN', None)

    if original_local_path:
        os.environ['LOCAL_BLOB_PATH'] = original_local_path
    else:
        os.environ.pop('LOCAL_BLOB_PATH', None)

    # Test 9: Test metrics after operations
    print("\n9. Testing metrics after operations...")
    final_metrics = blob.get_metrics()
    print(f"   Total uploads: {final_metrics.get('uploads', 0)}")
    print(f"   Total downloads: {final_metrics.get('downloads', 0)}")
    print(f"   Total deletes: {final_metrics.get('deletes', 0)}")
    print(f"   Errors: {final_metrics.get('errors', 0)}")

    # Cleanup
    await blob.close()
    if success:
        await test_blob.close()
    if success2:
        await test_blob2.close()

    print("\n" + "=" * 50)
    print("✅ Vercel Blob storage integration test completed")


if __name__ == "__main__":
    import json
    asyncio.run(test_vercel_blob_storage())
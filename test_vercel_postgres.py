#!/usr/bin/env python3
"""
Test script for Vercel Postgres connection validation.

This script tests the Vercel Postgres integration to ensure it works
correctly in both local and production environments.
"""

import asyncio
import os
from src.core.vercel_db import (
    get_database_url,
    test_connection,
    check_database_health,
    get_sync_engine,
    close_db
)
from sqlalchemy import text


async def test_vercel_postgres():
    """Test Vercel Postgres connection and functionality."""
    print("🔍 Testing Vercel Postgres Integration")
    print("=" * 50)

    # Test 1: Check database URL detection
    print("\n1. Testing database URL detection...")
    db_url = get_database_url()
    print(f"   Detected database URL: {db_url}")

    # Test 2: Test connection
    print("\n2. Testing database connection...")
    try:
        connection_success = await test_connection()
        print(f"   ✓ Connection test: {'SUCCESS' if connection_success else 'FAILED'}")
    except Exception as e:
        print(f"   ✗ Connection test: FAILED - {e}")
        connection_success = False

    # Test 3: Database health check
    print("\n3. Testing database health...")
    try:
        health_status = await check_database_health()
        print(f"   Health status: {health_status['status']}")
        print(f"   Database URL: {health_status.get('database_url', 'N/A')}")
        if 'pool_size' in health_status:
            print(f"   Pool size: {health_status['pool_size']}")
            print(f"   Checked in: {health_status['checked_in_connections']}")
            print(f"   Checked out: {health_status['checked_out_connections']}")
    except Exception as e:
        print(f"   ✗ Health check: FAILED - {e}")

    # Test 4: Test synchronous engine for Alembic
    print("\n4. Testing synchronous engine (for Alembic)...")
    try:
        sync_engine = get_sync_engine()
        if sync_engine:
            print("   ✓ Synchronous engine created successfully")
            # Test connection with sync engine
            with sync_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print(f"   ✓ Sync connection test: {result.scalar()}")
        else:
            print("   → SQLite detected, skipping sync engine test")
    except Exception as e:
        print(f"   ✗ Sync engine test: FAILED - {e}")

    # Test 5: Test different environment scenarios
    print("\n5. Testing environment scenarios...")

    # Save original env vars
    original_postgres_url = os.environ.get('POSTGRES_URL')
    original_non_pooling = os.environ.get('POSTGRES_URL_NON_POOLING')
    original_database_url = os.environ.get('DATABASE_URL')

    test_scenarios = [
        {
            'name': 'Vercel Production (POSTGRES_URL)',
            'env_vars': {'POSTGRES_URL': 'postgresql://user:pass@host:5432/db'},
            'expected_source': 'POSTGRES_URL'
        },
        {
            'name': 'Vercel Non-Pooling (POSTGRES_URL_NON_POOLING)',
            'env_vars': {
                'POSTGRES_URL': None,
                'POSTGRES_URL_NON_POOLING': 'postgresql://user:pass@host:5432/db'
            },
            'expected_source': 'POSTGRES_URL_NON_POOLING'
        },
        {
            'name': 'Local Development (DATABASE_URL)',
            'env_vars': {
                'POSTGRES_URL': None,
                'POSTGRES_URL_NON_POOLING': None,
                'DATABASE_URL': 'sqlite:///test.db'
            },
            'expected_source': 'DATABASE_URL'
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

        # Test URL detection
        detected_url = get_database_url()
        print(f"     Detected URL: {detected_url}")

        # Clean up
        for key in scenario['env_vars'].keys():
            os.environ.pop(key, None)

    # Restore original env vars
    if original_postgres_url:
        os.environ['POSTGRES_URL'] = original_postgres_url
    if original_non_pooling:
        os.environ['POSTGRES_URL_NON_POOLING'] = original_non_pooling
    if original_database_url:
        os.environ['DATABASE_URL'] = original_database_url

    # Test 6: Connection pooling settings
    print("\n6. Testing connection pool settings...")
    from src.core.vercel_db import engine
    try:
        pool_size = engine.pool.size() if hasattr(engine.pool, 'size') else 'N/A'
        print(f"   Pool size: {pool_size}")
        print(f"   Pool recycle: {engine.pool._recycle}")
        print(f"   Pool pre-ping: {engine.pool._pre_ping}")
    except Exception as e:
        print(f"   ✗ Pool settings: ERROR - {e}")

    await close_db()
    print("\n" + "=" * 50)
    print("✅ Vercel Postgres integration test completed")


if __name__ == "__main__":
    asyncio.run(test_vercel_postgres())
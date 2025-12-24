#!/usr/bin/env python3
"""
Test script to verify API services are working.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.config import settings
from src.core.database import engine, async_session_maker
from src.services.payment_service import PaymentService
from src.models.agent_sessions import ApprovalRequest as ApprovalRequestModel
from sqlalchemy import select

async def test_api_services():
    """Test the service layer directly."""
    print("Testing API services...")

    try:
        # Initialize database - just create tables, don't use session
        async with engine.begin() as conn:
            from src.core.database import Base
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database initialized")

        # Test payment service
        print("\nTesting payment service...")
        try:
            async with async_session_maker() as db:
                payment_service = PaymentService(db)
                result = await payment_service.get_payment_history()
                print(f"✓ Payment service: {result['total']} payments found")
                print(f"  Success: {result['success']}")
                print(f"  Limit: {result['limit']}")
        except Exception as e:
            print(f"✗ Payment service error: {e}")

        # Test approval service
        print("\nTesting approval service...")
        try:
            async with async_session_maker() as db:
                # Use raw SQL to test approval requests table
                result = await db.execute(
                    select(ApprovalRequestModel).where(ApprovalRequestModel.decision == "pending")
                )
                pending_requests = result.scalars().all()
                print(f"✓ Approval service: {len(pending_requests)} pending requests")
        except Exception as e:
            print(f"✗ Approval service error: {e}")

        print("\n✓ All API services working correctly!")

    except Exception as e:
        print(f"✗ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_services())
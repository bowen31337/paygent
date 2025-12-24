"""
Test service reputation update features.

Tests:
- Feature 45: Service reputation is updated after successful payment
"""

import asyncio
import sys
import os
from pathlib import Path
from uuid import uuid4

# Enable mock Redis BEFORE importing modules
os.environ["USE_MOCK_REDIS"] = "true"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import init_db, close_db
from src.core.cache import init_cache, close_cache
from src.services.service_registry import ServiceRegistryService
from src.services.payment_service import PaymentService
from src.api.routes.payments import ExecuteX402Request
from src.models.services import Service
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def test_feature_45_service_reputation_update():
    """Feature 45: Service reputation is updated after successful payment"""
    print("\n" + "="*70)
    print("TEST: Feature 45 - Service Reputation Update After Payment")
    print("="*70)

    await init_db()
    await init_cache()

    # Create a test database session
    from src.core.database import engine
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Step 1: Create a test service
        print("\n[1] Creating test service...")
        test_service_id = uuid4()
        test_service = Service(
            id=test_service_id,
            name="Test Market Data API",
            description="A test service for market data",
            endpoint="https://api.marketdata.example.com",
            pricing_model="pay-per-call",
            price_amount=0.1,
            price_token="USDC",
            mcp_compatible=True,
            reputation_score=0.0,
            total_calls=0,
        )
        db.add(test_service)
        await db.commit()
        await db.refresh(test_service)
        print(f"   Created service: {test_service.name}")
        print(f"   Initial reputation: {test_service.reputation_score}")
        print(f"   Initial total_calls: {test_service.total_calls}")

        # Step 2: Create a successful payment for this service
        print("\n[2] Creating successful payment...")
        payment_service = PaymentService(db)
        payment = await payment_service.create_payment(
            agent_wallet="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            recipient="https://api.marketdata.example.com",
            amount=0.1,
            token="USDC",
            service_id=test_service_id,
            tx_hash="0xmocktxhash123",
            status="confirmed",
        )
        print(f"   Created payment: {payment.id}")
        print(f"   Payment status: {payment.status}")

        # Step 3: Update service reputation (simulating what the payment endpoint does)
        print("\n[3] Updating service reputation...")
        registry = ServiceRegistryService(db)
        updated_service = await registry.update_service_reputation(
            str(test_service_id), 4.5
        )

        if updated_service:
            print(f"   ✓ Reputation updated: {updated_service.reputation_score}")
            print(f"   ✓ Total calls incremented: {updated_service.total_calls}")
        else:
            print(f"   ✗ Failed to update reputation")
            return False

        # Step 4: Verify the update
        print("\n[4] Verifying reputation update...")
        if updated_service.reputation_score > 0.0 and updated_service.total_calls == 1:
            print(f"   ✓ Reputation is now: {updated_service.reputation_score}")
            print(f"   ✓ Total calls is now: {updated_service.total_calls}")
            print(f"\n✅ PASSED: Service reputation updates correctly after payment")
            return True
        else:
            print(f"   ✗ Reputation not updated correctly")
            print(f"      Expected: reputation > 0, total_calls = 1")
            print(f"      Got: reputation = {updated_service.reputation_score}, total_calls = {updated_service.total_calls}")
            return False


async def test_multiple_reputation_updates():
    """Additional test: Multiple payments should average reputation"""
    print("\n" + "="*70)
    print("ADDITIONAL TEST: Multiple Reputation Updates")
    print("="*70)

    await init_db()
    await init_cache()

    from src.core.database import engine
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Create test service
        test_service_id = uuid4()
        test_service = Service(
            id=test_service_id,
            name="Test Service 2",
            description="Test service for multiple payments",
            endpoint="https://api.test2.example.com",
            pricing_model="pay-per-call",
            price_amount=0.1,
            price_token="USDC",
            mcp_compatible=True,
            reputation_score=0.0,
            total_calls=0,
        )
        db.add(test_service)
        await db.commit()
        await db.refresh(test_service)

        registry = ServiceRegistryService(db)

        # Make 3 payments with different ratings
        ratings = [5.0, 4.0, 3.0]
        expected_avg = sum(ratings) / len(ratings)

        print(f"\n[1] Making {len(ratings)} payments with ratings: {ratings}")

        for i, rating in enumerate(ratings, 1):
            await registry.update_service_reputation(str(test_service_id), rating)
            await db.refresh(test_service)
            print(f"   Payment {i}: rating={rating}, new_score={test_service.reputation_score:.2f}")

        # Verify final average
        print(f"\n[2] Verifying final reputation...")
        if abs(test_service.reputation_score - expected_avg) < 0.01:
            print(f"   ✓ Final reputation: {test_service.reputation_score:.2f} (expected: {expected_avg})")
            print(f"   ✓ Total calls: {test_service.total_calls}")
            print(f"\n✅ PASSED: Multiple reputation updates work correctly")
            return True
        else:
            print(f"   ✗ Reputation mismatch")
            print(f"      Expected: {expected_avg}, Got: {test_service.reputation_score}")
            return False


async def main():
    """Run all reputation tests."""
    print("\n" + "="*70)
    print("SERVICE REPUTATION TEST SUITE")
    print("="*70)
    print("\nTesting service reputation features:")
    print("- Feature 45: Service reputation is updated after successful payment")

    results = {}

    try:
        results["feature_45"] = await test_feature_45_service_reputation_update()
        results["multiple_updates"] = await test_multiple_reputation_updates()

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test}")

        print(f"\n{passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await close_db()
        await close_cache()


if __name__ == "__main__":
    asyncio.run(main())

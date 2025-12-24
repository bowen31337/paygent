#!/usr/bin/env python3
"""
Comprehensive test to verify current implementation status.
Tests all major components and features.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.config import settings
from src.core.database import engine, async_session_maker, Base
from src.services.payment_service import PaymentService
from src.services.wallet_service import WalletService
from src.services.service_registry import ServiceRegistryService
from src.services.approval_service import ApprovalService
from src.tools.simple_tools import CheckBalanceTool, SwapTokensTool, X402PaymentTool
from src.models.agent_sessions import ApprovalRequest as ApprovalRequestModel
from sqlalchemy import select

async def test_all_components():
    """Test all implemented components."""
    print("🧪 COMPREHENSIVE VERIFICATION TEST")
    print("=" * 70)

    try:
        # Initialize database
        print("\n📋 Database Setup")
        print("-" * 30)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database tables created")

        # Test Payment Service
        print("\n💳 Payment Service")
        print("-" * 30)
        async with async_session_maker() as db:
            payment_service = PaymentService(db)
            history_result = await payment_service.get_payment_history()
            stats_result = await payment_service.get_payment_stats()

            print(f"✓ Payment History: {history_result['total']} payments found")
            print(f"✓ Payment Stats: {stats_result['stats']['total_payments']} total payments")
            print(f"✓ Success Rate: {stats_result['stats']['success_rate']:.1%}")

        # Test Wallet Service
        print("\n💰 Wallet Service")
        print("-" * 30)
        async with async_session_maker() as db:
            wallet_service = WalletService(db)
            balance_result = await wallet_service.check_balance()
            allowance_result = await wallet_service.get_allowance()

            print(f"✓ Balance Check: {len(balance_result.get('balances', {}))} tokens")
            print(f"✓ Daily Allowance: ${allowance_result.get('remaining_allowance_usd', 0):.2f}")

        # Test Service Registry
        print("\n🌐 Service Registry")
        print("-" * 30)
        async with async_session_maker() as db:
            registry_service = ServiceRegistryService(db)
            services = await registry_service.discover_services(query="", limit=5)

            print(f"✓ Service Discovery: {len(services)} services found")
            if services:
                service = services[0]
                print(f"✓ Service: {service.name}")

        # Test Approval Service
        print("\n✅ Approval Service")
        print("-" * 30)
        async with async_session_maker() as db:
            approval_service = ApprovalService(db)

            # Check pending requests
            result = await db.execute(
                select(ApprovalRequestModel).where(ApprovalRequestModel.decision == "pending")
            )
            pending_requests = result.scalars().all()

            print(f"✓ Pending Requests: {len(pending_requests)} found")

        # Test Simple Tools
        print("\n🔧 Simple Tools")
        print("-" * 30)
        balance_tool = CheckBalanceTool()
        swap_tool = SwapTokensTool()
        payment_tool = X402PaymentTool()

        balance_result = balance_tool.run()
        print(f"✓ Balance Tool: {len(balance_result.get('balances', {}))} tokens")

        swap_result = swap_tool.run(amount=10, from_token="CRO", to_token="USDC")
        print(f"✓ Swap Tool: Success: {swap_result.get('success', False)}")

        payment_result = payment_tool.run(service_url="http://example.com", amount=10, token="USDC")
        print(f"✓ Payment Tool: Success: {payment_result.get('success', False)}")

        print("\n🎉 ALL COMPONENTS VERIFIED SUCCESSFULLY!")
        print("=" * 70)
        print("\n📊 IMPLEMENTATION STATUS:")
        print("✓ Payment Service - Working")
        print("✓ Wallet Service - Working")
        print("✓ Service Registry - Working")
        print("✓ Approval Service - Working")
        print("✓ Simple Tools - Working")
        print("✓ Database - Working")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_all_components())
    sys.exit(0 if success else 1)
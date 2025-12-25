"""
Comprehensive tests for approval workflow features.

Tests:
- Feature 59: GET /api/v1/approvals/pending lists pending approval requests
- Feature 60: POST /api/v1/approvals/{request_id}/approve resumes agent execution
- Feature 61: POST /api/v1/approvals/{request_id}/reject stops agent execution
- Feature 62: POST /api/v1/approvals/{request_id}/edit allows modifying args before approval
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from httpx import AsyncClient, TimeoutException
from sqlalchemy import select

from src.core.database import get_db
from src.models.agent_sessions import ApprovalRequest


async def test_feature_59_list_pending():
    """Feature 59: GET /api/v1/approvals/pending lists pending approval requests"""
    print("\n" + "="*70)
    print("TEST: Feature 59 - List Pending Approvals")
    print("="*70)

    async with AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        print("\n[1] Testing pending approvals endpoint...")
        response = await client.get("/api/v1/approvals/pending")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Total requests: {data['total']}")
            print(f"✓ Requests returned: {len(data['requests'])}")
            if data['requests']:
                for req in data['requests'][:3]:  # Show first 3
                    print(f"  - {req['id']}: {req['tool_name']} ({req['decision']})")
            print("\n✅ PASSED: Pending approvals endpoint works")
            return True
        else:
            print(f"✗ FAILED: Status {response.status_code}")
            print(f"  Response: {response.text}")
            return False


async def test_feature_60_approve_request():
    """Feature 60: POST /api/v1/approvals/{request_id}/approve resumes agent execution"""
    print("\n" + "="*70)
    print("TEST: Feature 60 - Approve Request")
    print("="*70)

    # First create a mock approval request
    request_id = None
    async for db in get_db():
        try:
            # Create a test approval request
            mock_request = ApprovalRequest(
                id=uuid4(),
                session_id=uuid4(),
                tool_name="transfer_tokens",
                tool_args={"amount": 100.0, "recipient": "0x1234..."},
                decision="pending",
            )
            db.add(mock_request)
            await db.commit()
            request_id = mock_request.id
            print(f"\n[1] Created test approval request: {request_id}")
        except Exception as e:
            print(f"✗ Failed to create test request: {e}")
        finally:
            await db.close()
            break

    if not request_id:
        print("\n⚠️  SKIPPED: Could not create test request")
        return False

    async with AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        print("\n[2] Testing approve endpoint...")
        response = await client.post(f"/api/v1/approvals/{request_id}/approve")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Request ID: {data['request_id']}")
            print(f"✓ Decision: {data['decision']}")
            print(f"✓ Message: {data['message']}")
            print("\n✅ PASSED: Approve endpoint works")
            return True
        else:
            print(f"✗ FAILED: Status {response.status_code}")
            print(f"  Response: {response.text}")
            return False


async def test_feature_61_reject_request():
    """Feature 61: POST /api/v1/approvals/{request_id}/reject stops agent execution"""
    print("\n" + "="*70)
    print("TEST: Feature 61 - Reject Request")
    print("="*70)

    # First create a mock approval request
    request_id = None
    async for db in get_db():
        try:
            # Create a test approval request
            mock_request = ApprovalRequest(
                id=uuid4(),
                session_id=uuid4(),
                tool_name="transfer_tokens",
                tool_args={"amount": 500.0, "recipient": "0x5678..."},
                decision="pending",
            )
            db.add(mock_request)
            await db.commit()
            request_id = mock_request.id
            print(f"\n[1] Created test approval request: {request_id}")
        except Exception as e:
            print(f"✗ Failed to create test request: {e}")
        finally:
            await db.close()
            break

    if not request_id:
        print("\n⚠️  SKIPPED: Could not create test request")
        return False

    async with AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        print("\n[2] Testing reject endpoint...")
        response = await client.post(
            f"/api/v1/approvals/{request_id}/reject",
            json={"reason": "Testing rejection"}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Request ID: {data['request_id']}")
            print(f"✓ Decision: {data['decision']}")
            print(f"✓ Message: {data['message']}")
            print("\n✅ PASSED: Reject endpoint works")
            return True
        else:
            print(f"✗ FAILED: Status {response.status_code}")
            print(f"  Response: {response.text}")
            return False


async def test_feature_62_edit_and_approve():
    """Feature 62: POST /api/v1/approvals/{request_id}/edit allows modifying args before approval"""
    print("\n" + "="*70)
    print("TEST: Feature 62 - Edit and Approve")
    print("="*70)

    # First create a mock approval request
    request_id = None
    async for db in get_db():
        try:
            # Create a test approval request with high amount
            mock_request = ApprovalRequest(
                id=uuid4(),
                session_id=uuid4(),
                tool_name="transfer_tokens",
                tool_args={"amount": 200.0, "recipient": "0xabcd..."},
                decision="pending",
            )
            db.add(mock_request)
            await db.commit()
            request_id = mock_request.id
            print(f"\n[1] Created test approval request: {request_id}")
            print("    Original amount: $200")
        except Exception as e:
            print(f"✗ Failed to create test request: {e}")
        finally:
            await db.close()
            break

    if not request_id:
        print("\n⚠️  SKIPPED: Could not create test request")
        return False

    async with AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        print("\n[2] Testing edit and approve endpoint...")
        print("    Reducing amount to $50...")

        edited_args = {"amount": 50.0, "recipient": "0xabcd..."}
        response = await client.post(
            f"/api/v1/approvals/{request_id}/edit",
            json={"edited_args": edited_args}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Request ID: {data['request_id']}")
            print(f"✓ Decision: {data['decision']}")
            print(f"✓ Message: {data['message']}")
            print("\n✅ PASSED: Edit and approve endpoint works")
            return True
        else:
            print(f"✗ FAILED: Status {response.status_code}")
            print(f"  Response: {response.text}")
            return False


async def test_feature_63_get_approval_request():
    """Additional test: GET /api/v1/approvals/{request_id} returns request details"""
    print("\n" + "="*70)
    print("TEST: Additional - Get Approval Request Details")
    print("="*70)

    # Get a request ID from the database
    request_id = None
    async for db in get_db():
        try:
            result = await db.execute(
                select(ApprovalRequest).limit(1)
            )
            req = result.scalar_one_or_none()
            if req:
                request_id = req.id
                print(f"\n[1] Found approval request: {request_id}")
        except Exception as e:
            print(f"✗ Failed to query request: {e}")
        finally:
            await db.close()
            break

    if not request_id:
        # Create one
        async for db in get_db():
            try:
                mock_request = ApprovalRequest(
                    id=uuid4(),
                    session_id=uuid4(),
                    tool_name="test_tool",
                    tool_args={"test": True},
                    decision="pending",
                )
                db.add(mock_request)
                await db.commit()
                request_id = mock_request.id
                print(f"\n[1] Created test approval request: {request_id}")
            except Exception as e:
                print(f"✗ Failed to create test request: {e}")
            finally:
                await db.close()
                break

    if not request_id:
        print("\n⚠️  SKIPPED: Could not get/create test request")
        return False

    async with AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        print("\n[2] Testing get approval request endpoint...")
        response = await client.get(f"/api/v1/approvals/{request_id}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Request ID: {data['id']}")
            print(f"✓ Tool: {data['tool_name']}")
            print(f"✓ Decision: {data['decision']}")
            print(f"✓ Args: {data['tool_args']}")
            print("\n✅ PASSED: Get approval request endpoint works")
            return True
        else:
            print(f"✗ FAILED: Status {response.status_code}")
            print(f"  Response: {response.text}")
            return False


async def main():
    """Run all approval workflow tests."""
    print("\n" + "="*70)
    print("APPROVAL WORKFLOW TEST SUITE")
    print("="*70)
    print("\nTesting approval workflow features:")
    print("- Feature 59: List pending approvals")
    print("- Feature 60: Approve request")
    print("- Feature 61: Reject request")
    print("- Feature 62: Edit and approve")
    print("- Additional: Get approval request details")

    results = {}

    try:
        # Check server is running
        async with AsyncClient(base_url="http://localhost:8000", timeout=5.0) as client:
            health = await client.get("/health")
            if health.status_code != 200:
                print(f"\n❌ Server health check failed: {health.status_code}")
                return

        # Run tests
        results["feature_59"] = await test_feature_59_list_pending()
        results["feature_60"] = await test_feature_60_approve_request()
        results["feature_61"] = await test_feature_61_reject_request()
        results["feature_62"] = await test_feature_62_edit_and_approve()
        results["get_request"] = await test_feature_63_get_approval_request()

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

    except TimeoutException:
        print("\n❌ ERROR: Server not responding. Is it running on port 8000?")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

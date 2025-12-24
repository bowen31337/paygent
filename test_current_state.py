#!/usr/bin/env python3
"""Test current state of the agent executor."""
import sys
sys.path.insert(0, '.')
import asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
from sqlalchemy import select
from src.core.database import get_db
from src.models.agent_sessions import ExecutionLog

async def test():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        print('=== TESTING ENHANCED AGENT EXECUTOR ===')
        print()

        # Test 1: Payment with plan generation
        print('1. Testing payment command with write_todos plan:')
        response = await client.post(
            '/api/v1/agent/execute',
            json={
                'command': 'Pay 0.10 USDC to access the market data API',
                'budget_limit_usd': 10.0
            }
        )
        print(f'   Status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'   Success: {data.get("result", {}).get("success")}')
            print(f'   Action: {data.get("result", {}).get("action")}')
            plan = data.get('result', {}).get('plan')
            if plan:
                print(f'   Plan generated: Yes')
                print(f'   Approach: {plan.get("approach")}')
                print(f'   Steps: {len(plan.get("steps", []))}')
            tool_calls = data.get('result', {}).get('tool_calls')
            if tool_calls:
                print(f'   Tool calls logged: {len(tool_calls)}')
        print()

        # Test 2: Balance check
        print('2. Testing balance check:')
        response = await client.post(
            '/api/v1/agent/execute',
            json={'command': 'Check my wallet balance'}
        )
        print(f'   Status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'   Success: {data.get("result", {}).get("success")}')
        print()

        # Test 3: Swap with plan
        print('3. Testing swap command with plan:')
        response = await client.post(
            '/api/v1/agent/execute',
            json={'command': 'Swap 100 CRO for USDC'}
        )
        print(f'   Status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'   Success: {data.get("result", {}).get("success")}')
            plan = data.get('result', {}).get('plan')
            if plan:
                print(f'   Plan generated: Yes')
                print(f'   Steps: {len(plan.get("steps", []))}')
        print()

        # Test 4: Budget enforcement
        print('4. Testing budget limit enforcement:')
        response = await client.post(
            '/api/v1/agent/execute',
            json={
                'command': 'Pay 50 USDC to API service',
                'budget_limit_usd': 10.0
            }
        )
        print(f'   Status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'   Success: {data.get("result", {}).get("success")}')
            if not data.get('result', {}).get('success'):
                error = data.get('result', {}).get('error', '')
                print(f'   Budget enforced: Yes')
                print(f'   Error: {error[:80]}...')
        print()

        # Test 5: Check execution logs
        print('5. Checking execution logs in database:')
        async for db in get_db():
            result = await db.execute(select(ExecutionLog).limit(5))
            logs = result.scalars().all()
            print(f'   Total logs found: {len(logs)}')
            if logs:
                for log in logs:
                    print(f'   - Log {log.id}: {log.status}, {log.duration_ms}ms, ${log.total_cost}')
            break

        print()
        print('=== ALL TESTS COMPLETED ===')

if __name__ == '__main__':
    asyncio.run(test())

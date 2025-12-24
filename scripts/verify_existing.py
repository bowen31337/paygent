#!/usr/bin/env python
"""Verify existing passing features still work."""
import httpx
import asyncio
import sys


async def verify_features():
    """Verify passing features still work."""
    results = []

    async with httpx.AsyncClient() as client:
        base = "http://localhost:8000"

        # Test 1: Health check
        try:
            resp = await client.get(f"{base}/health", timeout=2.0)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            results.append(("Health check", True, None))
        except Exception as e:
            results.append(("Health check", False, str(e)))

        # Test 2: OpenAPI docs
        try:
            resp = await client.get(f"{base}/docs", timeout=2.0)
            assert resp.status_code == 200
            results.append(("OpenAPI docs accessible", True, None))
        except Exception as e:
            results.append(("OpenAPI docs", False, str(e)))

        # Test 3: API root
        try:
            resp = await client.get(f"{base}/", timeout=2.0)
            assert resp.status_code == 200
            data = resp.json()
            assert "docs" in data
            results.append(("API root endpoint", True, None))
        except Exception as e:
            results.append(("API root", False, str(e)))

        # Test 4: Service discovery
        try:
            resp = await client.get(f"{base}/api/v1/services/discover", timeout=2.0)
            assert resp.status_code == 200
            data = resp.json()
            assert "services" in data or isinstance(data, list)
            results.append(("Service discovery", True, None))
        except Exception as e:
            results.append(("Service discovery", False, str(e)))

        # Test 5: Agent execute endpoint
        try:
            resp = await client.post(
                f"{base}/api/v1/agent/execute",
                json={"command": "test"},
                timeout=2.0
            )
            # May fail validation, that's okay
            results.append(("Agent execute endpoint exists", resp.status_code in [200, 202, 400, 422], None))
        except Exception as e:
            results.append(("Agent execute endpoint", False, str(e)))

    print("\n=== VERIFICATION RESULTS ===\n")
    for name, success, error in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
        if error and not success:
            print(f"  Error: {error[:80]}")

    passed = sum(1 for _, success, _ in results if success)
    print(f"\n{passed}/{len(results)} checks passed")

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(verify_features())
    sys.exit(0 if success else 1)

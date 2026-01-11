"""
Test Vercel deployment configuration for Paygent.

This script verifies that the Vercel deployment setup is correct and ready for deployment.
It checks:
1. API entry point exists and is valid
2. vercel.json configuration is correct
3. requirements.txt is complete
4. .vercelignore is properly configured
5. Health endpoint works
"""

import json
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx


def test_api_entry_point():
    """Test that the Vercel API entry point exists and is valid."""
    print("\n✓ Testing API entry point...")

    api_file = Path("api/index.py")
    if not api_file.exists():
        print("  ✗ FAIL: api/index.py does not exist")
        return False

    print("  ✓ api/index.py exists")

    # Check that the file imports the app
    content = api_file.read_text()
    if "from src.main import app" not in content:
        print("  ✗ FAIL: api/index.py does not import app from src.main")
        return False

    print("  ✓ api/index.py imports FastAPI app correctly")

    # Check that handler is exported
    if "handler = app" not in content:
        print("  ✗ FAIL: api/index.py does not export handler")
        return False

    print("  ✓ api/index.py exports handler for Vercel")
    return True


def test_vercel_json():
    """Test that vercel.json is properly configured."""
    print("\n✓ Testing vercel.json configuration...")

    vercel_file = Path("vercel.json")
    if not vercel_file.exists():
        print("  ✗ FAIL: vercel.json does not exist")
        return False

    print("  ✓ vercel.json exists")

    try:
        config = json.loads(vercel_file.read_text())
    except json.JSONDecodeError as e:
        print(f"  ✗ FAIL: vercel.json is not valid JSON: {e}")
        return False

    print("  ✓ vercel.json is valid JSON")

    # Check version
    if config.get("version") != 2:
        print("  ✗ FAIL: vercel.json version is not 2")
        return False

    print("  ✓ vercel.json version is 2")

    # Check builds
    builds = config.get("builds", [])
    if not builds:
        print("  ✗ FAIL: vercel.json has no builds")
        return False

    print(f"  ✓ vercel.json has {len(builds)} build(s)")

    # Check that api/index.py is in builds
    api_build = None
    for build in builds:
        if build.get("src") == "api/index.py":
            api_build = build
            break

    if not api_build:
        print("  ✗ FAIL: api/index.py is not in builds")
        return False

    print("  ✓ api/index.py is in builds")

    # Check Python runtime
    use = api_build.get("use")
    if use != "@vercel/python":
        print(f"  ✗ FAIL: api/index.py uses {use}, not @vercel/python")
        return False

    print("  ✓ api/index.py uses @vercel/python")

    # Check runtime version
    runtime = api_build.get("config", {}).get("runtime")
    if not runtime or not runtime.startswith("python3."):
        print(f"  ✗ FAIL: Invalid runtime: {runtime}")
        return False

    print(f"  ✓ Runtime is {runtime}")

    # Check routes
    routes = config.get("routes", [])
    if not routes:
        print("  ✗ FAIL: vercel.json has no routes")
        return False

    print(f"  ✓ vercel.json has {len(routes)} route(s)")

    return True


def test_requirements_txt():
    """Test that requirements.txt exists and is complete."""
    print("\n✓ Testing requirements.txt...")

    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("  ✗ FAIL: requirements.txt does not exist")
        return False

    print("  ✓ requirements.txt exists")

    # Check for key dependencies
    requirements = req_file.read_text()

    key_packages = [
        "fastapi",
        "uvicorn",
        "langchain",
        "sqlalchemy",
        "asyncpg",
        "redis",
        "httpx",
        "pydantic",
    ]

    missing = []
    for package in key_packages:
        if package.lower() not in requirements.lower():
            missing.append(package)

    if missing:
        print(f"  ✗ FAIL: Missing key packages: {', '.join(missing)}")
        return False

    print(f"  ✓ All key packages present ({len(key_packages)} checked)")

    # Count total packages
    lines = [line.strip() for line in requirements.strip().split("\n") if line.strip()]
    print(f"  ✓ requirements.txt has {len(lines)} packages")

    return True


def test_vercelignore():
    """Test that .vercelignore exists and has proper entries."""
    print("\n✓ Testing .vercelignore...")

    vercelignore_file = Path(".vercelignore")
    if not vercelignore_file.exists():
        print("  ✗ FAIL: .vercelignore does not exist")
        return False

    print("  ✓ .vercelignore exists")

    content = vercelignore_file.read_text()

    # Check for key ignore patterns
    key_patterns = [
        ".env",
        ".venv",
        "__pycache__",
        "tests/",
        "*.pyc",
        "node_modules/",
        ".git/",
    ]

    missing = []
    for pattern in key_patterns:
        if pattern not in content:
            missing.append(pattern)

    if missing:
        print(f"  ⚠ WARNING: Missing common ignore patterns: {', '.join(missing)}")

    print(f"  ✓ .vercelignore has {len(content.splitlines())} ignore patterns")

    return True


def test_health_endpoint():
    """Test that the health endpoint works."""
    print("\n✓ Testing health endpoint...")

    try:
        response = httpx.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print(f"  ✗ FAIL: Health endpoint returned {response.status_code}")
            return False

        print("  ✓ Health endpoint returned 200")

        data = response.json()
        if data.get("status") != "healthy":
            print(f"  ✗ FAIL: Health status is not healthy: {data}")
            return False

        print("  ✓ Health status is healthy")
        print(f"  ✓ Version: {data.get('version')}")
        print(f"  ✓ Environment: {data.get('environment')}")

        return True
    except Exception as e:
        print(f"  ✗ FAIL: Could not connect to health endpoint: {e}")
        print("  ⚠ Make sure the server is running: uv run uvicorn src.main:app --reload")
        return False


def test_api_docs():
    """Test that API documentation endpoints work."""
    print("\n✓ Testing API documentation...")

    try:
        # Try OpenAPI JSON
        response = httpx.get("http://localhost:8000/openapi.json", timeout=5)
        if response.status_code != 200:
            print(f"  ✗ FAIL: OpenAPI JSON returned {response.status_code}")
            return False

        print("  ✓ OpenAPI JSON endpoint works")

        openapi = response.json()
        if not openapi.get("openapi"):
            print("  ✗ FAIL: OpenAPI JSON does not contain 'openapi' key")
            return False

        print(f"  ✓ OpenAPI version: {openapi.get('openapi')}")

        # Check info
        info = openapi.get("info", {})
        print(f"  ✓ Title: {info.get('title')}")
        print(f"  ✓ Version: {info.get('version')}")

        return True
    except Exception as e:
        print(f"  ✗ FAIL: Could not get OpenAPI JSON: {e}")
        return False


def main():
    """Run all Vercel deployment tests."""
    print("=" * 70)
    print("Vercel Deployment Configuration Test")
    print("=" * 70)

    tests = [
        ("API Entry Point", test_api_entry_point),
        ("vercel.json", test_vercel_json),
        ("requirements.txt", test_requirements_txt),
        (".vercelignore", test_vercelignore),
        ("Health Endpoint", test_health_endpoint),
        ("API Documentation", test_api_docs),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n  ✗ ERROR in {name}: {e}")
            results[name] = False

    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n✓ All tests passed! Vercel deployment is ready.")
        print("\nNext steps:")
        print("  1. Install Vercel CLI: npm install -g vercel")
        print("  2. Link your project: vercel link")
        print("  3. Set environment variables in Vercel dashboard:")
        print("     - ANTHROPIC_API_KEY")
        print("     - CRONOS_RPC_URL")
        print("     - DATABASE_URL (Vercel Postgres)")
        print("     - REDIS_URL (Vercel KV)")
        print("  4. Deploy: vercel --prod")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

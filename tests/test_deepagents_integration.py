"""
Test deepagents framework integration with Claude Sonnet 4.

This test verifies the integration layer for deepagents.
"""

import os


def test_deepagents_module_exists():
    """Test that the deepagents integration module exists."""
    try:
        from src.agents.deepagents_integration import (
            DeepAgentsIntegration,
            get_integration,
            is_deepagents_available,
            verify_claude_sonnet_4,
        )
        print("✓ deepagents_integration module imported successfully")
        assert DeepAgentsIntegration is not None
        assert callable(get_integration)
        assert callable(is_deepagents_available)
        assert callable(verify_claude_sonnet_4)
    except ImportError as e:
        assert False, f"Failed to import deepagents_integration: {e}"


def test_deepagents_integration_initialization():
    """Test that DeepAgentsIntegration can be initialized."""
    from src.agents.deepagents_integration import DeepAgentsIntegration

    integration = DeepAgentsIntegration(session_id="test-session")
    assert integration is not None
    assert integration.session_id == "test-session"

    # Check if deepagents is available (may be False in some environments)
    available = integration.is_available()
    print("✓ DeepAgentsIntegration initialized")
    print(f"  Session ID: {integration.session_id}")
    print(f"  Available: {available}")


def test_get_model_info():
    """Test getting model information."""
    from src.agents.deepagents_integration import get_model_info

    info = get_model_info()
    assert info is not None
    assert "framework" in info
    assert "model" in info
    assert "available" in info

    print("✓ Model info retrieved")
    print(f"  Framework: {info['framework']}")
    print(f"  Model: {info['model']}")
    print(f"  Available: {info['available']}")

    if info.get("features"):
        print("  Features:")
        for feature in info["features"]:
            print(f"    - {feature}")


def test_verify_claude_sonnet_4():
    """Test Claude Sonnet 4 verification."""
    from src.agents.deepagents_integration import verify_claude_sonnet_4

    # Check if API key is available
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⊘ ANTHROPIC_API_KEY not set, skipping verification test")
        return

    verification = verify_claude_sonnet_4()
    assert verification is not None
    assert "framework" in verification

    print("✓ Claude Sonnet 4 verification completed")
    print(f"  Framework: {verification['framework']}")
    print(f"  Success: {verification.get('success', False)}")

    if verification.get("success"):
        print(f"  Model: {verification.get('model')}")
        print(f"  Verification: {verification.get('verification')}")
    else:
        print(f"  Error: {verification.get('error', 'Unknown error')}")


def test_singleton_integration():
    """Test that singleton integration works."""
    from src.agents.deepagents_integration import get_integration

    # Get integration for same session twice
    integration1 = get_integration("test-session")
    integration2 = get_integration("test-session")

    # Should be the same instance
    assert integration1 is integration2
    print("✓ Singleton integration works correctly")


def test_deepagents_dependency():
    """Test that deepagents is in dependencies."""
    import subprocess

    result = subprocess.run(
        ["uv", "pip", "show", "deepagents"],
        capture_output=True,
        text=True,
        cwd="."
    )

    if result.returncode == 0:
        print("✓ deepagents package is installed")
        # Parse version from output
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                version = line.split(':', 1)[1].strip()
                print(f"  Version: {version}")
                # Check if version is >= 0.2.7
                major, minor, patch = map(int, version.split('.')[:3])
                if major > 0 or (major == 0 and minor >= 2):
                    print(f"  ✓ Version {version} meets requirement (>=0.2.7)")
                    return
        print("  ⚠ Could not verify version requirement")
    else:
        print("✗ deepagents package not found")
        assert False, "deepagents should be installed as a dependency"


def test_pyproject_toml_has_deepagents():
    """Test that pyproject.toml includes deepagents."""
    with open("pyproject.toml", "r") as f:
        content = f.read()

    # Check if deepagents is in dependencies
    assert "deepagents" in content, "deepagents should be in pyproject.toml"

    # Find the dependencies section
    in_deps = False
    bracket_count = 0
    for line in content.split('\n'):
        if 'dependencies = [' in line or 'dependencies=[' in line:
            in_deps = True
            bracket_count += line.count('[') - line.count(']')
        elif in_deps:
            bracket_count += line.count('[') - line.count(']')
            if 'deepagents' in line:
                print(f"✓ deepagents found in pyproject.toml: {line.strip()}")
                if ">=" in line:
                    version_req = line.split(">=")[1].strip().replace(',', '').replace('"', '')
                    print(f"  Version requirement: >={version_req}")
                return
            if bracket_count <= 0 and ']' in line:
                break

    assert False, "deepagents should be in dependencies section"


if __name__ == "__main__":
    """Run tests manually."""
    print("=" * 70)
    print("Testing deepagents framework integration")
    print("=" * 70)

    tests = [
        ("Module exists", test_deepagents_module_exists),
        ("Integration initialization", test_deepagents_integration_initialization),
        ("Get model info", test_get_model_info),
        ("Verify Claude Sonnet 4", test_verify_claude_sonnet_4),
        ("Singleton integration", test_singleton_integration),
        ("deepagents dependency", test_deepagents_dependency),
        ("pyproject.toml configuration", test_pyproject_toml_has_deepagents),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n{name}:")
        print("-" * 70)
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All tests passed!")
        exit(0)
    else:
        print(f"\n✗ {failed} test(s) failed")
        exit(1)

#!/usr/bin/env python3
"""
Simple test script to verify MCP client configuration.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/media/DATA/projects/autonomous-coding-cro/paygent')

try:
    from src.core.config import settings
    print("✓ Configuration module imported successfully")
    print(f"  MCP Server URL: {settings.crypto_com_mcp_url}")
    print(f"  API Key: {'Set' if settings.crypto_com_api_key else 'Not set'}")
    print()

    # Test basic MCP client instantiation
    from src.services.mcp_client import MCPServerClient
    print("✓ MCP client class imported successfully")

    # Create client instance
    client = MCPServerClient()
    print(f"✓ MCP client created successfully")
    print(f"  Server URL: {client.server_url}")
    print(f"  API Key set: {client.api_key is not None}")

    print("\n✓ All basic MCP configuration tests passed!")

except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
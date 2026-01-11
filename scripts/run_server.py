#!/usr/bin/env python3
"""
Server startup script for Paygent.

This script sets up the Python path and starts the FastAPI server.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path (go up one level from scripts/)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables from .env if it exists
env_path = project_root / '.env'
if os.path.exists(env_path):
    from dotenv import load_dotenv
    load_dotenv(env_path)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )

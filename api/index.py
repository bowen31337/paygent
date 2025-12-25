"""
Vercel serverless function entry point for Paygent FastAPI application.

This file serves as the bridge between Vercel's serverless functions and the FastAPI app.
It handles the ASGI interface and ensures proper request/response handling.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app

# Vercel Python runtime looks for this handler
# The ASGI app is exposed directly for Vercel to use
handler = app

# Export for Vercel
__all__ = ["app", "handler"]

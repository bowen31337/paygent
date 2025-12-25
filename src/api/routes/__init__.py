"""
API routes package.

This package contains all FastAPI route modules organized by domain.
"""

from . import agent, approvals, defi, logs, metrics, payments, services, simple_agent, wallet, websocket

__all__ = ["agent", "services", "payments", "wallet", "approvals", "logs", "websocket", "defi", "metrics"]

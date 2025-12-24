"""
API routes package.

This package contains all FastAPI route modules organized by domain.
"""

from . import agent, services, payments, wallet, approvals, logs, websocket, defi, metrics

__all__ = ["agent", "services", "payments", "wallet", "approvals", "logs", "websocket", "defi", "metrics"]

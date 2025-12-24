"""
API routes package.

This package contains all FastAPI route modules organized by domain.
"""

from src.api.routes import agent, services, payments, wallet, approvals, logs

__all__ = ["agent", "services", "payments", "wallet", "approvals", "logs"]

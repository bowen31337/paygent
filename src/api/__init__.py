"""
API module containing FastAPI routes and endpoints.

This module provides the main API router that includes all sub-routers
for different API domains (agent, services, payments, wallet, approvals, logs).
"""

from fastapi import APIRouter

from src.api.routes import (
    agent,
    services,
    payments,
    wallet,
    approvals,
    logs,
)

router = APIRouter()

# Include all route modules
router.include_router(agent.router, prefix="/agent", tags=["Agent"])
router.include_router(services.router, prefix="/services", tags=["Services"])
router.include_router(payments.router, prefix="/payments", tags=["Payments"])
router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
router.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
router.include_router(logs.router, prefix="/logs", tags=["Logs"])

__all__ = ["router"]

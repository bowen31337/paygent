"""
Paygent - AI-Powered Multi-Agent Payment Orchestration Platform

This package contains the main application source code for the Paygent platform,
which enables autonomous AI agents to discover, negotiate, and execute payments
seamlessly across the Cronos ecosystem using the x402 protocol.

Key modules:
    - api: FastAPI routes and endpoints
    - agents: AI agent implementations with deepagents/LangGraph
    - middleware: Custom middleware for x402 payments, wallet, and registry
    - connectors: DeFi protocol connectors (VVS, Moonlander, Delphi)
    - x402: x402 payment protocol implementation
    - models: SQLAlchemy database models
    - schemas: Pydantic request/response schemas
    - services: Business logic layer
    - core: Configuration and database setup
"""

__version__ = "0.1.0"
__author__ = "Paygent Team"

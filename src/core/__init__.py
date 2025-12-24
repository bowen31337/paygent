"""
Core module containing configuration, settings, and database connection.

This module provides:
    - config: Application settings and environment variable management
    - database: Database connection and session management
"""

from src.core.config import settings
from src.core.database import get_db, engine, Base

__all__ = ["settings", "get_db", "engine", "Base"]

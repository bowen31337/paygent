"""
Service registry models.

This module defines the SQLAlchemy models for service registry and discovery.
"""

from sqlalchemy import Column, String, Text, Float, Boolean, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from datetime import datetime
from uuid import UUID

from src.core.database import Base


class Service(Base):
    """Service registry model for discovered and registered services."""

    __tablename__ = "services"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(50), nullable=False)  # pay-per-call, subscription, metered
    price_amount: Mapped[float] = mapped_column(Float, nullable=False)
    price_token: Mapped[str] = mapped_column(String(42), nullable=False)
    mcp_compatible: Mapped[bool] = mapped_column(Boolean, default=False)
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_calls: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name='{self.name}', endpoint='{self.endpoint}')>"

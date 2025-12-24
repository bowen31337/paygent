"""
Payment models.

This module defines the SQLAlchemy models for payments and transactions.
"""

from sqlalchemy import Column, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

from src.core.database import Base


class Payment(Base):
    """Payment model for tracking x402 payment transactions."""

    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=lambda: uuid4())
    agent_wallet: Mapped[str] = mapped_column(String(42), nullable=False)
    service_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("services.id"))
    recipient: Mapped[str] = mapped_column(String(42), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    token: Mapped[str] = mapped_column(String(42), nullable=False)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, confirmed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, status='{self.status}')>"

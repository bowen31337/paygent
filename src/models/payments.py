"""
Payment models.

This module defines the SQLAlchemy models for payments and transactions.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Payment(Base):
    """Payment model for tracking x402 payment transactions."""

    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=lambda: uuid4())
    agent_wallet: Mapped[str] = mapped_column(String(42), nullable=False)
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("services.id"))
    recipient: Mapped[str] = mapped_column(String(42), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    token: Mapped[str] = mapped_column(String(42), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(String(66))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, confirmed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, status='{self.status}')>"

"""Declarative base and shared column helpers (Phase 3.2)."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp helper for default columns."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """All models inherit from this base."""


class TimestampMixin:
    """Adds `created_at` (and optionally `updated_at`) columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

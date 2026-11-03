"""Notification model (Phase 3.2, functionality in Phase 26)."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


class NotificationChannel(StrEnum):
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationStatus(StrEnum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    DISMISSED = "dismissed"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    lead_time_days: Mapped[int | None] = mapped_column(nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status", native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=NotificationStatus.SCHEDULED,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task = relationship("Task")

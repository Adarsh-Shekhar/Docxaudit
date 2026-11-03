"""Task model (Phase 3.2, functionality in Phase 20)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    obligation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    # Simple recurrence for v1 (TRD §4): "none" | "yearly" | "monthly" | "quarterly"
    recurrence_rule: Mapped[str | None] = mapped_column(String(31), nullable=True, default="none")

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=TaskStatus.OPEN,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    obligation = relationship("Obligation", back_populates="tasks")
    evidence = relationship("EvidenceAttachment", back_populates="task", passive_deletes=True)

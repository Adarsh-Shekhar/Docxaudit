"""Obligation model (Phase 3.2) — VERIFIED data, created only via human
Accept/Edit on a clause (R-2). Citation fields keep verified obligations
traceable even if extraction records are pruned (TRD §4 design note)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base
from app.models.extracted_clause import ObligationType


class Obligation(Base):
    __tablename__ = "obligations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extracted_clause_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("extracted_clauses.id", ondelete="SET NULL"), nullable=True
    )

    obligation_type: Mapped[ObligationType] = mapped_column(
        Enum(ObligationType, name="obligation_type", create_type=False, native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String, nullable=False)

    # Source traceability (R-5)
    citation_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_offset_start: Mapped[int] = mapped_column(Integer, nullable=False)
    citation_offset_end: Mapped[int] = mapped_column(Integer, nullable=False)

    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tasks = relationship("Task", back_populates="obligation", passive_deletes=True)

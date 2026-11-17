"""ExtractedClause model (Phase 3.2) — provisional data, pre-verification (R-2).

The ExtractedClause/Obligation split is the enforcement mechanism for R-2:
clausing here is provisional; `Obligation` rows exist only after human
Accept/Edit (Phase 13). Never merge these tables (plan §3.2 Risks/Notes).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


class ObligationType(StrEnum):
    RENEWAL = "renewal"
    TERMINATION_NOTICE = "termination_notice"
    PAYMENT_TRIGGER = "payment_trigger"
    EVIDENCE_COMPLIANCE = "evidence_compliance"
    OTHER = "other"


class ClauseStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class ExtractedClause(Base):
    __tablename__ = "extracted_clauses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    obligation_type: Mapped[ObligationType] = mapped_column(
        Enum(ObligationType, name="obligation_type", native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    plain_language_text: Mapped[str] = mapped_column(String, nullable=False)
    raw_source_text: Mapped[str] = mapped_column(String, nullable=False)

    # Citation mandatory (R-5): a clause may never exist without these.
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[ClauseStatus] = mapped_column(
        Enum(ClauseStatus, name="clause_status", native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ClauseStatus.PENDING,
    )

    # Visual highlight box in PDF points (Phase 17.2 decision: stored at
    # parse time from PyMuPDF). None for DOCX or unlocatable spans.
    bbox: Mapped[dict[str, float | int] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document = relationship("Document", back_populates="clauses")

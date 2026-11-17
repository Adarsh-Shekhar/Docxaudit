"""Clause schemas (Phase 13.1)."""
from __future__ import annotations

import uuid
import zoneinfo
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VALID_OBLIGATION_TYPES = ("renewal", "termination_notice", "payment_trigger", "evidence_compliance", "other")

_REVIEW_ACTION = Literal["accept", "edit", "reject"]


class ClauseResponse(BaseModel):
    """One extracted clause as surfaced for review (citation always present, R-5)."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    obligation_type: str
    plain_language_text: str
    raw_source_text: str
    page_number: int | None
    char_start: int
    char_end: int
    confidence_score: float
    status: str  # pending | accepted | edited | rejected
    created_at: datetime


class ReviewProgress(BaseModel):
    """Review progress indicator (FR-2.5 / Phase 13.3)."""

    model_config = ConfigDict(extra="forbid")

    reviewed: int
    total: int


class ClauseListResponse(BaseModel):
    """`GET /documents/{id}/clauses` payload with embedded progress."""

    model_config = ConfigDict(extra="forbid")

    clauses: list[ClauseResponse]
    progress: ReviewProgress


class ClauseUpdateRequest(BaseModel):
    """Human decision on a clause (Phase 13.2) — the ONLY path that may
    create an `Obligation` row (R-2)."""

    model_config = ConfigDict(extra="forbid")

    action: _REVIEW_ACTION
    # Only meaningful for action="edit"; at least one must be provided.
    plain_language_text: str | None = Field(default=None, min_length=1)
    obligation_type: str | None = None

    @model_validator(mode="after")
    def _edit_requires_payload(self) -> ClauseUpdateRequest:
        if self.action == "edit" and self.plain_language_text is None and self.obligation_type is None:
            raise ValueError("action='edit' requires plain_language_text and/or obligation_type")
        if self.action != "edit" and (self.plain_language_text is not None or self.obligation_type is not None):
            raise ValueError("plain_language_text/obligation_type are only valid with action='edit'")
        return self


def utcnow() -> datetime:
    """Timezone-aware now for `Obligation.verified_at` (TZ-aware column)."""
    return datetime.now(tz=zoneinfo.ZoneInfo("UTC"))

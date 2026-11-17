"""Document schemas (Phase 7.2) + extraction status stubs (Phase 7.3)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

SUPPORTED_MIME = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB (Phase 7.3)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    filename: str
    mime_type: str
    version: int
    parent_document_id: uuid.UUID | None
    uploaded_at: datetime


class UploadResponse(DocumentResponse):
    """Same shape as DocumentResponse; explicit alias for upload UX."""


class ExtractionStatusResponse(BaseModel):
    """Extraction job status (Phase 12)."""

    model_config = ConfigDict(extra="forbid")

    status: str  # not_started | queued | parsing | extracting | ... | completed | failed
    progress: dict[str, int] | None = None  # {"done": n, "total": m}
    error: str | None = None

"""Document endpoints (Phase 7.3).

Org scoping on every endpoint via `CurrentUser` (Phase 7.6). File text is
NEVER logged (R-3). Filenames sanitized; storage paths server-controlled
(Phase 7.5).
"""
from __future__ import annotations

import contextlib
import re
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession
from app.core.storage import StorageError, get_storage
from app.models.document import Document
from app.models.user import UserRole
from app.schemas.document import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_MIME,
    DocumentResponse,
    ExtractionStatusResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(name: str) -> str:
    """Strip path traversal and unsafe characters; keep a readable stem."""
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    safe = _SAFE_FILENAME.sub("_", base).strip("._")
    return safe or "document"


def _storage_key(org_id: uuid.UUID, document_id: uuid.UUID, version: int, filename: str) -> str:
    """`{org_id}/{document_id}/v{version}/{filename}` (Phase 7.5)."""
    return f"{org_id}/{document_id}/v{version}/{_sanitize_filename(filename)}"


def _load_document_or_404(
    db: Session, document_id: uuid.UUID, user: CurrentUser
) -> Document:
    """Access check (Phase 7.6): 404 — never leak existence across orgs."""
    doc = db.get(Document, document_id)
    if doc is None or doc.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),  # noqa: B008 — FastAPI DI pattern
    replaces_document_id: uuid.UUID | None = None,
) -> DocumentResponse:
    """Upload PDF/DOCX; create Document row (version=1, or +1 on re-upload).

    Version handling (Phase 7.4 / US-8): passing `replaces_document_id`
    creates a new Document with version+1 linked via `parent_document_id`.
    """
    if file.content_type not in SUPPORTED_MIME:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type")

    # UploadFile gives a spooled file; read with the size cap enforced.
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    # Re-upload / versioning
    version = 1
    if replaces_document_id is not None:
        prior = _load_document_or_404(db, replaces_document_id, user)
        version = prior.version + 1

    doc = Document(
        id=uuid.uuid4(),  # explicit so the storage key can embed it pre-insert
        organization_id=user.organization_id,
        uploaded_by=user.id,
        filename=_sanitize_filename(file.filename or "document"),
        mime_type=file.content_type or "application/octet-stream",
        version=version,
        parent_document_id=replaces_document_id,
    )

    storage = get_storage()
    try:
        doc.storage_path = storage.save(data, _storage_key(user.organization_id, doc.id, version, doc.filename))
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage failure") from exc

    db.add(doc)
    db.flush()
    return DocumentResponse.model_validate(doc)


@router.get("", response_model=list[DocumentResponse])
def list_documents(user: CurrentUser, db: DbSession) -> list[DocumentResponse]:
    """List the org's documents (newest first)."""
    rows = db.scalars(
        select(Document)
        .where(Document.organization_id == user.organization_id)
        .order_by(Document.uploaded_at.desc())
    ).all()
    return [DocumentResponse.model_validate(r) for r in rows]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> DocumentResponse:
    return DocumentResponse.model_validate(_load_document_or_404(db, document_id, user))


@router.get("/{document_id}/content")
def download_document(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> dict[str, str]:
    """Return the stored file bytes (base64 in JSON for v1; streaming later)."""
    import base64

    doc = _load_document_or_404(db, document_id, user)
    try:
        data = get_storage().read(doc.storage_path)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing from storage") from exc
    return {
        "filename": doc.filename,
        "mime_type": doc.mime_type,
        "content_base64": base64.b64encode(data).decode("ascii"),
    }


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    """Admin or uploader deletes; hard delete cascades clauses/obligations.

    Decision (Phase 7.3): hard delete with CASCADE + audit log entry; block
    delete is deferred — obligations keep their copied citation fields
    (Obligation.citation_page/offsets) but lose the FK via SET NULL on
    extracted_clause_id. Only admin or uploader may delete.
    """
    from app.services.audit import log_action

    doc = _load_document_or_404(db, document_id, user)
    if not (user.role == UserRole.ADMIN or doc.uploaded_by == user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Best-effort storage cleanup; DB row deletion is the source of truth.
    with contextlib.suppress(StorageError):
        get_storage().delete(doc.storage_path)

    log_action(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="document",
        entity_id=doc.id,
        action="document.deleted",
        details={"filename": doc.filename, "version": doc.version},
    )
    db.delete(doc)


@router.post("/{document_id}/extract", response_model=ExtractionStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_extraction(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ExtractionStatusResponse:
    """Stub (Phase 7.3): accepts and returns 202; real LangGraph pipeline in Phase 12."""
    _load_document_or_404(db, document_id, user)
    return ExtractionStatusResponse(status="queued")


@router.get("/{document_id}/status", response_model=ExtractionStatusResponse)
def extraction_status(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ExtractionStatusResponse:
    """Stub (Phase 7.3): `not_started` until Phase 12 adds the job table."""
    _load_document_or_404(db, document_id, user)
    return ExtractionStatusResponse(status="not_started")

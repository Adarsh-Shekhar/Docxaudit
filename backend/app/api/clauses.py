"""Clauses API (Phase 13.2) — the human review layer.

R-2 enforcement: `Obligation` rows are created ONLY here, from an explicit
human accept/edit on an `ExtractedClause`. No other code path may create
them.

Role mapping (FR-5.1, documented): v1 has no separate "verifier" role —
`admin` decides (accept/edit/reject); `member` is read-only. A verifier
role can be added later by extending the guard below.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, require_role
from app.models.document import Document
from app.models.extracted_clause import ClauseStatus, ExtractedClause, ObligationType
from app.models.obligation import Obligation
from app.models.user import User, UserRole
from app.schemas.clause import (
    VALID_OBLIGATION_TYPES,
    ClauseListResponse,
    ClauseResponse,
    ClauseUpdateRequest,
    ReviewProgress,
    utcnow,
)
from app.services.audit import log_action

router = APIRouter(tags=["clauses"])

_ADMIN_ONLY = [Depends(require_role(UserRole.ADMIN))]


def _load_document_or_404(db: Session, document_id: uuid.UUID, user: User) -> Document:
    """Org-scoped access check: 404 — never leak existence across orgs."""
    doc = db.get(Document, document_id)
    if doc is None or doc.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


def _load_clause_or_404(
    db: Session, clause_id: uuid.UUID, user: User
) -> tuple[ExtractedClause, Document]:
    """Clause + its document, org-scoped (404 on foreign orgs)."""
    clause = db.get(ExtractedClause, clause_id)
    if clause is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clause not found")
    doc = _load_document_or_404(db, clause.document_id, user)
    return clause, doc


def _progress(db: Session, document_id: uuid.UUID) -> ReviewProgress:
    clauses = db.scalars(
        select(ExtractedClause).where(ExtractedClause.document_id == document_id)
    ).all()
    reviewed = sum(1 for c in clauses if c.status != ClauseStatus.PENDING)
    return ReviewProgress(reviewed=reviewed, total=len(clauses))


@router.get("/documents/{document_id}/clauses", response_model=ClauseListResponse)
def list_clauses(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ClauseListResponse:
    """List a document's clauses in document order, with review progress."""
    _load_document_or_404(db, document_id, user)
    clauses = db.scalars(
        select(ExtractedClause)
        .where(ExtractedClause.document_id == document_id)
        .order_by(ExtractedClause.page_number.nulls_first(), ExtractedClause.char_start)
    ).all()
    return ClauseListResponse(
        clauses=[ClauseResponse.model_validate(c) for c in clauses],
        progress=_progress(db, document_id),
    )


def _obligation_from_clause(clause: ExtractedClause, user: User) -> Obligation:
    """The single sanctioned Obligation factory (R-2). Copies citation data
    so obligations stay traceable even if extraction rows are pruned."""
    return Obligation(
        document_id=clause.document_id,
        extracted_clause_id=clause.id,
        obligation_type=clause.obligation_type,
        description=clause.plain_language_text,
        citation_page=clause.page_number,
        citation_offset_start=clause.char_start,
        citation_offset_end=clause.char_end,
        created_by=user.id,
        verified_at=utcnow(),
    )


@router.patch("/clauses/{clause_id}", response_model=ClauseResponse, dependencies=_ADMIN_ONLY)
def decide_clause(
    clause_id: uuid.UUID,
    decision: ClauseUpdateRequest,
    user: CurrentUser,
    db: DbSession,
) -> ClauseResponse:
    """Apply accept/edit/reject (Phase 13.2).

    Idempotency decision (documented): a clause is decided exactly ONCE —
    re-deciding returns 409. Corrections happen by rejecting and re-running
    extraction, or editing the resulting Obligation (Phase 17).
    """
    clause, doc = _load_clause_or_404(db, clause_id, user)

    if clause.status != ClauseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Clause already decided", "current_status": clause.status.value},
        )

    action = decision.action
    if action == "reject":
        clause.status = ClauseStatus.REJECTED
        log_action(
            db,
            organization_id=user.organization_id,
            actor_id=user.id,
            entity_type="extracted_clause",
            entity_id=clause.id,
            action="clause.rejected",
            details={"document_id": str(doc.id)},
        )
        db.flush()
        return ClauseResponse.model_validate(clause)

    if action == "edit":
        if decision.plain_language_text is not None:
            clause.plain_language_text = decision.plain_language_text
        if decision.obligation_type is not None:
            if decision.obligation_type not in VALID_OBLIGATION_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"obligation_type must be one of {VALID_OBLIGATION_TYPES}",
                )
            clause.obligation_type = ObligationType(decision.obligation_type)
        clause.status = ClauseStatus.EDITED
    else:  # accept
        clause.status = ClauseStatus.ACCEPTED

    db.add(_obligation_from_clause(clause, user))
    log_action(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="extracted_clause",
        entity_id=clause.id,
        action=f"clause.{action}ed" if action != "edit" else "clause.edited",
        details={
            "document_id": str(doc.id),
            "obligation_type": clause.obligation_type.value,
        },
    )
    db.flush()
    return ClauseResponse.model_validate(clause)

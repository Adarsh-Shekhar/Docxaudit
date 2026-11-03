"""Model aggregator — Alembic's `env.py` imports this to discover all models."""
from __future__ import annotations

from app.models.audit_log import AuditLog
from app.models.base import Base, utcnow
from app.models.document import Document
from app.models.evidence_attachment import EvidenceAttachment
from app.models.extracted_clause import ClauseStatus, ExtractedClause, ObligationType
from app.models.notification import Notification, NotificationChannel, NotificationStatus
from app.models.obligation import Obligation
from app.models.organization import Organization
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "utcnow",
    "Organization",
    "User",
    "UserRole",
    "Document",
    "ExtractedClause",
    "ClauseStatus",
    "ObligationType",
    "Obligation",
    "Task",
    "TaskStatus",
    "EvidenceAttachment",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "AuditLog",
]

"""Audit service (Phase 5.4; generalizes in Phase 23)."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Write one audit row. Fails loudly on error — mutations must be auditable."""
    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=details,
        )
    )

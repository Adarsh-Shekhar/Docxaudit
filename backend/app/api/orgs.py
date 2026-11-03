"""Org and user-management endpoints (Phase 5).

v1 invite flow decision (Phase 5.3): admin creates the user with a
temporary password and hands it over out-of-band. Email invite links are
a stretch goal (36.6). Audit entries written on role change and user
creation (Phase 5.4). Role guard via `require_role` (5.2).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, require_role
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.users import (
    AuditEntry,
    OrganizationResponse,
    UpdateRoleRequest,
    UserResponse,
    UserUpdateResponse,
)
from app.services.audit import log_action

router = APIRouter(tags=["orgs"])


class CreateUserRequest(BaseModel):
    """v1 invite flow: temp password handed out-of-band (Phase 5.3)."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


@router.get("/orgs/me", response_model=OrganizationResponse)
def get_my_organization(user: CurrentUser) -> OrganizationResponse:
    """Current org details (Phase 5.1). Org always from token, not path."""
    return OrganizationResponse.model_validate(user.organization)


@router.get("/orgs/me/audit", response_model=list[AuditEntry])
def get_org_audit(
    user: CurrentUser,
    db: DbSession,
    limit: int = 50,
) -> list[AuditEntry]:
    """Recent audit entries for the org, newest first (support tooling)."""
    limit_capped = max(1, min(limit, 200))
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == user.organization_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit_capped)
    ).all()
    return [AuditEntry.model_validate(r) for r in rows]


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("", response_model=list[UserResponse])
def list_org_members(user: CurrentUser, db: DbSession) -> list[UserResponse]:
    """List org members — scoped to the caller's organization (5.2)."""
    rows = db.scalars(
        select(User)
        .where(User.organization_id == user.organization_id)
        .order_by(User.created_at.asc())  # ordered join needed for stable ties
    ).all()
    return [UserResponse.model_validate(r) for r in rows]


@users_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_org_member(
    payload: CreateUserRequest,
    user: CurrentUser,
    db: DbSession,
    _admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> UserResponse:
    """Admin-only: create a member with a temp password (Phase 5.3)."""
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    new_user = User(
        organization_id=user.organization_id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=UserRole.MEMBER,
    )
    db.add(new_user)
    db.flush()

    log_action(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="user",
        entity_id=new_user.id,
        action="user.created",
        details={"email": new_user.email},
    )
    return UserResponse.model_validate(new_user)


@users_router.patch("/{user_id}/role", response_model=UserUpdateResponse)
def change_role(
    user_id: uuid.UUID,
    payload: UpdateRoleRequest,
    user: CurrentUser,
    db: DbSession,
    _admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> UserUpdateResponse:
    """Admin-only role change (Phase 5.2). Cannot demote the last admin."""
    if payload.role not in (UserRole.ADMIN.value, UserRole.MEMBER.value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role"
        )

    target = db.get(User, user_id)
    if target is None or target.organization_id != user.organization_id:
        # 404 — never leak existence across orgs (Phase 0 DoD cross-org note).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target.role == UserRole.ADMIN and payload.role != UserRole.ADMIN.value:
        admin_count = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.organization_id == user.organization_id,
                User.role == UserRole.ADMIN,
            )
        )
        if (admin_count or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Cannot demote the last admin"
            )

    old_role = target.role.value
    target.role = UserRole(payload.role)
    db.flush()

    log_action(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="user",
        entity_id=target.id,
        action="user.role_changed",
        details={"from": old_role, "to": payload.role},
    )
    return UserUpdateResponse.model_validate(target)

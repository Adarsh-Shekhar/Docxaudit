"""User/org schemas (Phase 5)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    created_at: datetime


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    # Temporary password handed out-of-band (Phase 5.3 decision); user
    # changes it after first login (stretch: email invite links, 36.6).
    password: str


class UpdateRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str  # "admin" | "member"


class UserUpdateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    email: str
    role: str


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    timestamp: datetime

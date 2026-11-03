"""Auth endpoints (Phase 4.2).

Org id in JWTs is derived ONLY server-side (Phase 4.6). Rate limiting on
auth is a Phase 36.7 stretch; v1 relies on bcrypt cost + short lockout is
out of scope (plan Â§4.8 â€” acceptable per C-7).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import DbSession
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshTokenResponse(BaseModel):
    model_config = {"extra": "forbid"}

    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    """Create Organization + first User (role admin), issue tokens (4.2)."""
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    org = Organization(name=payload.organization_name)
    db.add(org)
    db.flush()

    user = User(
        organization_id=org.id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.flush()

    settings = get_settings()
    access = create_access_token(subject=str(user.id), org_id=user.organization_id, role=user.role.value)
    refresh = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    """Verify credentials, issue access + refresh JWTs (4.2)."""
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        # 401 regardless of whether the email exists (7.6-style leak prevention).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    settings = get_settings()
    access = create_access_token(subject=str(user.id), org_id=user.organization_id, role=user.role.value)
    refresh = create_refresh_token(subject=str(user.id))
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh(payload: RefreshRequest, db: DbSession) -> RefreshTokenResponse:
    """Validate refresh token; issue new access token (4.2)."""
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        ) from None

    user = db.get(User, uuid.UUID(str(claims["sub"])))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )
    settings = get_settings()
    access = create_access_token(subject=str(user.id), org_id=user.organization_id, role=user.role.value)
    return RefreshTokenResponse(
        access_token=access,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )

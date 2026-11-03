"""Password hashing and JWT helpers (Phase 2.2)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_settings = get_settings()

# bcrypt cost factor >= 12 (Phase 4 Risks/Notes)
_pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12, deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


class InvalidTokenError(Exception):
    """Raised when a JWT is invalid or expired."""


def _create_token(subject: str, *, extra: dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
        **extra,
    }
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)


def create_access_token(*, subject: str, org_id: uuid.UUID, role: str) -> str:
    """Short-lived access token carrying user/org/role claims."""
    return _create_token(
        subject=str(subject),
        extra={"org": str(org_id), "role": role, "jti": uuid.uuid4().hex},
        expires_delta=timedelta(minutes=_settings.access_token_expire_minutes),
        token_type="access",
    )


def create_refresh_token(*, subject: str) -> str:
    """Longer-lived refresh token (rotation handled by the auth router)."""
    return _create_token(
        subject=str(subject),
        extra={"jti": uuid.uuid4().hex},
        expires_delta=timedelta(days=_settings.refresh_token_expire_days),
        token_type="refresh",
    )


def decode_token(token: str, *, expected_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT; raises `InvalidTokenError` on any failure."""
    try:
        payload = jwt.decode(token, _settings.jwt_secret_key, algorithms=[_settings.jwt_algorithm])
    except (ExpiredSignatureError, JWTError) as exc:
        raise InvalidTokenError from exc
    if payload.get("type") != expected_type:
        raise InvalidTokenError
    if not payload.get("sub"):
        raise InvalidTokenError
    return payload

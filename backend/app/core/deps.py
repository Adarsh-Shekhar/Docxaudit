"""FastAPI dependencies: db session, current user, role guard, org scoping
(Phase 2.3 / 4.4–4.6)."""
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import InvalidTokenError, decode_token
from app.models.user import User, UserRole

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Decode the access JWT, load the User, verify org still exists (4.4)."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.get(User, uuid.UUID(str(user_id)))
    if user is None or user.organization is None:
        # Org deleted since issuance — treat as unauthenticated (4.4).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_role(role: UserRole) -> Callable[[User], User]:
    """Dependency factory guarding admin-only endpoints (4.5)."""

    def _guard(user: CurrentUser) -> User:
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _guard


def current_organization_id(user: CurrentUser) -> uuid.UUID:
    """Org id injected ONLY from the authenticated user — never from the
    request body/query (TRD §5, Phase 4.6)."""
    return user.organization_id

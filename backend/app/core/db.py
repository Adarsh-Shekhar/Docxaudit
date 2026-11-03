"""Engine/session factory (Phase 2/13). All DB access goes through SQLAlchemy."""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _engine_kwargs(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    if url.startswith("postgresql"):
        # psycopg3 + SQLAlchemy: keep the pool modest for free-tier limits.
        return {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}
    return {}


def create_db_engine() -> Engine:
    settings = get_settings()
    url = settings.sqlalchemy_url()
    return create_engine(url, **_engine_kwargs(url))


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_db_engine()
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — one session per request."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

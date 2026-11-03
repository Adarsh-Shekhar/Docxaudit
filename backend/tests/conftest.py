"""Test fixtures (Phases 4.7 / 5.5).

Uses an isolated SQLite DB + TestClient; LLM never called in these tests.
Environment is pinned BEFORE importing the app (settings fail-fast).
"""
from __future__ import annotations

import os
import uuid

# Env must exist before app.core.config gets imported anywhere.
os.environ.setdefault("DATABASE_URL", f"sqlite:///./test_{uuid.uuid4().hex}.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base


@pytest.fixture(name="db_engine")
def db_engine_fixture():
    # Swap the settings URL to an in-memory SQLite instance shared across connections.
    metadata = Base.metadata
    test_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(test_engine)
    yield test_engine
    metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture(name="client")
def client_fixture(db_engine):  # noqa: ANN001
    # Point the app's engine at the test DB.
    import app.core.db as app_db

    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    original = (app_db._engine, app_db._SessionLocal)  # noqa: SLF001
    app_db._engine = db_engine  # noqa: SLF001
    app_db._SessionLocal = factory  # noqa: SLF001

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc

    app_db._engine, app_db._SessionLocal = original  # noqa: SLF001

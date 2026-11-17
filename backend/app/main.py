"""FastAPI application factory (Phase 2.4).

Routers are added here; endpoints must stay org-scoped via `deps.py`.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Fail fast if the DB is unreachable at startup (Phase 2.4).
    get_engine()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app_: FastAPI = FastAPI(
        title="Plain-Language Obligation Tracker",
        version="0.1.0",
        lifespan=lifespan,
    )
    app_.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api import auth, documents, orgs

    app_.include_router(auth.router)
    app_.include_router(orgs.router)
    app_.include_router(orgs.users_router)
    app_.include_router(documents.router)

    @app_.get("/health", tags=["ops"])
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    return app_


app = create_app()

"""Alembic migration environment (Phase 3.1).

Reads DATABASE_URL from env/.env and imports models from `app.models`
so autogenerate sees everything.
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `backend/` importable regardless of cwd (old alembic.ini
# `prepend_sys_path` is unreliable across Alembic versions).
_BACKEND_DIR = Path(context.config.config_file_name or __file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402  (path insert above)
from app.models import Base  # noqa: F401,E402  (import registers all models)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the SQLAlchemy URL from settings at runtime.
config.set_main_option("sqlalchemy.url", get_settings().sqlalchemy_url())

target_metadata = Base.metadata


def include_object(
    obj: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    """Skip SQLite-specific artifacts when autogenerating."""
    return not (type_ == "table" and name in ("alembic_version", "spatial_ref_sys"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (URL used literally)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""
alembic/env.py – Configured for SIH26069 Weather Platform.

Reads DATABASE_URL from the environment (falls back to SQLite for local dev).
Supports both sync (offline) and async (online) modes.
For PostgreSQL, uses psycopg2 for Alembic migrations (separate from the async
asyncpg driver used by FastAPI at runtime).
"""

from __future__ import annotations

import os
import re
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure the backend package is on the path so models can be imported
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Import the ORM metadata so autogenerate can detect all tables
from backend.app.models import Base  # noqa: E402  (after sys.path adjustment)

# ── Alembic Config ────────────────────────────────────────────────────────────

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_sync_url() -> str:
    """
    Convert the async DATABASE_URL to a synchronous one for Alembic.

    Priority:
      1. DATABASE_URL environment variable (converted from async to sync driver)
      2. Fall back to SQLite (offline dev)

    asyncpg  → psycopg2   (PostgreSQL)
    aiosqlite → sqlite    (SQLite, dev only)
    """
    url: str = os.environ.get("DATABASE_URL", "sqlite:///./wx.db")
    # Strip async driver prefix for Alembic (which uses synchronous connections)
    url = re.sub(r"^postgresql\+asyncpg", "postgresql+psycopg2", url)
    url = re.sub(r"^sqlite\+aiosqlite", "sqlite", url)
    return url


# ── Offline mode (generate SQL script without connecting) ────────────────────

def run_migrations_offline() -> None:
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connect to the DB and run migrations) ───────────────────────

def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_sync_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

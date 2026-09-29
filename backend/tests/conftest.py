"""
conftest.py – shared pytest fixtures for backend tests.

Key design decisions for Windows compatibility:
  - Each test gets its own *named* SQLite file (not :memory:) so that
    FastAPI's background tasks (which open a second connection) can reach it.
  - The file is deleted in teardown AFTER engine.dispose() releases all
    file handles — avoiding the PermissionError that :memory: hand-off
    and shared-file teardown cause on Windows.
  - Rate limiter storage is reset before each test so counter state from
    earlier tests does not bleed into later ones.
"""

import asyncio
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.database import Base, get_db
from backend.app.main import app


# ── Event loop (session-scoped, one loop for all tests) ───────────────────────
@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy (pytest-asyncio 0.24 compliant)."""
    return asyncio.DefaultEventLoopPolicy()


# ── Per-test isolated DB ──────────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async DB session backed by a temporary per-test SQLite file.
    Yields a session already bound to a fresh schema.
    Cleans up the file on Windows after dispose().
    """
    db_file = f"test_{uuid.uuid4().hex}.db"
    db_url = f"sqlite+aiosqlite:///./{db_file}"

    test_engine = create_async_engine(db_url, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with TestSession() as session:
        yield session

    await test_engine.dispose()
    if os.path.exists(db_file):
        os.remove(db_file)


# ── Per-test HTTP client with rate-limiter reset ──────────────────────────────
@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient wired to the FastAPI app with:
      - Test DB session injected via dependency override.
      - slowapi in-memory counter reset before each test to prevent
        rate-limit state from accumulating across the test suite.
    """
    # Reset the slowapi in-memory storage so each test starts with a clean counter
    from backend.app.rate_limit import limiter
    limiter._storage.reset()  # type: ignore[attr-defined]

    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Aliases used by test_media.py and other files ─────────────────────────────
# Allows tests to use either name interchangeably
async_client = client
async_session = db_session

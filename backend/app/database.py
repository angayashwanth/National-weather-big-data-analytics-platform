"""
database.py – SQLAlchemy 2 async engine + session factory.

DATABASE_URL defaults to SQLite (file-based) for local dev.
Override with a PostgreSQL+asyncpg URL in production:
  DATABASE_URL=postgresql+asyncpg://user:pass@host/db
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./wx.db")

# echo=False keeps test output clean; flip to True for debugging SQL
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a scoped async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

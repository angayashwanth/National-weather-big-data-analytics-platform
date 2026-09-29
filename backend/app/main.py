"""
main.py – FastAPI application entry point.

Wires together:
  - SQLAlchemy table creation on startup
  - slowapi rate-limit middleware + error handler
  - Reports router  (/api/reports, /api/export.geojson)
  - WebSocket router (/ws)
"""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .database import Base, engine
from .rate_limit import limiter
from .routers import reports as reports_router
from .routers import ws as ws_router
from .routers import admin as admin_router
from .routers import media as media_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup; clean up engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")
    # Ensure local media upload directory exists (used as MinIO fallback)
    media_dir = Path("./media_uploads")
    media_dir.mkdir(parents=True, exist_ok=True)
    # Mount it for static serving if not already mounted
    yield
    await engine.dispose()


app = FastAPI(
    title="National Weather Big Data Analytics Platform",
    description=(
        "SIH26069 — Unified intake, ML classification, human review, "
        "and live dashboard for citizen and social weather intelligence."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── Rate-limit state & middleware ─────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS (permissive for local dev; tighten in production) ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(reports_router.router)
app.include_router(ws_router.router)
app.include_router(admin_router.router)
app.include_router(media_router.router)

# Serve locally-stored media files at /media
_media_dir = Path("./media_uploads")
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}

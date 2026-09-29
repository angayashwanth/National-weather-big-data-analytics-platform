"""
models.py – SQLAlchemy 2 ORM model for the Report entity.

Matches Section 2.3.2 of SIH26069_Solution_Document.md exactly,
with additional ML pipeline fields.
"""

import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Report(Base):
    __tablename__ = "reports"

    # ── Primary key ────────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ── Section 2.3.2 core schema ──────────────────────────────────────────────
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    city: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # GPS stored as separate lat/lon columns (GeoJSON constructed in response)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Comma-separated storage URLs; empty string == no media
    photos: Mapped[str] = mapped_column(Text, nullable=False, default="")
    videos: Mapped[str] = mapped_column(Text, nullable=False, default="")
    event_category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unverified", index=True
    )
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Extended fields ────────────────────────────────────────────────────────
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_handle: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # ML pipeline outputs
    classify_conf: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fake_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high_impact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duplicate_of: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ml_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ml_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Admin panel fields
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

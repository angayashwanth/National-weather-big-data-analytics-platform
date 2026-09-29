"""
schemas.py – Pydantic v2 request / response schemas for the Report entity.

Enums mirror Section 2.3.2 of SIH26069_Solution_Document.md.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums (Section 2.3.2) ────────────────────────────────────────────────────

class EventCategory(str, Enum):
    rainfall = "rainfall"
    thunderstorm = "thunderstorm"
    flooding = "flooding"
    heatwave = "heatwave"
    fog = "fog"
    dust_storm = "dust_storm"
    strong_wind = "strong_wind"


class SourceType(str, Enum):
    citizen_report = "citizen_report"
    social_media = "social_media"
    website = "website"
    api = "api"
    public_dataset = "public_dataset"


class VerificationStatus(str, Enum):
    verified = "verified"
    under_review = "under_review"
    rejected = "rejected"
    unverified = "unverified"


# ── Request schema ───────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    """Payload accepted by POST /api/reports (all 5 source types)."""

    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="ISO-8601 observation time; defaults to submission time.",
    )
    city: str = Field(..., min_length=1, max_length=128)
    state: str = Field(..., min_length=1, max_length=128)
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    lon: Optional[float] = Field(None, ge=-180.0, le=180.0)
    photos: List[str] = Field(default_factory=list)
    videos: List[str] = Field(default_factory=list)
    event_category: EventCategory
    source_type: SourceType
    trust_score: float = Field(default=0.0, ge=0.0, le=100.0)

    # Optional extended fields
    text: Optional[str] = Field(None, max_length=4096)
    source_handle: Optional[str] = Field(None, max_length=256)

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone(cls, v: Any) -> datetime.datetime:
        if isinstance(v, datetime.datetime) and v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v


# ── Response schema ──────────────────────────────────────────────────────────

class GpsLocation(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]


class ReportOut(BaseModel):
    """Full report representation returned by GET endpoints."""

    id: int
    timestamp: datetime.datetime
    city: str
    state: str
    gps_location: GpsLocation
    photos: List[str]
    videos: List[str]
    event_category: EventCategory
    source_type: SourceType
    verification_status: VerificationStatus
    trust_score: float
    text: Optional[str]
    source_handle: Optional[str]
    classify_conf: Optional[float]
    fake_score: Optional[float]
    high_impact: bool
    duplicate_of: Optional[int]
    ml_verdict: Optional[str]
    reviewed_by: Optional[str]
    notes: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def build_from_orm(cls, data: Any) -> Any:
        """Convert ORM Report object fields to schema-friendly dict."""
        if hasattr(data, "__tablename__"):  # ORM instance
            d: Dict[str, Any] = {
                col: getattr(data, col)
                for col in (
                    "id", "timestamp", "city", "state", "lat", "lon",
                    "event_category", "source_type", "verification_status",
                    "trust_score", "text", "source_handle", "classify_conf",
                    "fake_score", "high_impact", "duplicate_of", "ml_verdict",
                    "reviewed_by", "notes", "created_at", "updated_at",
                )
            }
            # Parse comma-separated strings back to lists
            d["photos"] = [p for p in (data.photos or "").split(",") if p]
            d["videos"] = [v for v in (data.videos or "").split(",") if v]
            d["gps_location"] = {"latitude": data.lat, "longitude": data.lon}
            return d
        return data


# ── Accepted response ────────────────────────────────────────────────────────

class ReportAccepted(BaseModel):
    id: int
    message: str = "Report accepted; ML pipeline queued."


# ── List response ────────────────────────────────────────────────────────────

class ReportListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ReportOut]

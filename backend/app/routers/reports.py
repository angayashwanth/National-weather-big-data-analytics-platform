"""
reports.py – Core API router for weather report intake and retrieval.

Endpoints:
  POST   /api/reports            – unified intake (all 5 source types), rate-limited
  GET    /api/reports/{id}       – single report status tracking
  GET    /api/reports            – paginated list with filters
  GET    /api/export.geojson     – verified-only GeoJSON FeatureCollection
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import and_, select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..ml_stub import run_ml_pipeline
from ..models import Report
from ..rate_limit import RATE_LIMIT_POST_REPORTS, limiter
from ..schemas import (
    EventCategory,
    ReportAccepted,
    ReportCreate,
    ReportListOut,
    ReportOut,
    VerificationStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["reports"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize(report: Report) -> ReportOut:
    return ReportOut.model_validate(report)


def _build_filters(
    status: Optional[str],
    event: Optional[str],
    city: Optional[str],
    state: Optional[str],
    date_from: Optional[datetime.datetime],
    date_to: Optional[datetime.datetime],
) -> List[Any]:
    clauses: List[Any] = []
    if status:
        clauses.append(Report.verification_status == status)
    if event:
        clauses.append(Report.event_category == event)
    if city:
        clauses.append(Report.city.ilike(f"%{city}%"))
    if state:
        clauses.append(Report.state.ilike(f"%{state}%"))
    if date_from:
        clauses.append(Report.timestamp >= date_from)
    if date_to:
        clauses.append(Report.timestamp <= date_to)
    return clauses


# ── POST /api/reports ─────────────────────────────────────────────────────────

@router.post("/reports", status_code=202, response_model=ReportAccepted)
@limiter.limit(RATE_LIMIT_POST_REPORTS)
async def create_report(
    request: Request,  # required by slowapi for key_func
    payload: ReportCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ReportAccepted:
    """
    Unified intake endpoint for all 5 source types.
    Returns HTTP 202 immediately; ML pipeline runs as a background task.
    """
    report = Report(
        timestamp=payload.timestamp,
        city=payload.city,
        state=payload.state,
        lat=payload.lat,
        lon=payload.lon,
        photos=",".join(payload.photos),
        videos=",".join(payload.videos),
        event_category=payload.event_category.value,
        source_type=payload.source_type.value,
        trust_score=payload.trust_score,
        text=payload.text,
        source_handle=payload.source_handle,
        verification_status=VerificationStatus.unverified.value,
    )
    db.add(report)
    await db.flush()  # assigns report.id without committing yet

    report_id = report.id
    await db.commit()
    await db.refresh(report)

    # Queue ML processing without blocking the response
    background_tasks.add_task(_run_ml_and_maybe_broadcast, report_id)

    logger.info("Report %d accepted from %s", report_id, payload.source_type)
    return ReportAccepted(id=report_id)


async def _run_ml_and_maybe_broadcast(report_id: int) -> None:
    """
    Runs ML pipeline in a fresh DB session (background task context),
    then broadcasts over WebSocket if the report becomes verified.
    """
    from ..database import AsyncSessionLocal
    from .ws import broadcast_verified

    async with AsyncSessionLocal() as session:
        await run_ml_pipeline(report_id, session)
        report = await session.get(Report, report_id)
        if report and report.verification_status == VerificationStatus.verified.value:
            await broadcast_verified(report_id, report.city, report.event_category)


# ── GET /api/reports/{id} ─────────────────────────────────────────────────────

@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    """Return a single report by ID (used for citizen status tracking)."""
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")
    return _serialize(report)


# ── GET /api/reports ──────────────────────────────────────────────────────────

@router.get("/reports", response_model=ReportListOut)
async def list_reports(
    status: Optional[VerificationStatus] = Query(None),
    event: Optional[EventCategory] = Query(None),
    city: Optional[str] = Query(None, max_length=128),
    state: Optional[str] = Query(None, max_length=128),
    date_from: Optional[datetime.datetime] = Query(None),
    date_to: Optional[datetime.datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ReportListOut:
    """Paginated report list with optional filters."""
    clauses = _build_filters(
        status.value if status else None,
        event.value if event else None,
        city,
        state,
        date_from,
        date_to,
    )
    where = and_(*clauses) if clauses else True

    count_q = await db.execute(
        select(sqlfunc.count()).select_from(Report).where(where)
    )
    total: int = count_q.scalar_one()

    rows_q = await db.execute(
        select(Report)
        .where(where)
        .order_by(Report.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = rows_q.scalars().all()

    return ReportListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[_serialize(r) for r in rows],
    )


# ── GET /api/export.geojson ───────────────────────────────────────────────────

@router.get("/export.geojson")
async def export_geojson(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Export all verified reports as a GeoJSON FeatureCollection.
    For use by NDRF / SDMA tools.
    """
    rows_q = await db.execute(
        select(Report)
        .where(Report.verification_status == VerificationStatus.verified.value)
        .order_by(Report.timestamp.desc())
    )
    rows = rows_q.scalars().all()

    features = []
    for r in rows:
        geometry: Optional[Dict[str, Any]] = None
        if r.lat is not None and r.lon is not None:
            geometry = {"type": "Point", "coordinates": [r.lon, r.lat]}

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat(),
                    "city": r.city,
                    "state": r.state,
                    "event_category": r.event_category,
                    "source_type": r.source_type,
                    "trust_score": r.trust_score,
                    "text": r.text,
                    "photos": [p for p in (r.photos or "").split(",") if p],
                    "videos": [v for v in (r.videos or "").split(",") if v],
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}

"""
admin.py – JWT-protected Admin Panel endpoints.

Endpoints
---------
POST /api/auth/login                    – obtain a Bearer token (no auth required)
GET  /api/admin/queue                   – under_review reports, high-impact first
POST /api/admin/reports/{id}/decision   – approve (verified) or reject a report
GET  /api/admin/kpis                    – status counts + ML override rate
"""

from __future__ import annotations

import csv
import logging
import pathlib
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    create_access_token,
    verify_token,
)
from ..database import get_db
from ..models import Report
from ..schemas import ReportOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DecisionRequest(BaseModel):
    status: Literal["verified", "rejected"]
    notes: Optional[str] = None


class KpiResponse(BaseModel):
    total_reports: int
    by_status: Dict[str, int]
    override_rate: float
    """Fraction of admin-reviewed reports where the admin changed the ML verdict."""
    avg_trust_score: float
    classification_accuracy: float
    """Fraction of labeled_sample.csv rows classified correctly by classify()."""
    fake_precision: float
    """Precision of fake_score >= 0.5 threshold on the labeled fixture."""
    fake_recall: float
    """Recall of fake_score >= 0.5 threshold on the labeled fixture."""
    avg_ml_latency_ms: float
    """Average milliseconds from DB insertion to ML verdict, over last 50 reports."""


# ── POST /api/auth/login ──────────────────────────────────────────────────────

@router.post("/api/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """
    Authenticate with admin credentials from environment variables.
    Returns a Bearer JWT valid for 8 hours.
    """
    if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = create_access_token(body.username)
    logger.info("Admin login: %s", body.username)
    return TokenResponse(access_token=token)


# ── GET /api/admin/queue ──────────────────────────────────────────────────────

@router.get("/api/admin/queue", response_model=List[ReportOut])
async def get_review_queue(
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(verify_token),
) -> List[ReportOut]:
    """
    Returns all under_review reports ordered by:
    1. high_impact DESC (flood/dust_storm/trigger-word cases first)
    2. created_at ASC  (oldest unreviewed first — FIFO within priority)
    """
    result = await db.execute(
        select(Report)
        .where(Report.verification_status == "under_review")
        .order_by(Report.high_impact.desc(), Report.created_at.asc())
    )
    rows = result.scalars().all()
    return [ReportOut.model_validate(r) for r in rows]


# ── POST /api/admin/reports/{id}/decision ─────────────────────────────────────

@router.post("/api/admin/reports/{report_id}/decision", response_model=ReportOut)
async def make_decision(
    report_id: int,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(verify_token),
) -> ReportOut:
    """
    Approve or reject a queued report.
    - Sets verification_status to verified|rejected.
    - Records the reviewing admin's username in reviewed_by.
    - ml_verdict is intentionally left unchanged (used for override-rate KPI).
    - On approval, broadcasts over WebSocket.
    """
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")

    report.verification_status = body.status
    report.reviewed_by = username
    if body.notes:
        report.notes = body.notes

    await db.commit()
    await db.refresh(report)

    if body.status == "verified":
        from .ws import broadcast_verified
        await broadcast_verified(report_id, report.city, report.event_category)

    logger.info(
        "Admin %s set report %d -> %s", username, report_id, body.status
    )
    return ReportOut.model_validate(report)


# ── GET /api/admin/kpis ───────────────────────────────────────────────────────

@router.get("/api/admin/kpis", response_model=KpiResponse)
async def get_kpis(
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(verify_token),
) -> KpiResponse:
    """
    Returns aggregate KPIs for the Admin Panel dashboard.

    override_rate is computed ONLY on reports where:
    - ml_verdict is set (ML made a suggestion), AND
    - reviewed_by is set (an admin reviewed it).

    override_rate = (admin decision ≠ ml_verdict) / (total such reports).
    """
    result = await db.execute(select(Report))
    all_reports: List[Report] = result.scalars().all()

    total = len(all_reports)
    by_status: Dict[str, int] = {
        "verified": 0, "under_review": 0, "rejected": 0, "unverified": 0,
    }
    for r in all_reports:
        key = r.verification_status if r.verification_status in by_status else "unverified"
        by_status[key] += 1

    trust_scores = [r.trust_score for r in all_reports if r.trust_score is not None]
    avg_trust = round(sum(trust_scores) / len(trust_scores), 2) if trust_scores else 0.0

    # Override rate: reports where admin reviewed AND ML had a suggestion
    reviewed_with_ml = [
        r for r in all_reports
        if r.reviewed_by is not None and r.ml_verdict is not None
    ]
    overrides = sum(
        1 for r in reviewed_with_ml if r.ml_verdict != r.verification_status
    )
    override_rate = (
        round(overrides / len(reviewed_with_ml), 4) if reviewed_with_ml else 0.0
    )

    return KpiResponse(
        total_reports=total,
        by_status=by_status,
        override_rate=override_rate,
        avg_trust_score=avg_trust,
        **_compute_ml_accuracy_kpis(),
        avg_ml_latency_ms=_compute_avg_latency(all_reports),
    )


# ── KPI helper: classification + fake detection accuracy ─────────────────────

_FIXTURE_PATH = (
    pathlib.Path(__file__).parent.parent.parent
    / "tests" / "fixtures" / "labeled_sample.csv"
)


def _compute_ml_accuracy_kpis() -> Dict[str, float]:
    """Run classify() and fake_score() over labeled_sample.csv and return accuracy KPIs."""
    from ..pipeline import classify, fake_score  # local import to avoid circular

    FAKE_THRESHOLD = 0.5
    correct = total = 0
    tp = fp = fn = 0

    try:
        with open(_FIXTURE_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row["text"]
                true_cat = row["true_category"]
                is_fake_truth = row["is_fake"].strip().lower() == "true"

                # Classification accuracy
                pred_cat, _ = classify(text=text, hint=None)  # FIXED: was hint=true_cat (data leakage)
                total += 1
                if pred_cat == true_cat:
                    correct += 1

                # Fake detection precision / recall
                score = fake_score(text=text, lat=None, lon=None)
                pred_fake = score >= FAKE_THRESHOLD
                if is_fake_truth and pred_fake:
                    tp += 1
                elif not is_fake_truth and pred_fake:
                    fp += 1
                elif is_fake_truth and not pred_fake:
                    fn += 1
    except FileNotFoundError:
        logger.warning("labeled_sample.csv not found at %s", _FIXTURE_PATH)
        return {"classification_accuracy": 0.0, "fake_precision": 0.0, "fake_recall": 0.0}

    accuracy = round(correct / total, 4) if total else 0.0
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0

    return {
        "classification_accuracy": accuracy,
        "fake_precision": precision,
        "fake_recall": recall,
    }


def _compute_avg_latency(reports: List[Any], n: int = 50) -> float:
    """Average ml_latency_ms over the last n reports that have it set."""
    latencies = [
        r.ml_latency_ms for r in reports
        if getattr(r, "ml_latency_ms", None) is not None
    ]
    recent = latencies[-n:]
    return round(sum(recent) / len(recent), 2) if recent else 0.0
"""
ml_stub.py – ML pipeline runner (orchestrates the four pipeline stages).

The name is kept so existing imports are not broken. This file now calls
the real pipeline functions defined in pipeline.py. Replace this with a
proper async task worker (e.g., arq or Celery) in Phase 2.

HIGH_IMPACT_CATEGORIES mirrors pipeline.py to set the model's `high_impact`
flag correctly for admin queue ordering.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from .pipeline import (
    HIGH_IMPACT_CATEGORIES,
    TRIGGER_WORDS,
    classify,
    fake_score as compute_fake,
    find_duplicate,
    route,
    source_trust as compute_trust,
)


async def run_ml_pipeline(report_id: int, db: AsyncSession) -> None:
    """
    Orchestrate all four pipeline stages for a report, then persist results.

    Called as a background task from the reports router. Receives an
    open DB session — callers are responsible for providing an appropriate
    session (production uses AsyncSessionLocal; tests inject their own).
    """
    from .models import Report  # local import avoids circular dependency

    report: Report | None = await db.get(Report, report_id)
    if report is None:
        return

    _pipeline_start = datetime.datetime.now(datetime.timezone.utc)

    # ── Stage 1: Classify ────────────────────────────────────────────────────
    event_cat, confidence = classify(
        text=report.text,
        hint=report.event_category,  # user's self-reported category as hint
    )

    # ── Stage 2: Fake / misleading score ─────────────────────────────────────
    fake = compute_fake(
        text=report.text,
        lat=report.lat,
        lon=report.lon,
    )

    # ── Stage 3: Source trust score ───────────────────────────────────────────
    has_photo = bool(report.photos and report.photos.strip())
    has_gps = report.lat is not None and report.lon is not None
    trust = compute_trust(
        source_type=report.source_type,
        has_photo=has_photo,
        has_gps=has_gps,
    )

    # ── Stage 4: Near-duplicate detection ────────────────────────────────────
    photos_list = [p.strip() for p in (report.photos or "").split(",") if p.strip()]
    dup_id = await find_duplicate(
        text=report.text,
        event_category=event_cat,
        city=report.city,
        timestamp=report.timestamp,
        exclude_id=report.id,
        photos=photos_list if photos_list else None,
        db=db,
    )

    # ── Routing (Section 2.3.4) ───────────────────────────────────────────────
    verdict = route(
        event_category=event_cat,
        confidence=confidence,
        fake=fake,
        duplicate_of=dup_id,
        text=report.text,
    )

    # high_impact = True when the report was routed to review due to category
    # or trigger words (for admin queue priority ordering)
    text_lower = (report.text or "").lower()
    is_high_impact = event_cat in HIGH_IMPACT_CATEGORIES or any(
        tw in text_lower for tw in TRIGGER_WORDS
    )

    # ── Persist results ───────────────────────────────────────────────────────
    report.event_category = event_cat
    report.classify_conf = confidence
    report.fake_score = fake
    report.trust_score = trust
    report.duplicate_of = dup_id
    report.high_impact = is_high_impact
    report.ml_verdict = verdict          # ML's suggestion; never overwritten by admin
    report.verification_status = verdict
    _pipeline_end = datetime.datetime.now(datetime.timezone.utc)
    report.ml_latency_ms = (
        (_pipeline_end - _pipeline_start).total_seconds() * 1000
    )

    await db.commit()
    await db.refresh(report)

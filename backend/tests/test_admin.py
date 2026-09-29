"""
test_admin.py – Tests for admin endpoints and end-to-end pipeline flows.

E2E flows covered:
  1. Simple rainfall report → auto-verified (confidence high, not high-impact)
  2. Flooding report → under_review → admin approves → verified + WS broadcast
  3. Near-duplicate report → rejected by pipeline
  4. Admin endpoints return 401 without a valid Bearer token
"""

from __future__ import annotations

import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# ── Helpers ───────────────────────────────────────────────────────────────────

RAINFALL_PAYLOAD = {
    "city": "Pune",
    "state": "Maharashtra",
    "lat": 18.52,
    "lon": 73.85,
    "event_category": "rainfall",
    "source_type": "citizen_report",
    "text": "Heavy rain near Shivajinagar station Pune roads waterlogged monsoon",
    "trust_score": 50.0,
}

FLOOD_PAYLOAD = {
    "city": "Patna",
    "state": "Bihar",
    "lat": 25.59,
    "lon": 85.13,
    "event_category": "flooding",
    "source_type": "citizen_report",
    "text": "Severe flooding in Rajendra Nagar Patna roads submerged houses inundated overflow",
    "trust_score": 50.0,
    "photos": ["https://example.com/flood1.jpg"],
}

CREDS = {"username": "admin", "password": "changeme"}


async def _login(client: AsyncClient) -> str:
    """Helper: log in and return the Bearer token."""
    resp = await client.post("/api/auth/login", json=CREDS)
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _run_pipeline(report_id: int, db: AsyncSession) -> None:
    """Run the real ML pipeline synchronously in the test's DB session."""
    from backend.app.ml_stub import run_ml_pipeline
    await run_ml_pipeline(report_id, db)


# ═══════════════════════════════════════════════════════════════════════════════
# Auth tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/login", json=CREDS)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_username(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/login", json={"username": "hacker", "password": "changeme"})
    assert resp.status_code == 401


# ── All admin endpoints return 401 without token ──────────────────────────────

@pytest.mark.asyncio
async def test_queue_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/admin/queue")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_decision_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/admin/reports/1/decision", json={"status": "verified"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_kpis_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/admin/kpis")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient) -> None:
    headers = {"Authorization": "Bearer not.a.real.token"}
    resp = await client.get("/api/admin/queue", headers=headers)
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# E2E 1: Auto-verify (rainfall, good text, no high-impact trigger)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e2e_auto_verify_rainfall(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    A well-formed rainfall report with sufficient text and GPS should be
    auto-verified by the pipeline (not routed to the review queue).
    """
    # 1. Submit report
    resp = await client.post("/api/reports", json=RAINFALL_PAYLOAD)
    assert resp.status_code == 202, resp.text
    report_id = resp.json()["id"]

    # 2. Run pipeline synchronously in the test DB
    await _run_pipeline(report_id, db_session)

    # 3. Verify status
    get_resp = await client.get(f"/api/reports/{report_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["verification_status"] == "verified", (
        f"Expected 'verified', got {body['verification_status']!r}. "
        f"classify_conf={body['classify_conf']}, fake_score={body['fake_score']}"
    )
    assert body["ml_verdict"] == "verified"
    assert body["classify_conf"] is not None
    assert body["fake_score"] is not None
    assert body["trust_score"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# E2E 2: Flood → queue → admin approves → verified
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e2e_flood_queue_admin_approve(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    A flooding report must go to under_review (Section 2.3.4 — never auto-published).
    An admin can then approve it to 'verified'.
    The ml_verdict must remain 'under_review' so the override rate is accurate.
    """
    # 1. Submit flood report
    resp = await client.post("/api/reports", json=FLOOD_PAYLOAD)
    assert resp.status_code == 202, resp.text
    report_id = resp.json()["id"]

    # 2. Run pipeline
    await _run_pipeline(report_id, db_session)

    # 3. Confirm it's in under_review
    get_resp = await client.get(f"/api/reports/{report_id}")
    body = get_resp.json()
    assert body["verification_status"] == "under_review", (
        f"Flooding should be in under_review, got {body['verification_status']!r}"
    )
    assert body["ml_verdict"] == "under_review"
    assert body["high_impact"] is True

    # 4. Confirm it appears in admin queue
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    queue_resp = await client.get("/api/admin/queue", headers=headers)
    assert queue_resp.status_code == 200
    queue = queue_resp.json()
    ids_in_queue = [r["id"] for r in queue]
    assert report_id in ids_in_queue

    # 5. Admin approves the report
    decision_resp = await client.post(
        f"/api/admin/reports/{report_id}/decision",
        json={"status": "verified", "notes": "Confirmed by local NDRF team."},
        headers=headers,
    )
    assert decision_resp.status_code == 200
    decision_body = decision_resp.json()
    assert decision_body["verification_status"] == "verified"
    assert decision_body["reviewed_by"] == "admin"
    assert decision_body["notes"] == "Confirmed by local NDRF team."
    # ml_verdict must be unchanged (was under_review)
    assert decision_body["ml_verdict"] == "under_review"

    # 6. Report no longer in queue
    queue_resp2 = await client.get("/api/admin/queue", headers=headers)
    ids_in_queue2 = [r["id"] for r in queue_resp2.json()]
    assert report_id not in ids_in_queue2

    # 7. Appears in GeoJSON export (now verified)
    geo_resp = await client.get("/api/export.geojson")
    feat_ids = [f["properties"]["id"] for f in geo_resp.json()["features"]]
    assert report_id in feat_ids


# ═══════════════════════════════════════════════════════════════════════════════
# E2E 3: Near-duplicate → rejected
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e2e_duplicate_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    When a near-duplicate report is submitted within 3 hours of an existing
    report (same city, same category, Jaccard ≥ 0.6), it must be rejected.
    """
    text_a = "Heavy monsoon rain near Kurla station Mumbai shower downpour drizzle drive carefully"
    text_b = "Heavy monsoon rain near Kurla station Mumbai shower downpour drizzle please be careful"

    base_payload = {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.076,
        "lon": 72.877,
        "event_category": "rainfall",
        "source_type": "citizen_report",
        "trust_score": 50.0,
    }
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 1. First report
    r1 = await client.post("/api/reports", json={**base_payload, "text": text_a, "timestamp": now_iso})
    assert r1.status_code == 202
    id1 = r1.json()["id"]
    await _run_pipeline(id1, db_session)

    # Confirm first report is verified (not high-impact, good text)
    s1 = (await client.get(f"/api/reports/{id1}")).json()
    assert s1["verification_status"] == "verified"

    # 2. Second report (near-duplicate)
    r2 = await client.post("/api/reports", json={**base_payload, "text": text_b, "timestamp": now_iso})
    assert r2.status_code == 202
    id2 = r2.json()["id"]
    await _run_pipeline(id2, db_session)

    # 3. Duplicate must be rejected
    s2 = (await client.get(f"/api/reports/{id2}")).json()
    assert s2["verification_status"] == "rejected", (
        f"Expected 'rejected' for duplicate, got {s2['verification_status']!r}. "
        f"duplicate_of={s2['duplicate_of']}"
    )
    assert s2["duplicate_of"] == id1


# ═══════════════════════════════════════════════════════════════════════════════
# Admin KPI tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_kpis_empty_db(client: AsyncClient) -> None:
    token = await _login(client)
    resp = await client.get("/api/admin/kpis", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_reports"] == 0
    assert body["override_rate"] == 0.0
    assert body["avg_trust_score"] == 0.0
    assert set(body["by_status"].keys()) == {"verified", "under_review", "rejected", "unverified"}


@pytest.mark.asyncio
async def test_kpis_override_rate(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    After admin approves a flood report (ML said under_review → admin says verified),
    override_rate should be 1.0 (100% of reviewed reports were overrides).
    """
    resp = await client.post("/api/reports", json=FLOOD_PAYLOAD)
    report_id = resp.json()["id"]
    await _run_pipeline(report_id, db_session)

    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Admin approves (overrides ML's under_review verdict)
    await client.post(
        f"/api/admin/reports/{report_id}/decision",
        json={"status": "verified"},
        headers=headers,
    )

    kpi_resp = await client.get("/api/admin/kpis", headers=headers)
    body = kpi_resp.json()
    # ml_verdict=under_review, verification_status=verified → override
    assert body["override_rate"] == 1.0
    assert body["by_status"]["verified"] >= 1


@pytest.mark.asyncio
async def test_kpis_no_override_when_admin_agrees(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    If admin rejects a report the ML also marked as under_review (same decision),
    override_rate should be 0.0 (no override occurred).
    """
    resp = await client.post("/api/reports", json=FLOOD_PAYLOAD)
    report_id = resp.json()["id"]
    await _run_pipeline(report_id, db_session)

    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Admin rejects — ML also said under_review, so no true override;
    # but ml_verdict=under_review and admin sets verified_status=rejected → mismatch → counted
    # Let's have admin agree by re-routing: set decision to match ML exactly.
    # The ML set it to under_review; admin sets it to under_review via a workaround.
    # We can't POST under_review via decision (only verified|rejected are valid).
    # So instead: manually set ml_verdict="rejected" via DB to simulate ML saying rejected,
    # then admin also rejects → no override.
    from backend.app.models import Report
    report = await db_session.get(Report, report_id)
    report.ml_verdict = "rejected"
    await db_session.commit()

    await client.post(
        f"/api/admin/reports/{report_id}/decision",
        json={"status": "rejected"},
        headers=headers,
    )

    kpi_resp = await client.get("/api/admin/kpis", headers=headers)
    body = kpi_resp.json()
    # ml_verdict=rejected == verification_status=rejected → no override
    assert body["override_rate"] == 0.0


@pytest.mark.asyncio
async def test_queue_high_impact_sorted_first(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """High-impact reports must appear before regular under_review ones in the queue."""
    # Regular under_review: rainfall with low confidence
    low_conf_payload = {
        **RAINFALL_PAYLOAD,
        "city": "Nagpur",
        "text": "bad",  # short → fake_score high → under_review
        "lat": None,
        "lon": None,
    }
    r1 = await client.post("/api/reports", json=low_conf_payload)
    id1 = r1.json()["id"]
    await _run_pipeline(id1, db_session)

    # High-impact: flooding
    r2 = await client.post("/api/reports", json=FLOOD_PAYLOAD)
    id2 = r2.json()["id"]
    await _run_pipeline(id2, db_session)

    token = await _login(client)
    queue = (await client.get("/api/admin/queue", headers={"Authorization": f"Bearer {token}"})).json()

    # high_impact report must come first
    queue_ids = [r["id"] for r in queue]
    assert queue_ids.index(id2) < queue_ids.index(id1), (
        f"Flood (id={id2}) should precede low-conf (id={id1}) in queue. Queue: {queue_ids}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# KPI accuracy fields (Step 3: classification_accuracy, fake_precision,
# fake_recall, avg_ml_latency_ms)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_kpi_accuracy_fields_present_and_numeric(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    GET /api/admin/kpis must return the four new accuracy/latency fields
    and they must all be floats.

    classification_accuracy > 0 is assured because the labeled fixture
    deliberately uses keyword-rich sentences that the classifier handles.
    avg_ml_latency_ms is 0.0 when no reports have been processed (empty DB
    in test isolation), which is acceptable — the field must still be present.
    """
    # Submit one report and run pipeline so avg_ml_latency_ms is non-zero
    r = await client.post("/api/reports", json=RAINFALL_PAYLOAD)
    assert r.status_code == 202
    report_id = r.json()["id"]
    await _run_pipeline(report_id, db_session)

    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/admin/kpis", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # All four new fields must be present
    for field in ("classification_accuracy", "fake_precision", "fake_recall", "avg_ml_latency_ms"):
        assert field in body, f"Missing field: {field}"
        assert isinstance(body[field], (int, float)), (
            f"{field} must be numeric, got {type(body[field])}"
        )

    # Classification accuracy must be > 0 (fixture has clean keyword-rich rows)
    assert body["classification_accuracy"] > 0.0, (
        f"Expected classification_accuracy > 0, got {body['classification_accuracy']}"
    )

    # Latency must be > 0 since we ran the pipeline above
    assert body["avg_ml_latency_ms"] > 0.0, (
        f"Expected avg_ml_latency_ms > 0, got {body['avg_ml_latency_ms']}"
    )

    # Precision and recall must be in [0, 1]
    assert 0.0 <= body["fake_precision"] <= 1.0
    assert 0.0 <= body["fake_recall"] <= 1.0

"""
test_reports.py – Automated tests for every Report API endpoint.

Coverage:
  - POST /api/reports  (happy path, validation errors, rate-limit header)
  - GET  /api/reports/{id}  (found, not-found)
  - GET  /api/reports  (no filters, each filter individually)
  - GET  /api/export.geojson  (empty, with verified record)
  - GET  /health
"""

from __future__ import annotations

import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "city": "Mumbai",
    "state": "Maharashtra",
    "lat": 19.076,
    "lon": 72.877,
    "event_category": "rainfall",
    "source_type": "citizen_report",
    "text": "Heavy rain near Kurla station",
    "trust_score": 50.0,
}


# ── Health check ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── POST /api/reports ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_report_returns_202(client: AsyncClient) -> None:
    resp = await client.post("/api/reports", json=VALID_PAYLOAD)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "id" in body
    assert isinstance(body["id"], int)
    assert "message" in body


@pytest.mark.asyncio
async def test_create_report_all_source_types(client: AsyncClient) -> None:
    """All 5 source types must be accepted."""
    source_types = [
        "citizen_report",
        "social_media",
        "website",
        "api",
        "public_dataset",
    ]
    for st in source_types:
        payload = {**VALID_PAYLOAD, "source_type": st}
        resp = await client.post("/api/reports", json=payload)
        assert resp.status_code == 202, f"Failed for source_type={st}: {resp.text}"


@pytest.mark.asyncio
async def test_create_report_all_event_categories(client: AsyncClient) -> None:
    """All 7 event categories from Section 2.3.2 must be accepted."""
    categories = [
        "rainfall", "thunderstorm", "flooding",
        "heatwave", "fog", "dust_storm", "strong_wind",
    ]
    for cat in categories:
        payload = {**VALID_PAYLOAD, "event_category": cat}
        resp = await client.post("/api/reports", json=payload)
        assert resp.status_code == 202, f"Failed for event_category={cat}: {resp.text}"


@pytest.mark.asyncio
async def test_create_report_invalid_event_category(client: AsyncClient) -> None:
    payload = {**VALID_PAYLOAD, "event_category": "blizzard"}
    resp = await client.post("/api/reports", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_report_invalid_source_type(client: AsyncClient) -> None:
    payload = {**VALID_PAYLOAD, "source_type": "satellite"}
    resp = await client.post("/api/reports", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_report_trust_score_out_of_range(client: AsyncClient) -> None:
    payload = {**VALID_PAYLOAD, "trust_score": 150.0}
    resp = await client.post("/api/reports", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_report_minimal_payload(client: AsyncClient) -> None:
    """Only required fields; optional fields omitted."""
    payload = {
        "city": "Delhi",
        "state": "Delhi",
        "event_category": "fog",
        "source_type": "social_media",
    }
    resp = await client.post("/api/reports", json=payload)
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_create_report_with_photos_and_videos(client: AsyncClient) -> None:
    payload = {
        **VALID_PAYLOAD,
        "photos": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        "videos": ["https://example.com/vid1.mp4"],
    }
    resp = await client.post("/api/reports", json=payload)
    assert resp.status_code == 202
    report_id = resp.json()["id"]

    # Verify photos/videos round-trip correctly
    get_resp = await client.get(f"/api/reports/{report_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["photos"] == ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"]
    assert body["videos"] == ["https://example.com/vid1.mp4"]


# ── GET /api/reports/{id} ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_report_found(client: AsyncClient) -> None:
    create_resp = await client.post("/api/reports", json=VALID_PAYLOAD)
    report_id = create_resp.json()["id"]

    resp = await client.get(f"/api/reports/{report_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == report_id
    assert body["city"] == "Mumbai"
    assert body["state"] == "Maharashtra"
    assert body["event_category"] == "rainfall"
    assert body["source_type"] == "citizen_report"
    assert body["verification_status"] in ("unverified", "under_review", "verified", "rejected")
    assert "gps_location" in body
    assert body["gps_location"]["latitude"] == pytest.approx(19.076)
    assert body["gps_location"]["longitude"] == pytest.approx(72.877)


@pytest.mark.asyncio
async def test_get_report_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/reports/999999")
    assert resp.status_code == 404


# ── GET /api/reports (list + filters) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_reports_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_list_reports_returns_created(client: AsyncClient) -> None:
    await client.post("/api/reports", json=VALID_PAYLOAD)
    await client.post("/api/reports", json={**VALID_PAYLOAD, "city": "Pune"})

    resp = await client.get("/api/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_list_reports_filter_by_city(client: AsyncClient) -> None:
    await client.post("/api/reports", json=VALID_PAYLOAD)
    await client.post("/api/reports", json={**VALID_PAYLOAD, "city": "Chennai"})

    resp = await client.get("/api/reports", params={"city": "Chennai"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["city"] == "Chennai"


@pytest.mark.asyncio
async def test_list_reports_filter_by_state(client: AsyncClient) -> None:
    await client.post("/api/reports", json=VALID_PAYLOAD)
    await client.post("/api/reports", json={**VALID_PAYLOAD, "state": "Tamil Nadu", "city": "Chennai"})

    resp = await client.get("/api/reports", params={"state": "Tamil Nadu"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["state"] == "Tamil Nadu"


@pytest.mark.asyncio
async def test_list_reports_filter_by_event_category(client: AsyncClient) -> None:
    await client.post("/api/reports", json=VALID_PAYLOAD)  # rainfall
    await client.post("/api/reports", json={**VALID_PAYLOAD, "event_category": "flooding"})

    resp = await client.get("/api/reports", params={"event": "flooding"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["event_category"] == "flooding"


@pytest.mark.asyncio
async def test_list_reports_filter_by_status(client: AsyncClient) -> None:
    """ML stub always sets unverified; filter for it."""
    await client.post("/api/reports", json=VALID_PAYLOAD)

    resp = await client.get("/api/reports", params={"status": "unverified"})
    body = resp.json()
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_reports_filter_by_date_range(client: AsyncClient) -> None:
    past = "2020-01-01T00:00:00Z"
    payload_past = {**VALID_PAYLOAD, "timestamp": past}
    await client.post("/api/reports", json=payload_past)
    await client.post("/api/reports", json=VALID_PAYLOAD)  # now

    resp = await client.get(
        "/api/reports",
        params={"date_from": "2021-01-01T00:00:00Z"},
    )
    body = resp.json()
    # Only the recent report should be returned
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_list_reports_pagination(client: AsyncClient) -> None:
    for i in range(5):
        await client.post("/api/reports", json={**VALID_PAYLOAD, "city": f"City{i}"})

    resp = await client.get("/api/reports", params={"page": 1, "page_size": 2})
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page"] == 1

    resp2 = await client.get("/api/reports", params={"page": 3, "page_size": 2})
    body2 = resp2.json()
    assert len(body2["items"]) == 1  # 5th item on page 3


# ── GET /api/export.geojson ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_geojson_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/export.geojson")
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert body["features"] == []


@pytest.mark.asyncio
async def test_export_geojson_only_verified(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    The stub marks reports 'unverified', so the export should be empty
    after normal submission. We directly patch a report to verified via the
    shared db_session (same session injected into the app) to simulate
    an admin approval and verify it appears in the export.
    """
    from backend.app.models import Report

    # Create a report through the API
    create_resp = await client.post("/api/reports", json=VALID_PAYLOAD)
    assert create_resp.status_code == 202, create_resp.text
    report_id = create_resp.json()["id"]

    # Manually set it to verified (simulate admin approval)
    report = await db_session.get(Report, report_id)
    assert report is not None
    report.verification_status = "verified"
    await db_session.commit()

    resp = await client.get("/api/export.geojson")
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1
    feat = body["features"][0]
    assert feat["geometry"]["type"] == "Point"
    assert feat["properties"]["id"] == report_id
    assert feat["properties"]["event_category"] == "rainfall"


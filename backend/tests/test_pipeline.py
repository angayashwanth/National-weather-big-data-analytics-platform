"""
test_pipeline.py – Table-driven unit tests for each pipeline stage.

Tests are fully offline (no network, no running server).
Async tests (find_duplicate) use the db_session fixture from conftest.py.
"""

from __future__ import annotations

import datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.pipeline import (
    classify,
    fake_score,
    find_duplicate,
    jaccard,
    route,
    source_trust,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1 – classify
# ═══════════════════════════════════════════════════════════════════════════════

CLASSIFY_CASES = [
    # (text, hint, expected_category, min_conf)
    # English keywords
    ("heavy monsoon rain near Shivajinagar shower drizzle precipitation", None, "rainfall", 0.5),
    ("flood alert roads submerged overflow", None, "flooding", 0.5),
    ("lightning thunder hailstorm approaching", None, "thunderstorm", 0.5),
    ("dense fog visibility zero on highway", None, "fog", 0.5),
    ("extreme heat heatwave 45 degree celsius", None, "heatwave", 0.5),
    ("dust storm sandstorm visibility poor", None, "dust_storm", 0.5),
    ("strong wind gale cyclone gusts 80kmph", None, "strong_wind", 0.5),
    # Hindi / Devanagari keywords
    ("मुंबई में आज भारी बारिश वर्षा हो रही है", None, "rainfall", 0.5),
    ("बाढ़ जलजमाव सैलाब खतरा", None, "flooding", 0.5),
    ("गड़गड़ाहट बिजली ओलावृष्टि", None, "thunderstorm", 0.5),
    ("घना कोहरा दृश्यता शून्य", None, "fog", 0.5),
    ("भीषण गर्मी लू चल रही है तापमान", None, "heatwave", 0.5),
    ("धूलभरी आंधी रेतीली आंधी", None, "dust_storm", 0.5),
    ("तेज हवा चक्रवात तूफानी हवा", None, "strong_wind", 0.5),
    # hint used when text is empty
    ("", "flooding", "flooding", 0.2),
    ("", None, "rainfall", 0.0),
    # hint boosts confidence when it agrees
    ("rainfall rain shower drizzle", "rainfall", "rainfall", 0.8),
]


@pytest.mark.parametrize("text,hint,expected_cat,min_conf", CLASSIFY_CASES)
def test_classify(text, hint, expected_cat, min_conf):
    cat, conf = classify(text, hint)
    assert cat == expected_cat, f"Expected {expected_cat!r}, got {cat!r} for text={text!r}"
    assert conf >= min_conf, f"Confidence {conf} < {min_conf} for text={text!r}"
    assert 0.0 <= conf <= 1.0


def test_classify_returns_valid_category():
    """All returned categories must be one of the 7 defined types."""
    valid = {
        "rainfall", "thunderstorm", "flooding",
        "heatwave", "fog", "dust_storm", "strong_wind",
    }
    for text in ["hello", "some unknown text xyz", "", "rain flood thunder"]:
        cat, _ = classify(text)
        assert cat in valid, f"Got invalid category {cat!r} for text={text!r}"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2 – fake_score
# ═══════════════════════════════════════════════════════════════════════════════

FAKE_SCORE_CASES = [
    # (text, lat, lon, max_expected_score, description)
    (
        "Heavy rain near Kurla station Mumbai roads waterlogged",
        19.076, 72.877,
        0.20,
        "Genuine long report with GPS → low score",
    ),
    (
        "rain",
        None, None,
        1.0,
        "Too-short text, no GPS → high score",
    ),
    (
        "old video from 2019 flood in Chennai",
        13.0, 80.2,
        1.0,
        "Old content phrase → high score",
    ),
    (
        "share now viral flood video forward this breaking news",
        19.0, 72.8,
        0.50,
        "Spam words → elevated score",
    ),
    (
        "पुराना वीडियो बाढ़ का दृश्य देखें",
        19.0, 72.8,
        1.0,
        "Hindi old-video phrase → high score",
    ),
    (
        "Moderate rainfall observed in Bengaluru this evening",
        12.97, 77.59,
        0.20,
        "Genuine report with GPS → low score",
    ),
    (
        "Heavy rain",
        None, None,
        1.0,
        "Short + no GPS → ≥ 0.50",
    ),
]


@pytest.mark.parametrize("text,lat,lon,max_score,desc", FAKE_SCORE_CASES)
def test_fake_score(text, lat, lon, max_score, desc):
    score = fake_score(text, lat, lon)
    assert 0.0 <= score <= 1.0, f"{desc}: score out of [0,1]"
    assert score <= max_score, f"{desc}: score {score} > max {max_score}"


def test_fake_score_no_text():
    assert fake_score(None, None, None) >= 0.4
    assert fake_score("", None, None) >= 0.4


def test_fake_score_gps_adds_to_score():
    with_gps = fake_score("Heavy rain in Delhi", 28.6, 77.2)
    without_gps = fake_score("Heavy rain in Delhi", None, None)
    assert without_gps > with_gps


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3 – source_trust
# ═══════════════════════════════════════════════════════════════════════════════

SOURCE_TRUST_CASES = [
    # (source_type, has_photo, has_gps, min_expected, max_expected)
    ("api",            False, False, 90, 100),
    ("public_dataset", False, False, 85, 100),
    ("website",        True,  True,  85, 100),
    ("website",        False, False, 60,  75),
    ("citizen_report", True,  True,  75, 100),
    ("citizen_report", False, True,  60,  80),
    ("citizen_report", False, False, 50,  65),
    ("social_media",   True,  True,  60,  80),
    ("social_media",   False, False, 35,  50),
    ("unknown_source", False, False,  0,  50),  # unknown falls back to base 30
]


@pytest.mark.parametrize("src,photo,gps,lo,hi", SOURCE_TRUST_CASES)
def test_source_trust(src, photo, gps, lo, hi):
    score = source_trust(src, photo, gps)
    assert lo <= score <= hi, (
        f"source_type={src} photo={photo} gps={gps}: score={score} not in [{lo},{hi}]"
    )


def test_source_trust_always_bounded():
    for src in ["api", "citizen_report", "social_media", "website", "public_dataset"]:
        for photo in (True, False):
            for gps in (True, False):
                score = source_trust(src, photo, gps)
                assert 0 <= score <= 100


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 4 – jaccard (unit) and find_duplicate (async/DB)
# ═══════════════════════════════════════════════════════════════════════════════

JACCARD_CASES = [
    ("rain flood mumbai roads", "rain flood mumbai roads", 1.0),
    ("rain flood mumbai roads", "rain flood mumbai street", 0.6),  # 3/5
    ("rain mumbai area", "snow delhi region", 0.0),
    ("", "rain", 0.0),
    (None, "rain", 0.0),
    ("rain", None, 0.0),
]


@pytest.mark.parametrize("a,b,expected", JACCARD_CASES)
def test_jaccard(a, b, expected):
    result = jaccard(a, b)
    assert abs(result - expected) < 0.05, f"jaccard({a!r},{b!r})={result}, expected≈{expected}"


@pytest.mark.asyncio
async def test_find_duplicate_detects_near_duplicate(db_session: AsyncSession):
    """Two very similar reports in the same city/category within 3h → detected."""
    from backend.app.models import Report

    now = datetime.datetime.now(datetime.timezone.utc)
    text_a = "Heavy rain near Kurla station Mumbai roads flooded waterlogged drive carefully"
    text_b = "Heavy rain near Kurla station Mumbai roads flooded waterlogged please be careful"

    r1 = Report(
        timestamp=now - datetime.timedelta(hours=1),
        city="Mumbai", state="Maharashtra",
        lat=19.0, lon=72.8,
        event_category="rainfall", source_type="citizen_report",
        verification_status="unverified", trust_score=50.0,
        text=text_a, photos="", videos="",
    )
    db_session.add(r1)
    await db_session.flush()

    dup_id = await find_duplicate(
        text=text_b,
        event_category="rainfall",
        city="Mumbai",
        timestamp=now,
        exclude_id=None,
        db=db_session,
    )
    assert dup_id == r1.id


@pytest.mark.asyncio
async def test_find_duplicate_no_match_different_city(db_session: AsyncSession):
    """Same text but different city → not a duplicate."""
    from backend.app.models import Report

    now = datetime.datetime.now(datetime.timezone.utc)
    text = "Heavy rain roads flooded waterlogged drive carefully near station"

    r1 = Report(
        timestamp=now - datetime.timedelta(hours=1),
        city="Chennai", state="Tamil Nadu",
        lat=13.0, lon=80.2,
        event_category="rainfall", source_type="citizen_report",
        verification_status="unverified", trust_score=50.0,
        text=text, photos="", videos="",
    )
    db_session.add(r1)
    await db_session.flush()

    dup_id = await find_duplicate(
        text=text,
        event_category="rainfall",
        city="Mumbai",  # different city
        timestamp=now,
        exclude_id=None,
        db=db_session,
    )
    assert dup_id is None


@pytest.mark.asyncio
async def test_find_duplicate_no_match_outside_window(db_session: AsyncSession):
    """Same text, same city, but older than 3h → not a duplicate."""
    from backend.app.models import Report

    now = datetime.datetime.now(datetime.timezone.utc)
    text = "Heavy rain roads flooded waterlogged drive carefully near station"

    r1 = Report(
        timestamp=now - datetime.timedelta(hours=5),  # outside 3h window
        city="Mumbai", state="Maharashtra",
        lat=19.0, lon=72.8,
        event_category="rainfall", source_type="citizen_report",
        verification_status="unverified", trust_score=50.0,
        text=text, photos="", videos="",
    )
    db_session.add(r1)
    await db_session.flush()

    dup_id = await find_duplicate(
        text=text,
        event_category="rainfall",
        city="Mumbai",
        timestamp=now,
        exclude_id=None,
        db=db_session,
    )
    assert dup_id is None


@pytest.mark.asyncio
async def test_find_duplicate_excludes_self(db_session: AsyncSession):
    """A report should not be flagged as a duplicate of itself."""
    from backend.app.models import Report

    now = datetime.datetime.now(datetime.timezone.utc)
    text = "Heavy rain roads flooded waterlogged drive carefully near station"

    r1 = Report(
        timestamp=now,
        city="Mumbai", state="Maharashtra",
        lat=19.0, lon=72.8,
        event_category="rainfall", source_type="citizen_report",
        verification_status="unverified", trust_score=50.0,
        text=text, photos="", videos="",
    )
    db_session.add(r1)
    await db_session.flush()

    dup_id = await find_duplicate(
        text=text,
        event_category="rainfall",
        city="Mumbai",
        timestamp=now,
        exclude_id=r1.id,
        db=db_session,
    )
    assert dup_id is None


# ═══════════════════════════════════════════════════════════════════════════════
# Routing step
# ═══════════════════════════════════════════════════════════════════════════════

ROUTE_CASES = [
    # (event_category, confidence, fake, duplicate_of, text, expected_status)
    # Happy path → auto-verified
    ("rainfall",     0.80, 0.10, None, "Heavy rain near Kurla station Mumbai waterlogged", "verified"),
    ("fog",          0.75, 0.05, None, "Dense fog on highway visibility low", "verified"),
    ("thunderstorm", 0.80, 0.10, None, "Lightning thunder storm approaching tonight", "verified"),
    # High fake score
    ("rainfall",     0.80, 0.65, None, "old video share now viral flood", "under_review"),
    # High-impact categories always → queue
    ("flooding",     0.90, 0.05, None, "Roads submerged overflow", "under_review"),
    ("dust_storm",   0.90, 0.05, None, "Dust storm visibility poor", "under_review"),
    # Trigger words → queue
    ("rainfall",     0.80, 0.10, None, "cloudburst expected rescue teams deployed", "under_review"),
    ("rainfall",     0.80, 0.10, None, "3 casualties reported near the station", "under_review"),
    ("thunderstorm", 0.80, 0.10, None, "people trapped on rooftop", "under_review"),
    # Low confidence → queue
    ("rainfall",     0.30, 0.10, None, "some weather event", "under_review"),
    # Duplicate → rejected (highest priority)
    ("rainfall",     0.80, 0.10, 42,   "Heavy rain Kurla Mumbai roads flooded", "rejected"),
    # Duplicate even if high confidence + no fake
    ("flooding",     0.95, 0.02, 7,    "flood alert submerged", "rejected"),
]


@pytest.mark.parametrize(
    "event_cat,conf,fake,dup_of,text,expected", ROUTE_CASES
)
def test_route(event_cat, conf, fake, dup_of, text, expected):
    result = route(event_cat, conf, fake, dup_of, text)
    assert result == expected, (
        f"route({event_cat},{conf},{fake},{dup_of},{text!r}) = {result!r}, "
        f"expected {expected!r}"
    )

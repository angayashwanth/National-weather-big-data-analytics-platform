"""
pipeline.py – Four-stage ML pipeline implementing Sections 2.3.3 and 2.3.4.

Stages
------
1. classify(text, hint)              -> (event_category, confidence 0..1)
2. fake_score(text, lat, lon)        -> 0..1  (higher = more suspicious)
3. source_trust(source_type, ...)    -> 0..100
4. find_duplicate(...)               -> Optional[int] (id of earlier duplicate)

Routing step
------------
Applies Section 2.3.4 routing rules and returns a verification_status string.
"""

from __future__ import annotations

import datetime
import io
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── Keyword lexicons (English + Hindi/Devanagari) ─────────────────────────────

EVENT_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "rainfall": {
        "en": [
            "rain", "rainfall", "drizzle", "shower", "precipitation",
            "downpour", "monsoon", "rainy", "cloudburst rain",
        ],
        "hi": ["बारिश", "वर्षा", "बूंदाबांदी", "बरसात", "मूसलाधार", "बौछार"],
    },
    "thunderstorm": {
        "en": [
            "thunder", "thunderstorm", "lightning", "lightning bolt",
            "hailstorm", "hail", "thunder cloud",
        ],
        "hi": [
            "गड़गड़ाहट", "बिजली", "ओलावृष्टि", "आकाशीय बिजली",
            "अंधड़", "ओला", "तड़ितपात",
        ],
    },
    "flooding": {
        "en": [
            "flood", "flooding", "waterlog", "waterlogged", "waterlogging",
            "inundation", "inundated", "submerged", "overflow", "deluge",
            "floodwater", "flash flood",
        ],
        "hi": ["बाढ़", "जलजमाव", "सैलाब", "जलभराव", "डूब", "बाढ़ग्रस्त"],
    },
    "heatwave": {
        "en": [
            "heat", "heatwave", "hot", "scorching", "swelter", "temperature",
            "heat stroke", "sunstroke", "high temperature", "heat index",
        ],
        "hi": ["गर्मी", "लू", "तापमान", "उमस", "भीषण गर्मी", "लू लगना"],
    },
    "fog": {
        "en": [
            "fog", "foggy", "mist", "misty", "haze", "hazardous visibility",
            "dense fog", "visibility", "smog",
        ],
        "hi": ["कोहरा", "धुंध", "कुहासा", "धुंधला", "घना कोहरा"],
    },
    "dust_storm": {
        "en": [
            "dust", "dust storm", "sandstorm", "sand storm",
            "brown cloud", "dust cloud", "sand cloud",
        ],
        "hi": [
            "धूल", "धूलभरी आंधी", "रेतीली आंधी",
            "बालू आंधी", "धूल का तूफान",
        ],
    },
    "strong_wind": {
        "en": [
            "wind", "gale", "cyclone", "windy", "gusts", "gust",
            "storm force", "strong wind", "hurricane",
        ],
        "hi": ["हवा", "तेज हवा", "चक्रवात", "झक्कड़", "तूफानी हवा"],
    },
}

# Shared Hindi words that appear in multiple categories — these are tracked
# separately so they do NOT inflate a single category's score unfairly.
_AMBIGUOUS_HI = {"आंधी", "तूफान"}  # can mean thunderstorm, dust_storm, or strong_wind

SPAM_WORDS = [
    "share now", "forward this", "viral", "fake news", "breaking news",
    "unbelievable", "must watch", "click here",
]

OLD_CONTENT_PHRASES = [
    "old video", "purana video", "पुराना वीडियो", "पुरानी वीडियो",
    "old footage", "recycled", "not recent", "from 2018", "from 2019",
    "from 2020", "from 2021",
]

# Section 2.3.4: these categories NEVER auto-publish
HIGH_IMPACT_CATEGORIES = {"flooding", "dust_storm"}

# Trigger words that also force human review
TRIGGER_WORDS = {
    "cloudburst", "trapped", "casualties", "casualty", "rescue",
    "stranded", "death", "died", "missing", "dead", "danger",
}

SOURCE_TRUST_BASE: dict[str, float] = {
    "api": 90.0,
    "public_dataset": 85.0,
    "website": 60.0,
    "citizen_report": 50.0,
    "social_media": 35.0,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """
    Whitespace+punctuation tokenizer that handles both Latin and Devanagari.
    Strips punctuation, lowercases Latin; preserves Devanagari casing.
    """
    cleaned = re.sub(r"[^\w\u0900-\u097F]+", " ", text.lower())
    return {t for t in cleaned.split() if len(t) > 2}


# ── Stage 1: Event classification ────────────────────────────────────────────

def classify(
    text: Optional[str],
    hint: Optional[str] = None,
) -> Tuple[str, float]:
    """
    Stage 1: Classify event category from free-text using keyword lexicon.

    Supports English and Hindi (Devanagari) keywords for all 7 categories.
    `hint` is the submitter's self-reported category; it breaks ties and
    gets a small confidence boost when it agrees with the top ML result.

    Returns (event_category, confidence) where confidence ∈ [0, 1].
    """
    if not text or not text.strip():
        if hint and hint in EVENT_KEYWORDS:
            return hint, 0.3
        return "rainfall", 0.1  # safe default

    text_lower = text.lower()
    scores: dict[str, int] = {cat: 0 for cat in EVENT_KEYWORDS}

    for category, kw_groups in EVENT_KEYWORDS.items():
        for kw in kw_groups["en"]:
            if kw in text_lower:
                scores[category] += 1
        for kw in kw_groups["hi"]:
            if kw in _AMBIGUOUS_HI:
                # Ambiguous Hindi word: only counts if no better match yet
                if kw in text:
                    scores[category] += 1
            elif kw in text:
                scores[category] += 2  # unambiguous Hindi match is stronger signal

    best_cat = max(scores, key=lambda k: scores[k])
    best_score = scores[best_cat]
    total_hits = sum(scores.values())

    if total_hits == 0:
        if hint and hint in EVENT_KEYWORDS:
            return hint, 0.3
        return "rainfall", 0.1

    # Confidence: fraction of hits attributed to the best category
    confidence = min(0.95, 0.40 + (best_score / total_hits) * 0.55)

    # Hint agreement boost
    if hint == best_cat:
        confidence = min(0.98, confidence + 0.05)

    return best_cat, round(confidence, 3)


# ── Stage 2: Fake / misleading report score ───────────────────────────────────

def fake_score(
    text: Optional[str],
    lat: Optional[float],
    lon: Optional[float],
) -> float:
    """
    Stage 2: Heuristic credibility score — 0 = genuine, 1 = very suspicious.

    Heuristics (additive, clamped to 1.0):
    - Text absent or < 20 chars              → +0.40
    - Old/recycled content phrase found      → +0.50
    - Spam/viral language (per hit, max 0.3) → +0.15 each
    - No GPS coordinates                     → +0.10
    """
    score = 0.0
    text_str = (text or "").strip()
    text_lower = text_str.lower()

    if len(text_str) < 20:
        score += 0.40

    for phrase in OLD_CONTENT_PHRASES:
        if phrase.lower() in text_lower or phrase in text_str:
            score += 0.50
            break  # one hit is enough

    spam_hits = sum(1 for sw in SPAM_WORDS if sw in text_lower)
    score += min(0.30, spam_hits * 0.15)

    if lat is None or lon is None:
        score += 0.10

    return round(min(1.0, score), 3)


# ── Stage 3: Source trust score ───────────────────────────────────────────────

def source_trust(
    source_type: str,
    has_photo: bool,
    has_gps: bool,
) -> float:
    """
    Stage 3: Source credibility score 0–100.

    Base score by source_type (API/public_dataset are inherently authoritative).
    Bonuses for corroborating evidence (photo, GPS).
    """
    base = SOURCE_TRUST_BASE.get(source_type, 30.0)
    bonus = 0.0
    if has_photo:
        bonus += 15.0
    if has_gps:
        bonus += 10.0
    return min(100.0, base + bonus)


# ── Stage 4: Near-duplicate detection ────────────────────────────────────────

def jaccard(a: Optional[str], b: Optional[str]) -> float:
    """Token-level Jaccard similarity between two texts (0.0–1.0)."""
    if not a or not b:
        return 0.0
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# Perceptual-hash threshold: Hamming distance ≤ 10 out of 64 bits ≈ 85% similar
_PHASH_THRESHOLD = 10


def _phash_from_bytes(data: bytes):
    """Compute pHash for raw image bytes. Returns None on any error."""
    try:
        import imagehash
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        return imagehash.phash(img)
    except Exception:
        return None


def _phash_from_local_url(url: str):
    """Load a local /media/<file> path or MinIO URL and compute pHash. Returns None on error."""
    if not url:
        return None
    try:
        from .media_store import MEDIA_LOCAL_DIR, _get_minio

        # 1. Local storage URL: /media/<filename>
        if url.startswith("/media/"):
            rel = url.removeprefix("/media/")
            filepath = MEDIA_LOCAL_DIR / rel
            if filepath.exists():
                return _phash_from_bytes(filepath.read_bytes())
            filepath_default = Path("./media_uploads") / rel
            if filepath_default.exists():
                return _phash_from_bytes(filepath_default.read_bytes())

        # 2. MinIO URL: http(s)://<endpoint>/<bucket>/<object_key>
        elif url.startswith("http://") or url.startswith("https://"):
            client, bucket = _get_minio()
            if client is not None and bucket and f"/{bucket}/" in url:
                try:
                    object_key = url.split(f"/{bucket}/", 1)[1]
                    response = client.get_object(bucket, object_key)
                    data = response.read()
                    response.close()
                    response.release_conn()
                    return _phash_from_bytes(data)
                except Exception as me:
                    logger.debug("pHash MinIO fetch error: %s", me)

        # 3. Direct filename or local relative path fallback
        else:
            filepath = MEDIA_LOCAL_DIR / url
            if filepath.exists():
                return _phash_from_bytes(filepath.read_bytes())

        return None
    except Exception:
        return None


def _phash_list(photo_urls: List[str]) -> list:
    """
    Return a list of computed pHash values for all image URLs.
    Skips non-images and failed hashes silently.
    """
    from .media_store import ALLOWED_IMAGE_TYPES  # avoid circular at module level
    import mimetypes

    hashes = []
    for url in photo_urls:
        if not url:
            continue
        # Guess type from extension or URL
        clean_url = url.split("?")[0]
        mime = mimetypes.guess_type(clean_url)[0] or ""
        ext = Path(clean_url).suffix.lower()
        if mime not in ALLOWED_IMAGE_TYPES and ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}:
            continue
        h = _phash_from_local_url(url)
        if h is not None:
            hashes.append(h)
    return hashes


def _any_phash_near_duplicate(hashes_a: list, hashes_b: list) -> bool:
    """Return True if any pair of hashes is within _PHASH_THRESHOLD Hamming distance."""
    if not hashes_a or not hashes_b:
        return False
    for ha in hashes_a:
        for hb in hashes_b:
            try:
                if abs(ha - hb) <= _PHASH_THRESHOLD:
                    return True
            except Exception:
                continue
    return False


async def find_duplicate(
    text: Optional[str],
    event_category: str,
    city: str,
    timestamp: datetime.datetime,
    exclude_id: Optional[int],
    db: AsyncSession,
    photos: Optional[List[str]] = None,
) -> Optional[int]:
    """
    Stage 4: Near-duplicate detection.

    Two-pass check:
    1. Photo perceptual hash (pHash): if the incoming report has images
       and any candidate shares a pHash within Hamming distance ≤ 10,
       it is considered a duplicate (same scene photographed twice).
    2. Text Jaccard ≥ 0.6 on candidate reports within ±3h / same city+event.

    Only non-rejected prior reports are considered as duplicate sources.
    """
    from .models import Report  # local import avoids circular dependency

    if timestamp.tzinfo is not None:
        window_start = timestamp - datetime.timedelta(hours=3)
        window_end = timestamp + datetime.timedelta(hours=3)
    else:
        window_start = timestamp - datetime.timedelta(hours=3)
        window_end = timestamp + datetime.timedelta(hours=3)

    q = select(Report).where(
        and_(
            Report.event_category == event_category,
            Report.city.ilike(city),
            Report.timestamp >= window_start,
            Report.timestamp <= window_end,
            Report.verification_status != "rejected",
        )
    )
    result = await db.execute(q)
    candidates = result.scalars().all()

    # --- Pass 1: perceptual-hash image comparison -------------------------
    incoming_hashes = _phash_list(photos or [])
    if incoming_hashes:
        for candidate in candidates:
            if exclude_id is not None and candidate.id == exclude_id:
                continue
            candidate_photos = [p for p in (candidate.photos or "").split(",") if p]
            if not candidate_photos:
                continue
            candidate_hashes = _phash_list(candidate_photos)
            if _any_phash_near_duplicate(incoming_hashes, candidate_hashes):
                logger.info(
                    "find_duplicate: pHash match report id=%s", candidate.id
                )
                return candidate.id

    # --- Pass 2: text Jaccard similarity ----------------------------------
    for candidate in candidates:
        if exclude_id is not None and candidate.id == exclude_id:
            continue
        if jaccard(text, candidate.text) >= 0.6:
            return candidate.id

    return None


# ── Routing (Section 2.3.4) ───────────────────────────────────────────────────

def route(
    event_category: str,
    confidence: float,
    fake: float,
    duplicate_of: Optional[int],
    text: Optional[str],
) -> str:
    """
    Determines verification_status based on pipeline outputs.

    Priority order (first matching rule wins):
    1. Duplicate detected          → rejected
    2. fake_score ≥ 0.6            → under_review
    3. High-impact category        → under_review  (NEVER auto-published)
    4. Trigger word in text        → under_review  (NEVER auto-published)
    5. Low confidence (< 0.5)      → under_review
    6. Otherwise                   → verified  (auto-published)
    """
    if duplicate_of is not None:
        return "rejected"

    if fake >= 0.6:
        return "under_review"

    if event_category in HIGH_IMPACT_CATEGORIES:
        return "under_review"

    text_lower = (text or "").lower()
    if any(tw in text_lower for tw in TRIGGER_WORDS):
        return "under_review"

    if confidence < 0.5:
        return "under_review"

    return "verified"

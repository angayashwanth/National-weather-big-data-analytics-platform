"""
backend/app/connectors/social_mock.py – Simulated social-media connector (SourceType.social_media)

Reads scripts/sample_tweets.json and produces ReportCreate objects that
mimic what a live X (Twitter) connector would produce.

To replace this with a real X API connector:
  1. Create a new class that extends Connector (or this class).
  2. Override fetch() to call tweepy / X API v2 instead of reading JSON.
  3. Re-use _parse_tweet() for normalisation – no other changes required.

The JSON file must be a list of objects with at minimum:
  { "id": str, "text": str, "created_at": str (ISO-8601), "handle": str }
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Connector, CITY_TABLE, HINDI_CITY_MAP
from ..schemas import EventCategory, ReportCreate, SourceType

logger = logging.getLogger(__name__)

# Default path relative to the repo root – resolved at import time
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_JSON = _REPO_ROOT / "scripts" / "sample_tweets.json"
if not _DEFAULT_JSON.exists():
    _fallback = Path.cwd() / "scripts" / "sample_tweets.json"
    if _fallback.exists():
        _DEFAULT_JSON = _fallback

# Same keyword set as the news scraper, self-contained to keep modules independent
_EVENT_KW: list[tuple[list[str], EventCategory]] = [
    (["flood", "flooded", "inundat", "waterlog", "submerg",
      "बाढ़", "जलभराव", "जलमग्न"],               EventCategory.flooding),
    (["thunderstorm", "lightning", "cyclone",
      "गड़गड़ाहट", "बिजली", "चक्रवात"],            EventCategory.thunderstorm),
    (["heavy rain", "rainfall", "rain", "downpour", "cloudburst",
      "बारिश", "वर्षा", "बरसात", "मूसलाधार"],      EventCategory.rainfall),
    (["dust storm", "sandstorm", "धूलभरी आंधी"],   EventCategory.dust_storm),
    (["heatwave", "heat wave", "scorching", "गर्मी", "लू"], EventCategory.heatwave),
    (["fog", "dense fog", "कोहरा", "धुंध"],        EventCategory.fog),
    (["strong wind", "gusty", "gale", "तेज़ हवा"],  EventCategory.strong_wind),
]


def _detect_category(text: str) -> Optional[EventCategory]:
    lower = text.lower()
    for keywords, cat in _EVENT_KW:
        if any(kw in lower for kw in keywords):
            return cat
    return None


def _detect_city(text: str) -> Optional[tuple[str, str, float, float]]:
    sorted_keys = sorted(CITY_TABLE.keys(), key=len, reverse=True)
    lower = text.lower()
    for key in sorted_keys:
        if key in lower:
            state, lat, lon = CITY_TABLE[key]
            return key.title(), state, lat, lon

    sorted_hindi = sorted(HINDI_CITY_MAP.keys(), key=len, reverse=True)
    for hi_name in sorted_hindi:
        if hi_name in text:
            canonical = HINDI_CITY_MAP[hi_name]
            state, lat, lon = CITY_TABLE[canonical]
            return canonical.title(), state, lat, lon
    return None


class SocialMockConnector(Connector):
    """
    Reads a JSON file of mock tweets and converts them to ReportCreate objects.

    Parameters
    ----------
    json_path : str | Path | None
        Path to sample_tweets.json.  Defaults to scripts/sample_tweets.json.
    """

    SOURCE_TYPE = SourceType.social_media

    def __init__(self, json_path: Optional[os.PathLike] = None) -> None:
        self._json_path = Path(json_path) if json_path else _DEFAULT_JSON

    def _load_tweets(self) -> List[Dict[str, Any]]:
        with open(self._json_path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("sample_tweets.json must be a JSON array")
        return data

    @staticmethod
    def _parse_tweet(tweet: Dict[str, Any]) -> Optional[ReportCreate]:
        """
        Convert a single tweet dict to ReportCreate.
        Returns None if the tweet is not weather-related or city is unknown.
        """
        text = str(tweet.get("text", "")).strip()
        if not text:
            return None

        cat = _detect_category(text)
        if cat is None:
            return None

        city_info = _detect_city(text)
        if city_info is None:
            return None

        city, state, lat, lon = city_info

        return ReportCreate(
            city=city,
            state=state,
            lat=lat,
            lon=lon,
            event_category=cat,
            source_type=SourceType.social_media,
            text=text[:4096],
            source_handle=tweet.get("handle"),
            trust_score=40.0,   # social media: lower default trust
        )

    def fetch(self) -> List[ReportCreate]:
        try:
            tweets = self._load_tweets()
        except FileNotFoundError:
            logger.error("SocialMock: file not found: %s", self._json_path)
            return []
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("SocialMock: JSON error: %s", exc)
            return []

        reports: List[ReportCreate] = []
        for tweet in tweets:
            report = self._parse_tweet(tweet)
            if report is not None:
                reports.append(report)
                logger.debug("SocialMock: %s → %s", report.city, report.event_category)

        logger.info(
            "SocialMock: %d/%d tweets yielded weather reports",
            len(reports), len(tweets),
        )
        return reports

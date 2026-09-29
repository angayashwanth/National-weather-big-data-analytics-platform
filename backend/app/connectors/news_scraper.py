"""
backend/app/connectors/news_scraper.py – News / RSS connector (SourceType.website)

Scrapes ONE configurable web source for weather-related headlines then
geocodes city names found in the text against the built-in CITY_TABLE.

Default source: NDTV Weather RSS feed (freely accessible, no login).
Any other RSS or plain-HTML page can be plugged in via the constructor.

Design
------
- If the URL ends in `.rss` / `.xml` or response Content-Type contains
  `xml`, we parse it as RSS (iterating <item> / <entry> elements).
- Otherwise we parse it as HTML and extract <a> / <h2> / <h3> headlines.
- For each headline we:
    1. Search for a known city name (case-insensitive, longest match wins).
    2. Search for an event keyword to decide EventCategory.
    3. Emit at most one ReportCreate per headline.

The scraper is intentionally simple – "One configurable page" as requested,
no recursive crawling.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .base import Connector, CITY_TABLE, HINDI_CITY_MAP, geocode
from ..schemas import EventCategory, ReportCreate, SourceType

logger = logging.getLogger(__name__)

# Default source – NDTV weather/disaster section (RSS)
DEFAULT_URL = "https://feeds.feedburner.com/ndtvnews-india-news"

# Keyword → EventCategory (longest match applied first for each headline)
_EVENT_KW: list[tuple[list[str], EventCategory]] = [
    (["flood", "flooded", "inundat", "waterlog", "submerg", "deluge",
      "बाढ़", "जलभराव", "जलमग्न"],              EventCategory.flooding),
    (["cloudburst", "cloudburst rain", "flash flood",
      "बादल फटा", "भारी बारिश"],                 EventCategory.flooding),
    (["cyclone", "hurricane", "typhoon", "storm surge"],
                                                   EventCategory.thunderstorm),
    (["thunderstorm", "lightning", "thunder", "hailstorm",
      "गड़गड़ाहट", "बिजली", "ओलावृष्टि"],           EventCategory.thunderstorm),
    (["heavy rain", "rainfall", "rain", "drizzle", "downpour", "shower",
      "precipitation", "monsoon", "बारिश", "वर्षा", "बरसात"],
                                                   EventCategory.rainfall),
    (["dust storm", "sandstorm", "dust cloud", "haboob",
      "धूलभरी आंधी", "रेतीली आंधी"],              EventCategory.dust_storm),
    (["heatwave", "heat wave", "scorching", "extreme heat",
      "गर्मी", "लू", "तापमान"],                   EventCategory.heatwave),
    (["fog", "dense fog", "low visibility",
      "कोहरा", "धुंध"],                           EventCategory.fog),
    (["strong wind", "gale", "gusty", "wind speed",
      "तेज़ हवा", "आंधी"],                        EventCategory.strong_wind),
]

# Minimum headline length (chars) worth processing
_MIN_TEXT_LEN = 15
# Maximum text length stored in the report
_MAX_TEXT_LEN = 512


def _detect_category(text: str) -> Optional[EventCategory]:
    """Return the first matching EventCategory for the given text, or None."""
    lower = text.lower()
    for keywords, cat in _EVENT_KW:
        if any(kw in lower for kw in keywords):
            return cat
    return None


def _detect_city(text: str) -> Optional[tuple[str, str, float, float]]:
    """
    Find the first known city in `text`.
    Returns (city_display, state, lat, lon) or None.
    Tries longest city name first to prefer "Visakhapatnam" over "Visa".
    """
    sorted_cities = sorted(CITY_TABLE.keys(), key=len, reverse=True)
    lower = text.lower()
    for key in sorted_cities:
        if key in lower:
            state, lat, lon = CITY_TABLE[key]
            # Capitalize for display
            display = key.title()
            return display, state, lat, lon

    sorted_hindi = sorted(HINDI_CITY_MAP.keys(), key=len, reverse=True)
    for hi_name in sorted_hindi:
        if hi_name in text:
            canonical = HINDI_CITY_MAP[hi_name]
            state, lat, lon = CITY_TABLE[canonical]
            return canonical.title(), state, lat, lon
    return None


def _clean(text: str) -> str:
    """Strip extra whitespace and truncate."""
    return re.sub(r"\s+", " ", text).strip()[:_MAX_TEXT_LEN]


class NewsScraperConnector(Connector):
    """
    Scrapes one news/RSS URL for weather headlines.

    Parameters
    ----------
    url : str
        The RSS feed or HTML page to scrape.
    timeout : int
        HTTP timeout in seconds.
    session : requests.Session | None
        Injected session (for testing without live network).
    """

    SOURCE_TYPE = SourceType.website

    def __init__(self, url: str = DEFAULT_URL, timeout: int = 15,
                 session: Optional[requests.Session] = None) -> None:
        self._url = url
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (IMD-WeatherBot/1.0; "
                "+https://github.com/sih069) WeatherCrawler"
            )
        })

    # ------------------------------------------------------------------
    # Public parse helpers (used directly in tests with saved HTML/XML)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_rss(content: bytes) -> List[str]:
        """Return a list of item titles + descriptions from an RSS/Atom feed."""
        soup = BeautifulSoup(content, "lxml-xml")
        items = soup.find_all("item") or soup.find_all("entry")
        texts: List[str] = []
        for item in items:
            title = (item.find("title") or {}).get_text(strip=True) if item.find("title") else ""
            desc  = (item.find("description") or item.find("summary") or {})
            desc_text = desc.get_text(strip=True) if desc else ""
            combined = f"{title}. {desc_text}".strip(". ")
            if combined:
                texts.append(_clean(combined))
        return texts

    @staticmethod
    def parse_html(content: bytes) -> List[str]:
        """Return visible headline strings from an HTML page."""
        soup = BeautifulSoup(content, "lxml")
        # Remove script/style/nav noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        texts: List[str] = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
            text = tag.get_text(strip=True)
            if len(text) >= _MIN_TEXT_LEN:
                texts.append(_clean(text))
        return list(dict.fromkeys(texts))  # deduplicate preserving order

    def _extract_headlines(self, response: requests.Response) -> List[str]:
        ct = response.headers.get("Content-Type", "")
        url_lower = self._url.lower()
        if "xml" in ct or url_lower.endswith((".rss", ".xml", ".atom")):
            return self.parse_rss(response.content)
        return self.parse_html(response.content)

    @staticmethod
    def headline_to_report(headline: str) -> Optional[ReportCreate]:
        """
        Convert a single headline string into a ReportCreate, or None if
        the headline isn't weather-related or no city is found.
        """
        cat = _detect_category(headline)
        if cat is None:
            return None

        city_info = _detect_city(headline)
        if city_info is None:
            return None

        city, state, lat, lon = city_info
        return ReportCreate(
            city=city,
            state=state,
            lat=lat,
            lon=lon,
            event_category=cat,
            source_type=SourceType.website,
            text=headline,
            trust_score=55.0,   # scraped news: moderate trust
        )

    def fetch(self) -> List[ReportCreate]:
        try:
            resp = self._session.get(self._url, timeout=self._timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("NewsScraper: failed to fetch %s: %s", self._url, exc)
            return []

        headlines = self._extract_headlines(resp)
        logger.info("NewsScraper: %d raw headlines from %s", len(headlines), self._url)

        reports: List[ReportCreate] = []
        seen: set[str] = set()
        for hl in headlines:
            report = self.headline_to_report(hl)
            if report is None:
                continue
            key = f"{report.city}:{report.event_category}"
            if key in seen:
                continue  # local dedup (ML pipeline does full dedup later)
            seen.add(key)
            reports.append(report)
            logger.info("NewsScraper: %s → %s", report.city, report.event_category)

        return reports

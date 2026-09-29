"""
backend/app/connectors/open_meteo.py – Open-Meteo API connector (SourceType.api)

Fetches current weather for ~10 Indian cities from the free, no-key-required
Open-Meteo API (https://open-meteo.com/).

Variables polled
----------------
  precipitation      → rainfall / flooding  (if extreme)
  rain               → rainfall
  snowfall           → ignored (India)
  wind_speed_10m     → strong_wind (if > 40 km/h)
  weathercode        → WMO codes mapped to EventCategory

WMO code mapping (partial, sufficient for Indian weather events)
  0-2   → (skip – clear)
  3     → thunderstorm (if combined with rain)
  45,48 → fog
  51-57 → rainfall
  61-67 → rainfall
  71-77 → (skip – snow)
  80-82 → rainfall
  85-86 → (skip – snow)
  95    → thunderstorm
  96,99 → thunderstorm + hail
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from .base import Connector, CITY_TABLE
from ..schemas import EventCategory, ReportCreate, SourceType

logger = logging.getLogger(__name__)

# The 10 cities the connector fetches – subset of CITY_TABLE.
CITIES: list[tuple[str, str, float, float]] = [
    ("Mumbai",     "Maharashtra",      19.0760,  72.8777),
    ("Delhi",      "Delhi",            28.6139,  77.2090),
    ("Chennai",    "Tamil Nadu",       13.0827,  80.2707),
    ("Kolkata",    "West Bengal",      22.5726,  88.3639),
    ("Bengaluru",  "Karnataka",        12.9716,  77.5946),
    ("Hyderabad",  "Telangana",        17.3850,  78.4867),
    ("Pune",       "Maharashtra",      18.5204,  73.8567),
    ("Ahmedabad",  "Gujarat",          23.0225,  72.5714),
    ("Jaipur",     "Rajasthan",        26.9124,  75.7873),
    ("Patna",      "Bihar",            25.5941,  85.1376),
]

# WMO weather interpretation codes → EventCategory
_WMO_MAP: dict[int, EventCategory] = {
    **{c: EventCategory.fog          for c in [45, 48]},
    **{c: EventCategory.rainfall     for c in [51, 53, 55, 56, 57,
                                                61, 63, 65, 66, 67,
                                                80, 81, 82]},
    **{c: EventCategory.thunderstorm for c in [95, 96, 99]},
}

BASE_URL = "https://api.open-meteo.com/v1/forecast"


def _wmo_to_category(code: int, wind_kmh: float, precip_mm: float) -> Optional[EventCategory]:
    """Map WMO code (+ wind/precip thresholds) to EventCategory or None."""
    if precip_mm >= 50:
        return EventCategory.flooding
    if wind_kmh >= 60:
        return EventCategory.flooding   # severe storm → flood-risk
    if code in _WMO_MAP:
        cat = _WMO_MAP[code]
        # Upgrade heavy rain to flooding when precipitation is extreme
        if cat == EventCategory.rainfall and precip_mm >= 50:
            return EventCategory.flooding
        return cat
    if wind_kmh >= 40:
        return EventCategory.strong_wind
    if precip_mm >= 5:
        return EventCategory.rainfall
    return None  # clear weather – skip


def _build_description(city: str, cat: EventCategory, code: int,
                        precip: float, wind: float) -> str:
    labels: dict[EventCategory, str] = {
        EventCategory.rainfall:     f"precipitation {precip:.1f} mm",
        EventCategory.flooding:     f"extreme precipitation {precip:.1f} mm",
        EventCategory.thunderstorm: "thunderstorm (WMO {code})",
        EventCategory.fog:          "dense fog (WMO {code})",
        EventCategory.strong_wind:  f"strong wind {wind:.0f} km/h",
    }
    desc = labels.get(cat, f"weather code {code}").format(code=code)
    return (
        f"Open-Meteo API report for {city}: {desc}. "
        f"Wind {wind:.0f} km/h, precipitation {precip:.1f} mm."
    )


class OpenMeteoConnector(Connector):
    """
    Pulls current-hour weather from Open-Meteo for CITIES.

    Parameters
    ----------
    timeout : int
        HTTP request timeout in seconds (default 10).
    session : requests.Session | None
        Injected session for testing (avoids live network calls in tests).
    """

    SOURCE_TYPE = SourceType.api

    def __init__(self, timeout: int = 10,
                 session: Optional[requests.Session] = None) -> None:
        self._timeout = timeout
        self._session = session or requests.Session()

    def _call_api(self, lat: float, lon: float) -> Dict[str, Any]:
        """Hit Open-Meteo and return the raw JSON dict."""
        params = {
            "latitude":  lat,
            "longitude": lon,
            "current":   "precipitation,rain,wind_speed_10m,weathercode",
            "wind_speed_unit": "kmh",
            "timezone":  "Asia/Kolkata",
        }
        resp = self._session.get(BASE_URL, params=params, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def parse_response(city: str, state: str, lat: float, lon: float,
                       data: Dict[str, Any]) -> Optional[ReportCreate]:
        """
        Convert a raw Open-Meteo JSON response into a ReportCreate.
        Returns None when current conditions are not a weather event worth reporting.
        """
        try:
            cur = data["current"]
            precip   = float(cur.get("precipitation") or cur.get("rain") or 0)
            wind_kmh = float(cur.get("wind_speed_10m") or 0)
            wmo_code = int(cur.get("weathercode", 0))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("OpenMeteo parse error for %s: %s", city, exc)
            return None

        cat = _wmo_to_category(wmo_code, wind_kmh, precip)
        if cat is None:
            return None

        return ReportCreate(
            city=city,
            state=state,
            lat=lat,
            lon=lon,
            event_category=cat,
            source_type=SourceType.api,
            text=_build_description(city, cat, wmo_code, precip, wind_kmh),
            source_handle="open-meteo.com",
            trust_score=90.0,  # official API data → high baseline trust
        )

    def fetch(self) -> List[ReportCreate]:
        reports: List[ReportCreate] = []
        for city, state, lat, lon in CITIES:
            try:
                data = self._call_api(lat, lon)
                report = self.parse_response(city, state, lat, lon, data)
                if report is not None:
                    reports.append(report)
                    logger.info("OpenMeteo: fetched %s → %s", city, report.event_category)
            except requests.RequestException as exc:
                logger.warning("OpenMeteo: HTTP error for %s: %s", city, exc)
            except Exception as exc:
                logger.warning("OpenMeteo: unexpected error for %s: %s", city, exc)
        return reports

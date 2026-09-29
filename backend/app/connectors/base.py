"""
backend/app/connectors/base.py

Abstract base class for all data-source connectors.

Each connector must implement fetch() and return a list of ReportCreate
objects that are already normalised to the Section 2.3.2 schema.
The runner then POST-s them through the normal /api/reports intake
pipeline so the ML stages apply uniformly.

No platform specifics belong here – this file may never need editing.
"""

from __future__ import annotations

import abc
import datetime
from typing import List

from ..schemas import EventCategory, ReportCreate, SourceType


# ---------------------------------------------------------------------------
# Built-in city → (state, lat, lon) lookup table used by every connector
# that needs to geocode a free-text city name.  ~30 major Indian cities.
# ---------------------------------------------------------------------------

CITY_TABLE: dict[str, tuple[str, float, float]] = {
    "mumbai":      ("Maharashtra", 19.0760,  72.8777),
    "delhi":       ("Delhi",       28.6139,  77.2090),
    "chennai":     ("Tamil Nadu",  13.0827,  80.2707),
    "kolkata":     ("West Bengal", 22.5726,  88.3639),
    "bengaluru":   ("Karnataka",   12.9716,  77.5946),
    "bangalore":   ("Karnataka",   12.9716,  77.5946),
    "hyderabad":   ("Telangana",   17.3850,  78.4867),
    "pune":        ("Maharashtra", 18.5204,  73.8567),
    "ahmedabad":   ("Gujarat",     23.0225,  72.5714),
    "jaipur":      ("Rajasthan",   26.9124,  75.7873),
    "lucknow":     ("Uttar Pradesh", 26.8467, 80.9462),
    "patna":       ("Bihar",       25.5941,  85.1376),
    "bhopal":      ("Madhya Pradesh", 23.2599, 77.4126),
    "surat":       ("Gujarat",     21.1702,  72.8311),
    "nagpur":      ("Maharashtra", 21.1458,  79.0882),
    "bhubaneswar": ("Odisha",      20.2961,  85.8245),
    "guwahati":    ("Assam",       26.1445,  91.7362),
    "chandigarh":  ("Punjab",      30.7333,  76.7794),
    "thiruvananthapuram": ("Kerala", 8.5241, 76.9366),
    "kochi":       ("Kerala",      9.9312,   76.2673),
    "indore":      ("Madhya Pradesh", 22.7196, 75.8577),
    "varanasi":    ("Uttar Pradesh", 25.3176, 82.9739),
    "amritsar":    ("Punjab",      31.6340,  74.8723),
    "jodhpur":     ("Rajasthan",   26.2389,  73.0243),
    "visakhapatnam": ("Andhra Pradesh", 17.6868, 83.2185),
    "coimbatore":  ("Tamil Nadu",  11.0168,  76.9558),
    "madurai":     ("Tamil Nadu",  9.9252,   78.1198),
    "ranchi":      ("Jharkhand",   23.3441,  85.3096),
    "agra":        ("Uttar Pradesh", 27.1767, 78.0081),
    "dehradun":    ("Uttarakhand", 30.3165,  78.0322),
}

HINDI_CITY_MAP: dict[str, str] = {
    "मुंबई": "mumbai",
    "दिल्ली": "delhi",
    "चेन्नई": "chennai",
    "कोलकाता": "kolkata",
    "कलकत्ता": "kolkata",
    "बेंगलुरु": "bengaluru",
    "बैंगलोर": "bengaluru",
    "हैदराबाद": "hyderabad",
    "पुणे": "pune",
    "अहमदाबाद": "ahmedabad",
    "जयपुर": "jaipur",
    "लखनऊ": "lucknow",
    "पटना": "patna",
    "भोपाल": "bhopal",
    "सूरत": "surat",
    "नागपुर": "nagpur",
    "भुवनेश्वर": "bhubaneswar",
    "गुवाहाटी": "guwahati",
    "चंडीगढ़": "chandigarh",
    "तिरुवनंतपुरम": "thiruvananthapuram",
    "कोच्चि": "kochi",
    "इंदौर": "indore",
    "वाराणसी": "varanasi",
    "बनारस": "varanasi",
    "अमृतसर": "amritsar",
    "जोधपुर": "jodhpur",
    "विशाखापट्टनम": "visakhapatnam",
    "विशाखापत्तनम": "visakhapatnam",
    "कोयंबटूर": "coimbatore",
    "मदुरै": "madurai",
    "रांची": "ranchi",
    "आगरा": "agra",
    "देहरादून": "dehradun",
}


def geocode(city_raw: str) -> tuple[str, float | None, float | None]:
    """
    Look up a city name (case-insensitive or Hindi) in CITY_TABLE.
    Returns (state, lat, lon) or (city_raw, None, None) if not found.
    """
    key = city_raw.strip().lower()
    if key in HINDI_CITY_MAP:
        key = HINDI_CITY_MAP[key]
    if key in CITY_TABLE:
        state, lat, lon = CITY_TABLE[key]
        return state, lat, lon
    return city_raw, None, None


class Connector(abc.ABC):
    """
    Abstract connector base.  Every concrete connector must declare:
      - SOURCE_TYPE : SourceType   (the enum value it produces)
    and implement:
      - fetch()                    (network / file I/O; returns list[ReportCreate])

    The runner calls fetch() and immediately POST-s the results through the
    normal /api/reports endpoint so the ML pipeline applies uniformly.
    """

    SOURCE_TYPE: SourceType

    @abc.abstractmethod
    def fetch(self) -> List[ReportCreate]:
        """Pull data from the external source and return normalised reports."""
        ...

    # ------------------------------------------------------------------
    # Convenience helpers available to all subclasses
    # ------------------------------------------------------------------

    @staticmethod
    def now_utc() -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)

    @staticmethod
    def geocode(city: str) -> tuple[str, float | None, float | None]:
        return geocode(city)

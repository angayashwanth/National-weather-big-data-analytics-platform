"""
scripts/seed.py – Mumbai Flash-Flood Demo: a coherent 2-hour incident narrative.

Storyline (all set in REAL Mumbai localities):
  T-120 min  Light rain starts (Andheri East / Santacruz) → auto-verified
  T-105 min  Rain intensifies near Kurla (social media) → auto-verified
  T-90  min  Moderate rainfall + waterlogging near Sion → auto-verified
  T-75  min  Thunderstorm cell forms over Ghatkopar → under_review (high-impact category)
  T-60  min  First flooding reports Dharavi / Chunabhatti → under_review (high-impact)
  T-50  min  Flooding worsens; residents trapped near Matunga → high-impact queue
  T-40  min  DUPLICATE of T-50 report (near-identical text) → rejected by dedup
  T-30  min  Obvious spam/fake: "forward this video" + old media reference → under_review
  T-20  min  Critical: Mithi river overflow, road submerged, people trapped → queue
  T-10  min  Rescue team deployment confirmed (API source, high trust) → verified
  T-5   min  Rain easing in Andheri; isolated flooding remains → verified
  T-0         Current: road clearance update → verified

Usage (PowerShell, from repo root, with server running on :8000):
    .\.venv\Scripts\python.exe scripts/seed.py

Rate-limit aware: 6.5s between posts = ~9/min, stays under 10/min.
"""

import sys
import time
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import httpx
except ImportError:
    print("Install httpx first: .venv\\Scripts\\pip install httpx")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8000"
now = datetime.now(timezone.utc)


# ── Mumbai flash-flood incident reports (chronological) ───────────────────────

REPORTS = [
    # ── T-120: Light rain starts – Andheri East ──────────────────────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.1197,
        "lon": 72.8697,
        "event_category": "rainfall",
        "source_type": "citizen_report",
        "text": (
            "Light rain started in Andheri East Mumbai, roads slightly wet near "
            "Sakinaka junction. Carry umbrellas. Moderate shower expected."
        ),
        "trust_score": 52.0,
        "timestamp": (now - timedelta(hours=2)).isoformat(),
    },
    # ── T-105: Rain intensifies – Kurla (social media) ───────────────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0728,
        "lon": 72.8826,
        "event_category": "rainfall",
        "source_type": "social_media",
        "source_handle": "@MumbaiRains",
        "text": (
            "Heavy rain intensifying near Kurla station Mumbai. Roads starting to "
            "waterlog near LBS Marg. Motorists advised to avoid underpasses. "
            "Monsoon downpour ongoing #MumbaiRains #IMD"
        ),
        "trust_score": 40.0,
        "timestamp": (now - timedelta(minutes=105)).isoformat(),
    },
    # ── T-90: Waterlogging – Sion ─────────────────────────────────────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0388,
        "lon": 72.8619,
        "event_category": "rainfall",
        "source_type": "website",
        "text": (
            "Sion area Mumbai: moderate to heavy rainfall continues. Waterlogging "
            "reported near Sion circle and King's Circle. Water levels knee-deep "
            "in low-lying areas. BMC pumps deployed."
        ),
        "trust_score": 62.0,
        "timestamp": (now - timedelta(minutes=90)).isoformat(),
    },
    # ── T-75: Thunderstorm develops – Ghatkopar ───────────────────────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0860,
        "lon": 72.9081,
        "event_category": "thunderstorm",
        "source_type": "social_media",
        "source_handle": "@GhatkoparLocals",
        "text": (
            "Thunderstorm with lightning over Ghatkopar Mumbai. Dark clouds, loud "
            "thunder, lightning strikes near Vikhroli pipe road. Stay indoors, "
            "unplug electronics. Heavy rain with gusty winds 60 kmph. #Thunderstorm"
        ),
        "trust_score": 42.0,
        "timestamp": (now - timedelta(minutes=75)).isoformat(),
    },
    # ── T-60: First flooding – Dharavi ────────────────────────────────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0478,
        "lon": 72.8528,
        "event_category": "flooding",
        "source_type": "citizen_report",
        "text": (
            "Flooding in Dharavi Mumbai: roads completely submerged near 90-feet road "
            "intersection. Water chest-high in ground floor homes near transit camp. "
            "Residents evacuating. Urgent: need pumps and NDRF assistance."
        ),
        "trust_score": 58.0,
        "timestamp": (now - timedelta(minutes=60)).isoformat(),
    },
    # ── T-50: Flooding worsens – Matunga (CRITICAL, HIGH-IMPACT → queue) ─────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0228,
        "lon": 72.8416,
        "event_category": "flooding",
        "source_type": "citizen_report",
        "photos": ["https://example.com/matunga_flood_t50.jpg"],
        "text": (
            "Critical flooding near Matunga East station Mumbai. Residents trapped "
            "on rooftops near Tilak Nagar road. Water level 4 feet above road level. "
            "Mithi river overflow expected imminently. Rescue teams needed urgently. "
            "People trapped unable to move."
        ),
        "trust_score": 68.0,
        "timestamp": (now - timedelta(minutes=50)).isoformat(),
    },
    # ── T-40: DUPLICATE of T-50 (near-identical text → rejected by dedup) ────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0228,
        "lon": 72.8416,
        "event_category": "flooding",
        "source_type": "citizen_report",
        "text": (
            "Critical flooding near Matunga East station Mumbai. Residents trapped "
            "on rooftops near Tilak Nagar road. Water level 4 feet above road level. "
            "Mithi river overflow expected imminently. People cannot move need rescue."
        ),
        "trust_score": 55.0,
        "timestamp": (now - timedelta(minutes=42)).isoformat(),
    },
    # ── T-30: Spam/fake – old video forwarded as current (→ under_review) ────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": None,
        "lon": None,
        "event_category": "flooding",
        "source_type": "social_media",
        "source_handle": "@ViralNews24x7",
        "text": (
            "Old video 2019 Mumbai floods viral breaking forward now share immediately "
            "to all groups. This is old footage not current please share breaking alert "
            "viral flood video forward this to everyone now."
        ),
        "trust_score": 20.0,
        "timestamp": (now - timedelta(minutes=30)).isoformat(),
    },
    # ── T-20: Mithi river overflow (CRITICAL → queue) ─────────────────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0576,
        "lon": 72.8777,
        "event_category": "flooding",
        "source_type": "citizen_report",
        "photos": ["https://example.com/mithi_overflow_t20.jpg"],
        "text": (
            "Mithi river has overflowed near Kurla-Sion Link Road Mumbai. Road N M Joshi "
            "Marg submerged. Several vehicles swept away. At least 6 people trapped in cars. "
            "BMC and NDRF teams en route. Situation critical — avoid Kurla-Sion Link Road."
        ),
        "trust_score": 72.0,
        "timestamp": (now - timedelta(minutes=20)).isoformat(),
    },
    # ── T-10: Rescue deployment confirmed (API → auto-verified) ──────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0576,
        "lon": 72.8777,
        "event_category": "flooding",
        "source_type": "api",
        "text": (
            "BMC Emergency OPS: 4 NDRF teams deployed to Kurla-Sion Link Road Mumbai. "
            "3 inflatable boats in water. 6 people rescued as of 14:30 IST. "
            "Mithi river water level 2.4m above warning threshold. Road remains closed."
        ),
        "trust_score": 90.0,
        "timestamp": (now - timedelta(minutes=10)).isoformat(),
    },
    # ── T-5: Rain easing – Andheri (→ auto-verified) ─────────────────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.1197,
        "lon": 72.8697,
        "event_category": "rainfall",
        "source_type": "citizen_report",
        "text": (
            "Rain easing in Andheri East Mumbai. Drizzle now, roads still flooded in "
            "pockets near Sakinaka. Avoid low-lying areas. IMD says intensity reducing "
            "over next 2 hours. Monsoon shower tapering off."
        ),
        "trust_score": 55.0,
        "timestamp": (now - timedelta(minutes=5)).isoformat(),
    },
    # ── T-0: Road clearance update (→ auto-verified) ──────────────────────────
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0388,
        "lon": 72.8619,
        "event_category": "flooding",
        "source_type": "website",
        "text": (
            "Update from BMC: Sion-Kurla Link Road partially re-opened after emergency "
            "drain clearance. Water receding from Dharavi. Normal traffic expected in "
            "2–3 hours. Mithi river water level still above danger mark. Stay vigilant."
        ),
        "trust_score": 70.0,
        "timestamp": now.isoformat(),
    },
]


def post_report(client: httpx.Client, payload: dict, idx: int) -> None:
    try:
        resp = client.post(f"{BASE_URL}/api/reports", json=payload, timeout=10)
        if resp.status_code == 202:
            data = resp.json()
            print(f"  [{idx:02d}] [OK]   id={data['id']:3d}  {payload['city']} / {payload['event_category']:<12}")
        elif resp.status_code == 429:
            print(f"  [{idx:02d}] [WAIT] Rate limited — waiting 65s...")
            time.sleep(65)
            resp = client.post(f"{BASE_URL}/api/reports", json=payload, timeout=10)
            data = resp.json()
            print(f"  [{idx:02d}] [OK]   id={data.get('id','?')}  {payload['city']} / {payload['event_category']}")
        else:
            print(f"  [{idx:02d}] [FAIL] {resp.status_code} {resp.text[:120]}")
    except Exception as exc:
        print(f"  [{idx:02d}] [ERROR] {exc}")


def main() -> None:
    print("=" * 62)
    print(" Mumbai Flash-Flood Demo Seed")
    print(f" Posting {len(REPORTS)} incident reports to {BASE_URL}")
    print("=" * 62)
    print()

    try:
        with httpx.Client() as probe:
            health = probe.get(f"{BASE_URL}/health", timeout=5)
            assert health.json()["status"] == "ok"
    except Exception:
        print("ERROR: Server not reachable. Start it first:")
        print(r"  .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload")
        sys.exit(1)

    print("Narrative timeline (T = flash-flood peak):")
    timeline = [
        "T-120 Light rain starts (Andheri East)",
        "T-105 Rain intensifies (Kurla, social)",
        "T-90  Waterlogging (Sion)",
        "T-75  Thunderstorm (Ghatkopar)",
        "T-60  First flooding (Dharavi)",
        "T-50  Critical flooding + rooftop trapping (Matunga) → QUEUE",
        "T-40  Near-duplicate of T-50 → REJECTED by dedup",
        "T-30  Spam/fake old viral video → QUEUE",
        "T-20  Mithi overflow, people trapped (Kurla-Sion) → QUEUE",
        "T-10  Rescue deployment confirmed (API) → VERIFIED",
        "T-5   Rain easing (Andheri)",
        "T-0   Road clearance update",
    ]
    for t in timeline:
        print(f"  {t}")
    print()
    print("Submitting...\n")

    with httpx.Client() as client:
        for i, report in enumerate(REPORTS, start=1):
            post_report(client, report, i)
            if i < len(REPORTS):
                time.sleep(6.5)

    print("\nDone. Verify with:")
    print(f"  GET {BASE_URL}/api/reports?page_size=20")
    print(f"  GET {BASE_URL}/api/admin/kpis  (Bearer token required)")
    print(f"  GET {BASE_URL}/api/export.geojson")


if __name__ == "__main__":
    main()

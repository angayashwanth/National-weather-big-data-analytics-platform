"""
backend/app/connectors/run.py – Connector runner

Usage (from repo root, with backend running on :8000):
    python -m app.connectors.run

Flags:
    --url      Base URL of the API (default: http://127.0.0.1:8000)
    --dry-run  Parse and print reports but do NOT POST to the API
    --only     Comma-separated subset of connectors: openmeteo,news,social
    --json     Path to sample_tweets.json (overrides default path)
    --rss      RSS / HTML URL for the news scraper
    --delay    Seconds to wait between POST requests (default: 6.5 to stay
               under 10/min rate limit)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List

import requests

# Allow running as: python -m app.connectors.run or python -m backend.app.connectors.run
_backend_dir = Path(__file__).resolve().parents[2]
_repo_dir = Path(__file__).resolve().parents[3]
for _p in (str(_backend_dir), str(_repo_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from app.connectors.open_meteo import OpenMeteoConnector
    from app.connectors.news_scraper import NewsScraperConnector
    from app.connectors.social_mock import SocialMockConnector
    from app.schemas import ReportCreate
except ImportError:
    from backend.app.connectors.open_meteo import OpenMeteoConnector  # type: ignore
    from backend.app.connectors.news_scraper import NewsScraperConnector  # type: ignore
    from backend.app.connectors.social_mock import SocialMockConnector  # type: ignore
    from backend.app.schemas import ReportCreate  # type: ignore

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
logger = logging.getLogger("connectors.run")

DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_DELAY = 6.5   # seconds – keeps under 10/min rate limit


def _post_report(session: requests.Session, base_url: str, report: ReportCreate) -> bool:
    """POST a single report to /api/reports. Returns True on HTTP 202."""
    try:
        resp = session.post(
            f"{base_url}/api/reports",
            json=report.model_dump(mode="json"),
            timeout=10,
        )
        if resp.status_code == 202:
            data = resp.json()
            logger.info("[OK] id=%-4s  %-16s  %s", data["id"], report.city, report.event_category)
            return True
        if resp.status_code == 429:
            logger.warning("[WAIT] Rate limited – sleeping 65s before retry")
            time.sleep(65)
            resp = session.post(
                f"{base_url}/api/reports",
                json=report.model_dump(mode="json"),
                timeout=10,
            )
            if resp.status_code == 202:
                return True
        logger.error("[FAIL] %s %s", resp.status_code, resp.text[:120])
        return False
    except requests.RequestException as exc:
        logger.error("[ERROR] %s", exc)
        return False


def run(
    base_url: str = DEFAULT_URL,
    dry_run: bool = False,
    only: list[str] | None = None,
    tweet_json: str | None = None,
    rss_url: str | None = None,
    delay: float = DEFAULT_DELAY,
) -> None:
    """Main entry-point; also callable from other Python code."""
    all_reports: List[ReportCreate] = []

    active = set(only) if only else {"openmeteo", "news", "social"}

    if "openmeteo" in active:
        logger.info("=== Open-Meteo connector ===")
        reports = OpenMeteoConnector().fetch()
        logger.info("Open-Meteo: %d reports", len(reports))
        all_reports.extend(reports)

    if "news" in active:
        logger.info("=== News scraper connector ===")
        kwargs: dict = {}
        if rss_url:
            kwargs["url"] = rss_url
        reports = NewsScraperConnector(**kwargs).fetch()
        logger.info("News scraper: %d reports", len(reports))
        all_reports.extend(reports)

    if "social" in active:
        logger.info("=== Social mock connector ===")
        kwargs = {}
        if tweet_json:
            kwargs["json_path"] = tweet_json
        reports = SocialMockConnector(**kwargs).fetch()
        logger.info("Social mock: %d reports", len(reports))
        all_reports.extend(reports)

    logger.info("=== Total reports to submit: %d ===", len(all_reports))

    if dry_run:
        for r in all_reports:
            print(f"  [DRY-RUN] {r.city:18s} {r.event_category:12s}  {r.source_type}  {(r.text or '')[:80]}")
        return

    # Health-check before bulk submission
    try:
        health = requests.get(f"{base_url}/health", timeout=5)
        assert health.json()["status"] == "ok"
    except Exception:
        logger.error("Server not reachable at %s – aborting", base_url)
        sys.exit(1)

    session = requests.Session()
    ok = fail = 0
    for i, report in enumerate(all_reports, 1):
        success = _post_report(session, base_url, report)
        if success:
            ok += 1
        else:
            fail += 1
        if i < len(all_reports):
            time.sleep(delay)

    logger.info("Done: %d submitted, %d failed", ok, fail)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IMD Weather Platform Connector Runner")
    p.add_argument("--url",     default=DEFAULT_URL, help="API base URL")
    p.add_argument("--dry-run", action="store_true",  help="Print only, do not POST")
    p.add_argument("--only",    default=None,         help="Comma-separated: openmeteo,news,social")
    p.add_argument("--json",    dest="tweet_json", default=None, help="Path to sample_tweets.json")
    p.add_argument("--rss",     default=None,         help="RSS or HTML URL for news scraper")
    p.add_argument("--delay",   type=float, default=DEFAULT_DELAY, help="Seconds between POSTs")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(
        base_url=args.url,
        dry_run=args.dry_run,
        only=args.only.split(",") if args.only else None,
        tweet_json=args.tweet_json,
        rss_url=args.rss,
        delay=args.delay,
    )

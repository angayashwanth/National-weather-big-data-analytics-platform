"""
rate_limit.py – Per-IP rate limiting for the citizen report intake endpoint.

Uses slowapi (Starlette-compatible limiter backed by in-memory storage).
Default limit: 10 POST /api/reports per minute per IP.
Override via RATE_LIMIT_POST_REPORTS env var (e.g. "30/minute").
"""

import os
from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT_POST_REPORTS: str = os.getenv("RATE_LIMIT_POST_REPORTS", "10/minute")

limiter = Limiter(key_func=get_remote_address)

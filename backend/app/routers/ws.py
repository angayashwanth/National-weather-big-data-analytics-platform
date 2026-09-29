"""
ws.py – WebSocket broadcast hub for real-time dashboard updates.

/ws clients receive a JSON message whenever a report's verification_status
changes to "verified".  The hub is a simple in-process set of WebSocket
connections — sufficient for MVP single-server deployment.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# In-process connection registry (reset on each server restart)
_connections: Set[WebSocket] = set()
_lock = asyncio.Lock()


async def broadcast_verified(report_id: int, city: str, event_category: str) -> None:
    """
    Called by the reports router when a report becomes verified.
    Fans out a lightweight JSON notification to all connected WS clients.
    """
    payload = json.dumps(
        {
            "event": "report_verified",
            "report_id": report_id,
            "city": city,
            "event_category": event_category,
        }
    )
    dead: Set[WebSocket] = set()
    async with _lock:
        for ws in list(_connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        _connections.difference_update(dead)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Accept a persistent WebSocket connection and keep it alive."""
    await ws.accept()
    async with _lock:
        _connections.add(ws)
    logger.info("WS client connected; total=%d", len(_connections))
    try:
        while True:
            # Keep the connection alive; ignore any client messages
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with _lock:
            _connections.discard(ws)
        logger.info("WS client disconnected; total=%d", len(_connections))

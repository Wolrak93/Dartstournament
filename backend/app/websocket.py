"""WebSocket connection manager for real-time match and tournament updates."""

from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Registry of active WebSocket connections grouped by match_id or tournament_id.

    Both registries are plain dicts of sets.  Since FastAPI runs on a single
    asyncio event loop, no thread-safety primitives are needed — all coroutines
    share the same loop and never run truly concurrently.
    """

    def __init__(self) -> None:
        self._match: dict[int, set[WebSocket]] = defaultdict(set)
        self._tournament: dict[int, set[WebSocket]] = defaultdict(set)

    # ------------------------------------------------------------------
    # Match channel
    # ------------------------------------------------------------------

    async def connect_match(self, match_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._match[match_id].add(ws)
        logger.debug(
            "WS connect: match %d  (total=%d)", match_id, len(self._match[match_id])
        )

    def disconnect_match(self, match_id: int, ws: WebSocket) -> None:
        self._match[match_id].discard(ws)
        logger.debug("WS disconnect: match %d", match_id)

    async def broadcast_match(self, match_id: int, message: dict) -> None:
        """Broadcast a JSON message to every client subscribed to a match channel."""
        dead: set[WebSocket] = set()
        for ws in list(self._match.get(match_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._match[match_id].discard(ws)

    # ------------------------------------------------------------------
    # Tournament channel
    # ------------------------------------------------------------------

    async def connect_tournament(self, tournament_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._tournament[tournament_id].add(ws)
        logger.debug(
            "WS connect: tournament %d  (total=%d)",
            tournament_id,
            len(self._tournament[tournament_id]),
        )

    def disconnect_tournament(self, tournament_id: int, ws: WebSocket) -> None:
        self._tournament[tournament_id].discard(ws)
        logger.debug("WS disconnect: tournament %d", tournament_id)

    async def broadcast_tournament(self, tournament_id: int, message: dict) -> None:
        """Broadcast a JSON message to all tournament-channel subscribers."""
        dead: set[WebSocket] = set()
        for ws in list(self._tournament.get(tournament_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._tournament[tournament_id].discard(ws)


# Module-level singleton used by routers and WebSocket endpoints.
manager = ConnectionManager()

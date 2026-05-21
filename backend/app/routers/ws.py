"""WebSocket endpoints for real-time match and tournament updates.

Event protocol (all messages are JSON objects with a "type" field):

  Client → Server
  ---------------
  {"type": "ping"}                    — keepalive; server replies with pong

  Server → Client (match channel)
  --------------------------------
  {"type": "match_state",  "data": {match_id, status, round_type,
                                     player1_id, player2_id, player3_id,
                                     player4_id, starting_player_id,
                                     starting_score_p1, starting_score_p2}}
  {"type": "score_update", "data": {match_id, player_id, visit_number,
                                     total, is_bust, remaining_after,
                                     match_finished, winner_id,
                                     special_events}}
  {"type": "special_event","data": {match_id, player_id, event_type,
                                     bonus_value, count}}
  {"type": "match_finished","data": {match_id, winner_id}}

  Server → Client (tournament channel)
  -------------------------------------
  {"type": "standings_update", "data": {"tournament_id": <id>}}
  {"type": "bracket_update",   "data": {"tournament_id": <id>}}
  {"type": "pong"}
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.match_repo import get_match_by_id
from app.repositories.tournament_repo import get_tournament_by_id
from app.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


# ---------------------------------------------------------------------------
# WS /ws/match/{match_id}
# ---------------------------------------------------------------------------


@router.websocket("/ws/match/{match_id}")
async def ws_match(
    match_id: int, websocket: WebSocket, db: AsyncSession = Depends(get_db)
) -> None:
    """Subscribe to real-time updates for a single match.

    On successful connection the server immediately pushes a ``match_state``
    message with the current persisted state — this also serves as the
    reconnect snapshot so the client never has to do a separate REST call.

    The connection stays open until the client disconnects.  The REST layer
    (record_visit, start_match, finish_match, record_bull_throw) pushes
    further events via ``manager.broadcast_match``.
    """
    # Validate the match exists and build the initial snapshot.
    match = await get_match_by_id(db, match_id)
    if match is None:
        await websocket.close(code=4004)
        return
    initial_msg: dict = {
        "type": "match_state",
        "data": {
            "match_id": match_id,
            "status": match.status.value,
            "round_type": match.round_type.value,
            "player1_id": match.player1_id,
            "player2_id": match.player2_id,
            "player3_id": match.player3_id,
            "player4_id": match.player4_id,
            "starting_player_id": match.starting_player_id,
            "starting_score_p1": match.starting_score_p1,
            "starting_score_p2": match.starting_score_p2,
        },
    }

    await manager.connect_match(match_id, websocket)
    try:
        await websocket.send_json(initial_msg)
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unexpected error in ws_match handler (match_id=%d)", match_id)
    finally:
        manager.disconnect_match(match_id, websocket)


# ---------------------------------------------------------------------------
# WS /ws/tournament/{tournament_id}
# ---------------------------------------------------------------------------


@router.websocket("/ws/tournament/{tournament_id}")
async def ws_tournament(
    tournament_id: int, websocket: WebSocket, db: AsyncSession = Depends(get_db)
) -> None:
    """Subscribe to real-time tournament-level updates.

    On successful connection the server pushes a ``standings_update``
    notification so the client knows to fetch fresh standings via REST.

    Subsequent push events (``standings_update``, ``bracket_update``) are
    triggered by the REST layer after state-changing operations.
    """
    tournament = await get_tournament_by_id(db, tournament_id)
    if tournament is None:
        await websocket.close(code=4004)
        return

    await manager.connect_tournament(tournament_id, websocket)
    try:
        # Send initial notification so the client fetches current standings.
        await websocket.send_json(
            {"type": "standings_update", "data": {"tournament_id": tournament_id}}
        )
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception(
            "Unexpected error in ws_tournament handler (tournament_id=%d)",
            tournament_id,
        )
    finally:
        manager.disconnect_tournament(tournament_id, websocket)

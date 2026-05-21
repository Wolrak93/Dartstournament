"""Match flow endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import bad_request, conflict, not_found
from app.models.match import MatchStatus, RoundType
from app.repositories.match_repo import (
    get_match_by_id,
    set_starting_player,
    update_match_status,
    update_match_winner,
)
from app.repositories.visit_repo import (
    list_visits_by_match,
    list_visits_by_match_and_player,
)
from app.schemas.match import (
    BullThrowRequest,
    BullThrowResponse,
    CheckoutSuggestionResponse,
    FinishMatchRequest,
    MatchRead,
    MatchStateResponse,
    SpecialEventItem,
    VisitRequest,
    VisitResponse,
)
from app.services.events import detect_events
from app.services.match import (
    Dart,
    DartBand,
    dart_from_score,
    get_checkout_suggestion,
    persist_visit,
    process_visit,
    record_doubles_bull_throw,
    record_singles_bull_throw,
    should_switch_to_single_out,
)
from app.websocket import manager

router = APIRouter(prefix="/matches", tags=["matches"])

# Vorrunde base score for reference
_VORRUNDE_BASE_SCORE = 301


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_match_or_404(db: AsyncSession, match_id: int):
    match = await get_match_by_id(db, match_id)
    if match is None:
        raise not_found("Match", match_id)
    return match


def _build_dart(score: int, bounce: bool, robin_hood: bool) -> Dart:
    """Build a Dart object from a raw score and special flags."""
    _miss = Dart(score=0, band=DartBand.MISS, number=0)
    if bounce:
        base = dart_from_score(score) if score > 0 else _miss
        return Dart(score=base.score, band=base.band, number=base.number, bounce=True)
    if robin_hood:
        base = dart_from_score(score) if score > 0 else _miss
        return Dart(
            score=base.score, band=base.band, number=base.number, robin_hood=True
        )
    if score == 0:
        return _miss
    return dart_from_score(score)


def _compute_remaining(visits, starting_score: int) -> int:
    """Return remaining score for a player given their visits and starting score."""
    scored = sum(v.total for v in visits)
    return starting_score - scored


def _current_player_id(match, visit_counts: dict[int, int]) -> int | None:
    """Determine whose turn it is in a singles match.

    For doubles the frontend tracks the individual player; here we just return
    None to signal that it's not determinable from visit counts alone.
    """
    if match.starting_player_id is None:
        return None

    is_doubles = match.player3_id is not None

    if is_doubles:
        # Cannot determine individual player turn server-side
        # without storing full play order.
        return None

    p1 = match.player1_id
    p2 = match.player2_id
    c1 = visit_counts.get(p1, 0)
    c2 = visit_counts.get(p2, 0)
    # If starting_player is p1: p1 goes when counts are equal
    if match.starting_player_id == p1:
        return p1 if c1 == c2 else p2
    # starting_player is p2: p2 goes when counts are equal
    return p2 if c1 == c2 else p1


# ---------------------------------------------------------------------------
# GET /matches/{id}
# ---------------------------------------------------------------------------


@router.get("/{match_id}", response_model=MatchRead)
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> MatchRead:
    return await _get_match_or_404(db, match_id)


# ---------------------------------------------------------------------------
# POST /matches/{id}/bull-throw
# ---------------------------------------------------------------------------


@router.post("/{match_id}/bull-throw", response_model=BullThrowResponse)
async def record_bull_throw(
    match_id: int,
    body: BullThrowRequest,
    db: AsyncSession = Depends(get_db),
) -> BullThrowResponse:
    match = await _get_match_or_404(db, match_id)

    if match.status != MatchStatus.pending:
        raise conflict(
            f"Bull throw can only be recorded when match is 'pending', "
            f"currently '{match.status}'.",
            "invalid_match_status",
        )

    is_doubles = match.player3_id is not None

    try:
        if is_doubles:
            if body.best_player_id is None or body.best_opponent_id is None:
                raise bad_request(
                    "Doubles bull throw requires best_player_id and best_opponent_id.",
                    "missing_doubles_fields",
                )
            result = record_doubles_bull_throw(
                team1=(match.player1_id, match.player3_id),
                team2=(match.player2_id, match.player4_id),
                best_player_id=body.best_player_id,
                best_opponent_id=body.best_opponent_id,
            )
        else:
            if body.winner_id is None:
                raise bad_request(
                    "Singles bull throw requires winner_id.",
                    "missing_winner_id",
                )
            result = record_singles_bull_throw(
                player1_id=match.player1_id,
                player2_id=match.player2_id,
                winner_id=body.winner_id,
            )
    except ValueError as exc:
        raise bad_request(str(exc), "invalid_bull_throw") from exc

    starting_player_id = result.play_order[0]
    await set_starting_player(
        db, match_id=match_id, starting_player_id=starting_player_id
    )
    await db.commit()

    await manager.broadcast_match(
        match_id,
        {
            "type": "match_state",
            "data": {
                "match_id": match_id,
                "status": "bull_throw",
                "starting_player_id": starting_player_id,
                "play_order": result.play_order,
            },
        },
    )

    return BullThrowResponse(
        starting_player_id=starting_player_id,
        play_order=result.play_order,
    )


# ---------------------------------------------------------------------------
# POST /matches/{id}/start
# ---------------------------------------------------------------------------


@router.post("/{match_id}/start", response_model=dict)
async def start_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    match = await _get_match_or_404(db, match_id)

    if match.status != MatchStatus.bull_throw:
        raise conflict(
            f"Match can only be started after bull throw, currently '{match.status}'.",
            "invalid_match_status",
        )

    await update_match_status(db, match_id=match_id, status=MatchStatus.in_progress)
    await db.commit()

    await manager.broadcast_match(
        match_id,
        {
            "type": "match_state",
            "data": {"match_id": match_id, "status": "in_progress"},
        },
    )

    return {"match_id": match_id, "status": MatchStatus.in_progress}


# ---------------------------------------------------------------------------
# POST /matches/{id}/visits
# ---------------------------------------------------------------------------


@router.post("/{match_id}/visits", response_model=VisitResponse, status_code=201)
async def record_visit(
    match_id: int,
    body: VisitRequest,
    db: AsyncSession = Depends(get_db),
) -> VisitResponse:
    match = await _get_match_or_404(db, match_id)

    if match.status != MatchStatus.in_progress:
        raise conflict(
            f"Visits can only be recorded when match is 'in_progress', "
            f"currently '{match.status}'.",
            "invalid_match_status",
        )

    # Validate player is a participant
    participants = {match.player1_id, match.player2_id}
    if match.player3_id is not None:
        participants.add(match.player3_id)
    if match.player4_id is not None:
        participants.add(match.player4_id)
    if body.player_id not in participants:
        raise bad_request(
            f"Player {body.player_id} is not a participant in match {match_id}.",
            "player_not_in_match",
        )

    # Validate bounce/robin_hood flags length
    if len(body.bounce_flags) != 3 or len(body.robin_hood_flags) != 3:
        raise bad_request(
            "bounce_flags and robin_hood_flags must each have exactly 3 elements.",
            "invalid_flags_length",
        )

    # Determine visit number for this player
    existing_visits = await list_visits_by_match_and_player(
        db, match_id, body.player_id
    )
    visit_number = len(existing_visits) + 1

    # Determine which team the player is on and compute remaining
    is_doubles = match.player3_id is not None
    if is_doubles:
        team1 = {match.player1_id, match.player3_id}
    else:
        team1 = {match.player1_id}

    if body.player_id in team1:
        team_visits = await list_visits_by_match_and_player(
            db, match_id, match.player1_id
        )
        if is_doubles:
            team_visits_p3 = await list_visits_by_match_and_player(
                db, match_id, match.player3_id
            )
            team_visits = team_visits + team_visits_p3
        remaining = _compute_remaining(team_visits, match.starting_score_p1)
    else:
        team_visits = await list_visits_by_match_and_player(
            db, match_id, match.player2_id
        )
        if is_doubles:
            team_visits_p4 = await list_visits_by_match_and_player(
                db, match_id, match.player4_id
            )
            team_visits = team_visits + team_visits_p4
        remaining = _compute_remaining(team_visits, match.starting_score_p2)

    # Determine single_out_mode
    round_type_str = match.round_type.value
    if round_type_str == "lightning":
        single_out_mode = True
    else:
        single_out_mode = should_switch_to_single_out(visit_number, round_type_str)

    # Build Dart objects
    scores = [body.dart1, body.dart2, body.dart3]
    bounces = body.bounce_flags
    robins = body.robin_hood_flags
    darts = [_build_dart(scores[i], bounces[i], robins[i]) for i in range(3)]

    # Process visit
    visit_result = process_visit(
        darts=darts,
        remaining=remaining,
        visit_number=visit_number,
        single_out_mode=single_out_mode,
    )

    # Detect special events
    is_vorrunde = match.round_type == RoundType.vorrunde
    events = detect_events(
        visit_result=visit_result,
        remaining_before=remaining,
        is_vorrunde=is_vorrunde,
    )

    # Persist visit + events
    visit = await persist_visit(
        db=db,
        match_id=match_id,
        player_id=body.player_id,
        visit_number=visit_number,
        darts=darts,
        result=visit_result,
        events=events,
    )

    # Check if match is finished
    match_finished = visit_result.remaining_after == 0
    winner_id = None
    if match_finished:
        winner_id = body.player_id
        await update_match_winner(db, match_id=match_id, winner_id=winner_id)

    await db.commit()

    event_items = [
        SpecialEventItem(
            event_type=e.event_type.value,
            bonus_value=e.bonus_value,
            count=e.count,
        )
        for e in events
    ]

    # Broadcast score update to all clients watching this match.
    await manager.broadcast_match(
        match_id,
        {
            "type": "score_update",
            "data": {
                "match_id": match_id,
                "player_id": body.player_id,
                "visit_number": visit_number,
                "total": visit_result.total,
                "is_bust": visit_result.is_bust,
                "remaining_after": visit_result.remaining_after,
                "match_finished": match_finished,
                "winner_id": winner_id,
                "special_events": [
                    {
                        "event_type": e.event_type,
                        "bonus_value": e.bonus_value,
                        "count": e.count,
                    }
                    for e in event_items
                ],
            },
        },
    )

    # Broadcast each special event individually so the frontend can show popups.
    for e in event_items:
        await manager.broadcast_match(
            match_id,
            {
                "type": "special_event",
                "data": {
                    "match_id": match_id,
                    "player_id": body.player_id,
                    "event_type": e.event_type,
                    "bonus_value": e.bonus_value,
                    "count": e.count,
                },
            },
        )

    # Notify tournament channel when a match finishes (standings may have changed).
    if match_finished:
        await manager.broadcast_match(
            match_id,
            {
                "type": "match_finished",
                "data": {"match_id": match_id, "winner_id": winner_id},
            },
        )
        await manager.broadcast_tournament(
            match.tournament_id,
            {
                "type": "standings_update",
                "data": {"tournament_id": match.tournament_id},
            },
        )

    return VisitResponse(
        visit_id=visit.id,
        player_id=body.player_id,
        visit_number=visit_number,
        total=visit_result.total,
        is_bust=visit_result.is_bust,
        remaining_after=visit_result.remaining_after,
        match_finished=match_finished,
        winner_id=winner_id,
        special_events=event_items,
    )


# ---------------------------------------------------------------------------
# GET /matches/{id}/state
# ---------------------------------------------------------------------------


@router.get("/{match_id}/state", response_model=MatchStateResponse)
async def get_match_state(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> MatchStateResponse:
    match = await _get_match_or_404(db, match_id)

    all_visits = await list_visits_by_match(db, match_id)

    # Per-player visit counts
    visit_counts: dict[int, int] = {}
    for v in all_visits:
        visit_counts[v.player_id] = visit_counts.get(v.player_id, 0) + 1

    # Compute remaining per side
    visits_p1 = [v for v in all_visits if v.player_id == match.player1_id]
    visits_p2 = [v for v in all_visits if v.player_id == match.player2_id]

    if match.player3_id is not None:
        visits_p3 = [v for v in all_visits if v.player_id == match.player3_id]
        visits_p4 = [v for v in all_visits if v.player_id == match.player4_id]
        team1_visits = visits_p1 + visits_p3
        team2_visits = visits_p2 + visits_p4
    else:
        team1_visits = visits_p1
        team2_visits = visits_p2

    remaining_p1 = _compute_remaining(team1_visits, match.starting_score_p1)
    remaining_p2 = _compute_remaining(team2_visits, match.starting_score_p2)

    count_p1 = visit_counts.get(match.player1_id, 0)
    count_p2 = visit_counts.get(match.player2_id, 0)

    current_player_id = _current_player_id(match, visit_counts)

    # Determine single_out_mode for current player
    round_type_str = match.round_type.value
    if current_player_id is not None:
        current_visit_count = visit_counts.get(current_player_id, 0) + 1
        if round_type_str == "lightning":
            single_out_mode = True
        else:
            single_out_mode = should_switch_to_single_out(
                current_visit_count, round_type_str
            )
    else:
        single_out_mode = round_type_str == "lightning"

    # Checkout suggestion for current player
    checkout = None
    if current_player_id is not None and match.status == MatchStatus.in_progress:
        team1_ids = (
            {match.player1_id, match.player3_id}
            if match.player3_id
            else {match.player1_id}
        )
        if current_player_id in team1_ids:
            remaining_for_current = remaining_p1
        else:
            remaining_for_current = remaining_p2

        suggestion = get_checkout_suggestion(
            remaining=remaining_for_current,
            darts_remaining=3,
            single_out=single_out_mode,
        )
        if suggestion is not None:
            checkout = CheckoutSuggestionResponse(
                darts=suggestion.darts,
                is_finish=suggestion.is_finish,
                leave=suggestion.leave,
            )

    return MatchStateResponse(
        match_id=match_id,
        status=match.status,
        round_type=match.round_type,
        starting_player_id=match.starting_player_id,
        current_player_id=current_player_id,
        remaining_p1=remaining_p1,
        remaining_p2=remaining_p2,
        visit_count_p1=count_p1,
        visit_count_p2=count_p2,
        single_out_mode=single_out_mode,
        checkout_suggestion=checkout,
    )


# ---------------------------------------------------------------------------
# POST /matches/{id}/finish  (referee override)
# ---------------------------------------------------------------------------


@router.post("/{match_id}/finish", response_model=dict)
async def finish_match(
    match_id: int,
    body: FinishMatchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    match = await _get_match_or_404(db, match_id)

    if match.status not in (MatchStatus.in_progress, MatchStatus.bull_throw):
        raise conflict(
            f"Match cannot be finished from status '{match.status}'.",
            "invalid_match_status",
        )

    # Validate winner is a participant
    participants = {match.player1_id, match.player2_id}
    if match.player3_id is not None:
        participants.add(match.player3_id)
    if match.player4_id is not None:
        participants.add(match.player4_id)
    if body.winner_id not in participants:
        raise bad_request(
            f"winner_id {body.winner_id} is not a participant in match {match_id}.",
            "player_not_in_match",
        )

    tournament_id = match.tournament_id
    await update_match_winner(db, match_id=match_id, winner_id=body.winner_id)
    await db.commit()

    await manager.broadcast_match(
        match_id,
        {
            "type": "match_finished",
            "data": {"match_id": match_id, "winner_id": body.winner_id},
        },
    )
    await manager.broadcast_tournament(
        tournament_id,
        {"type": "standings_update", "data": {"tournament_id": tournament_id}},
    )

    return {
        "match_id": match_id,
        "winner_id": body.winner_id,
        "status": MatchStatus.finished,
    }

"""Match flow endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import bad_request, conflict, not_found
from app.models.match import MatchStatus, RoundType
from app.repositories.match_repo import (
    get_match_by_id,
    reopen_match,
    set_starting_player,
    undo_standings_after_vorrunde_match,
    update_match_status,
    update_match_winner,
    update_standings_after_vorrunde_match,
)
from app.repositories.special_event_repo import count_event_by_type_in_tournament
from app.repositories.visit_repo import (
    get_last_visit_by_match,
    list_visits_by_match,
    list_visits_by_match_and_player,
    list_visits_by_match_recent_first,
)
from app.schemas.match import (
    BullThrowRequest,
    BullThrowResponse,
    CheckoutSuggestionResponse,
    FinishMatchRequest,
    MatchRead,
    MatchStateResponse,
    SpecialEventItem,
    UndoVisitResponse,
    VisitHistoryItem,
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


_BAND_MAP: dict[str, DartBand] = {
    "single": DartBand.SINGLE,
    "double": DartBand.DOUBLE,
    "triple": DartBand.TRIPLE,
    "bull": DartBand.BULL,
    "bullseye": DartBand.BULLSEYE,
    "miss": DartBand.MISS,
}


def _build_dart(score: int, bounce: bool, robin_hood: bool, band: str = "") -> Dart:
    """Build a Dart object from a raw score, special flags, and an explicit band.

    The explicit band avoids ambiguous inference: e.g. score=36 is both D18 and T12.
    If band is empty or unrecognised, the score is inferred via dart_from_score().
    """
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

    explicit_band = _BAND_MAP.get(band)
    if explicit_band is not None:
        number = 0
        if explicit_band in (DartBand.BULL, DartBand.BULLSEYE):
            number = 25
        elif explicit_band == DartBand.SINGLE:
            number = score
        elif explicit_band == DartBand.DOUBLE:
            number = score // 2
        elif explicit_band == DartBand.TRIPLE:
            number = score // 3
        return Dart(score=score, band=explicit_band, number=number)

    return dart_from_score(score)


def _compute_remaining(visits, starting_score: int) -> int:
    """Return remaining score for a player given their visits and starting score."""
    scored = sum(v.total for v in visits)
    return starting_score - scored


def _player_avg(visits: list) -> float:
    """3-dart average: total scored across all visits / number of visits."""
    if not visits:
        return 0.0
    return sum(v.total for v in visits) / len(visits)


def _current_player_id(match, visit_counts: dict[int, int]) -> int | None:
    """Determine whose turn it is based on visit counts and starting player.

    Singles: alternates p1/p2 based on visit counts.
    Doubles: fixed rotation [sp, opp1, sp_partner, opp2] derived from visit counts.
    """
    if match.starting_player_id is None:
        return None

    is_doubles = match.player3_id is not None

    if not is_doubles:
        p1 = match.player1_id
        p2 = match.player2_id
        c1 = visit_counts.get(p1, 0)
        c2 = visit_counts.get(p2, 0)
        if match.starting_player_id == p1:
            return p1 if c1 == c2 else p2
        return p2 if c1 == c2 else p1

    # Doubles: fixed rotation [sp, opp1, sp_partner, opp2].
    # opp1 is stored in second_player_id from the bull throw result.
    sp = match.starting_player_id
    team1 = [match.player1_id, match.player3_id]
    team2 = [match.player2_id, match.player4_id]

    if sp in team1:
        sp_partner = team1[1] if team1[0] == sp else team1[0]
        opposing = team2
    else:
        sp_partner = team2[1] if team2[0] == sp else team2[0]
        opposing = team1

    if match.second_player_id is not None and match.second_player_id in opposing:
        opp1 = match.second_player_id
        opp2 = opposing[1] if opposing[0] == opp1 else opposing[0]
    else:
        # Fallback: sort by id (matches without second_player_id stored)
        opp1, opp2 = sorted(opposing)

    turn_order = [sp, opp1, sp_partner, opp2]
    total_visits = sum(visit_counts.get(pid, 0) for pid in turn_order)
    return turn_order[total_visits % 4]


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
    second_player_id = result.play_order[1] if is_doubles else None
    await set_starting_player(
        db,
        match_id=match_id,
        starting_player_id=starting_player_id,
        second_player_id=second_player_id,
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

    # Determine single_out_mode using the TEAM's combined visit count.
    # team_visits already holds all visits for this player's team (computed above).
    # The current visit will be the (len(team_visits) + 1)-th team visit.
    round_type_str = match.round_type.value
    if round_type_str == "lightning":
        single_out_mode = True
    else:
        team_visit_number = len(team_visits) + 1
        single_out_mode = should_switch_to_single_out(team_visit_number, round_type_str)

    # Build Dart objects
    scores = [body.dart1, body.dart2, body.dart3]
    bounces = body.bounce_flags
    robins = body.robin_hood_flags
    bands = body.dart_bands if len(body.dart_bands) == 3 else ["", "", ""]
    darts = [_build_dart(scores[i], bounces[i], robins[i], bands[i]) for i in range(3)]

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
        if match.round_type == RoundType.vorrunde:
            await update_standings_after_vorrunde_match(db, match, winner_id)

    await db.commit()

    # Query cumulative tournament count for each detected event type.
    tournament_counts: dict[str, int] = {}
    for e in events:
        key = e.event_type.value
        if key not in tournament_counts:
            tournament_counts[key] = await count_event_by_type_in_tournament(
                db, match.tournament_id, e.event_type
            )

    event_items = [
        SpecialEventItem(
            event_type=e.event_type.value,
            bonus_value=e.bonus_value,
            count=e.count,
            tournament_count=tournament_counts[e.event_type.value],
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
                    "tournament_count": e.tournament_count,
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

    # Per-player averages and doubles-only counts
    avg_p1 = _player_avg(visits_p1)
    avg_p2 = _player_avg(visits_p2)
    if match.player3_id is not None:
        count_p3: int | None = visit_counts.get(match.player3_id, 0)
        count_p4: int | None = visit_counts.get(match.player4_id, 0) if match.player4_id else 0
        avg_p3: float | None = _player_avg(visits_p3)
        avg_p4: float | None = _player_avg(visits_p4)
    else:
        count_p3 = None
        count_p4 = None
        avg_p3 = None
        avg_p4 = None

    # Most recent visit score (for display purposes)
    last_visit_total: int | None = all_visits[-1].total if all_visits else None

    current_player_id = _current_player_id(match, visit_counts)

    # Determine single_out_mode using the TEAM's combined visit count.
    round_type_str = match.round_type.value
    if current_player_id is not None:
        is_doubles_state = match.player3_id is not None
        if is_doubles_state:
            if current_player_id in {match.player1_id, match.player3_id}:
                team_done = visit_counts.get(match.player1_id, 0) + visit_counts.get(
                    match.player3_id, 0
                )
            else:
                team_done = visit_counts.get(match.player2_id, 0) + visit_counts.get(
                    match.player4_id or 0, 0
                )
        else:
            team_done = visit_counts.get(current_player_id, 0)
        if round_type_str == "lightning":
            single_out_mode = True
        else:
            single_out_mode = should_switch_to_single_out(team_done + 1, round_type_str)
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
                text=suggestion.text,
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
        visit_count_p3=count_p3,
        visit_count_p4=count_p4,
        avg_p1=avg_p1,
        avg_p2=avg_p2,
        avg_p3=avg_p3,
        avg_p4=avg_p4,
        last_visit_total=last_visit_total,
        single_out_mode=single_out_mode,
        checkout_suggestion=checkout,
    )


# ---------------------------------------------------------------------------
# GET /matches/{id}/visits  (visit history)
# ---------------------------------------------------------------------------


@router.get("/{match_id}/visits", response_model=list[VisitHistoryItem])
async def get_match_visits(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[VisitHistoryItem]:
    await _get_match_or_404(db, match_id)
    visits = await list_visits_by_match_recent_first(db, match_id)
    return [
        VisitHistoryItem(
            visit_id=v.id,
            player_id=v.player_id,
            visit_number=v.visit_number,
            dart1=v.dart1,
            dart2=v.dart2,
            dart3=v.dart3,
            total=v.total,
            is_bust=v.is_bust,
        )
        for v in visits
    ]


# ---------------------------------------------------------------------------
# DELETE /matches/{id}/visits/last  (undo last visit)
# ---------------------------------------------------------------------------


@router.delete("/{match_id}/visits/last", response_model=UndoVisitResponse)
async def undo_last_visit(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> UndoVisitResponse:
    match = await _get_match_or_404(db, match_id)

    if match.status not in (MatchStatus.in_progress, MatchStatus.finished):
        raise conflict(
            f"Cannot undo visits when match status is '{match.status}'.",
            "invalid_match_status",
        )

    last_visit = await get_last_visit_by_match(db, match_id)
    if last_visit is None:
        raise bad_request("No visits to undo for this match.", "no_visits")

    visit_id = last_visit.id
    former_winner_id = match.winner_id
    was_finished = match.status == MatchStatus.finished

    # Delete special events linked to this visit
    from sqlalchemy import delete as sql_delete

    from app.models.special_event import SpecialEvent

    await db.execute(sql_delete(SpecialEvent).where(SpecialEvent.visit_id == visit_id))

    # Delete the visit itself
    await db.delete(last_visit)
    await db.flush()

    # If match was finished: undo standings (Vorrunde only) and reopen
    if was_finished:
        if match.round_type == RoundType.vorrunde and former_winner_id is not None:
            await undo_standings_after_vorrunde_match(db, match, former_winner_id)
        await reopen_match(db, match_id)

    await db.commit()

    await manager.broadcast_match(
        match_id,
        {"type": "visit_undone", "data": {"match_id": match_id, "undone_visit_id": visit_id}},
    )

    if was_finished:
        await manager.broadcast_match(
            match_id,
            {"type": "match_state", "data": {"match_id": match_id, "status": "in_progress"}},
        )
        if match.round_type == RoundType.vorrunde:
            await manager.broadcast_tournament(
                match.tournament_id,
                {"type": "standings_update", "data": {"tournament_id": match.tournament_id}},
            )

    return UndoVisitResponse(undone_visit_id=visit_id, match_id=match_id)


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

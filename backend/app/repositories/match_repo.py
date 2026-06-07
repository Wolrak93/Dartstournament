"""Repository for Match CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match, MatchStatus, RoundType


async def create_match(
    db: AsyncSession,
    tournament_id: int,
    round_type: RoundType,
    round_number: int,
    player1_id: int,
    player2_id: int,
    starting_score_p1: int,
    starting_score_p2: int,
    player3_id: int | None = None,
    player4_id: int | None = None,
) -> Match:
    match = Match(
        tournament_id=tournament_id,
        round_type=round_type,
        round_number=round_number,
        player1_id=player1_id,
        player2_id=player2_id,
        starting_score_p1=starting_score_p1,
        starting_score_p2=starting_score_p2,
        player3_id=player3_id,
        player4_id=player4_id,
        status=MatchStatus.pending,
    )
    db.add(match)
    await db.flush()
    return match


async def get_match_by_id(
    db: AsyncSession, match_id: int
) -> Match | None:
    result = await db.execute(select(Match).where(Match.id == match_id))
    return result.scalar_one_or_none()


async def list_matches_by_tournament(
    db: AsyncSession, tournament_id: int
) -> list[Match]:
    result = await db.execute(
        select(Match)
        .where(Match.tournament_id == tournament_id)
        .order_by(Match.round_number, Match.id)
    )
    return list(result.scalars().all())


async def update_match_status(
    db: AsyncSession, match_id: int, status: MatchStatus
) -> Match:
    match = await get_match_by_id(db, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")
    match.status = status
    await db.flush()
    return match


async def update_match_winner(
    db: AsyncSession, match_id: int, winner_id: int
) -> Match:
    match = await get_match_by_id(db, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")
    match.winner_id = winner_id
    match.status = MatchStatus.finished
    await db.flush()
    return match


async def update_standings_after_vorrunde_match(
    db: AsyncSession,
    match: Match,
    winner_id: int,
) -> None:
    """Update reg_points, avg_score, and bonus_points for all players after a Vorrunde match."""
    from app.repositories.special_event_repo import sum_bonus_by_player_and_tournament
    from app.repositories.tournament_player_repo import (
        get_tournament_player,
        update_tournament_player_standing,
    )
    from app.repositories.visit_repo import list_visits_by_tournament_and_player

    team1_ids = [pid for pid in [match.player1_id, match.player3_id] if pid is not None]
    team2_ids = [pid for pid in [match.player2_id, match.player4_id] if pid is not None]
    winner_team = team1_ids if winner_id in team1_ids else team2_ids

    for player_id in team1_ids + team2_ids:
        visits = await list_visits_by_tournament_and_player(
            db, match.tournament_id, player_id
        )
        avg = sum(v.total for v in visits) / len(visits) if visits else 0.0

        tp = await get_tournament_player(db, match.tournament_id, player_id)
        if tp is None:
            continue

        new_reg = tp.reg_points + (1.0 if player_id in winner_team else 0.0)
        new_bonus = await sum_bonus_by_player_and_tournament(
            db, match.tournament_id, player_id
        )
        await update_tournament_player_standing(
            db,
            tournament_id=match.tournament_id,
            player_id=player_id,
            reg_points=new_reg,
            avg_score=avg,
            bonus_points=new_bonus,
        )


async def reopen_match(
    db: AsyncSession,
    match_id: int,
) -> Match:
    """Revert a finished match back to in_progress (e.g. after an undo)."""
    match = await get_match_by_id(db, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")
    match.status = MatchStatus.in_progress
    match.winner_id = None
    await db.flush()
    return match


async def undo_standings_after_vorrunde_match(
    db: AsyncSession,
    match: Match,
    former_winner_id: int,
) -> None:
    """Reverse the standings update for a Vorrunde match when its last visit is undone.

    The visit must already be deleted from the DB before calling this so that
    the avg recalculation reflects the correct remaining visits.
    """
    from app.repositories.special_event_repo import sum_bonus_by_player_and_tournament
    from app.repositories.tournament_player_repo import (
        get_tournament_player,
        update_tournament_player_standing,
    )
    from app.repositories.visit_repo import list_visits_by_tournament_and_player

    team1_ids = [pid for pid in [match.player1_id, match.player3_id] if pid is not None]
    team2_ids = [pid for pid in [match.player2_id, match.player4_id] if pid is not None]
    winner_team = team1_ids if former_winner_id in team1_ids else team2_ids

    for player_id in team1_ids + team2_ids:
        visits = await list_visits_by_tournament_and_player(
            db, match.tournament_id, player_id
        )
        avg = sum(v.total for v in visits) / len(visits) if visits else 0.0

        tp = await get_tournament_player(db, match.tournament_id, player_id)
        if tp is None:
            continue

        new_reg = tp.reg_points - (1.0 if player_id in winner_team else 0.0)
        new_bonus = await sum_bonus_by_player_and_tournament(
            db, match.tournament_id, player_id
        )
        await update_tournament_player_standing(
            db,
            tournament_id=match.tournament_id,
            player_id=player_id,
            reg_points=max(0.0, new_reg),
            avg_score=avg,
            bonus_points=new_bonus,
        )


async def set_starting_player(
    db: AsyncSession,
    match_id: int,
    starting_player_id: int,
    second_player_id: int | None = None,
) -> Match:
    match = await get_match_by_id(db, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")
    match.starting_player_id = starting_player_id
    match.second_player_id = second_player_id
    match.status = MatchStatus.bull_throw
    await db.flush()
    return match

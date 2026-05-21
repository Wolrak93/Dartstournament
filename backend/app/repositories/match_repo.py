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


async def set_starting_player(
    db: AsyncSession, match_id: int, starting_player_id: int
) -> Match:
    match = await get_match_by_id(db, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")
    match.starting_player_id = starting_player_id
    match.status = MatchStatus.bull_throw
    await db.flush()
    return match

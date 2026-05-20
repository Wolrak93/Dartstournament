"""Repository for TournamentPlayer join-table operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tournament import TournamentPlayer


async def add_player_to_tournament(
    db: AsyncSession,
    tournament_id: int,
    player_id: int,
) -> TournamentPlayer:
    tp = TournamentPlayer(
        tournament_id=tournament_id,
        player_id=player_id,
        reg_points=0.0,
        bonus_points=0,
        avg_score=0.0,
    )
    db.add(tp)
    await db.flush()
    return tp


async def get_tournament_player(
    db: AsyncSession,
    tournament_id: int,
    player_id: int,
) -> TournamentPlayer | None:
    result = await db.execute(
        select(TournamentPlayer).where(
            TournamentPlayer.tournament_id == tournament_id,
            TournamentPlayer.player_id == player_id,
        )
    )
    return result.scalar_one_or_none()


async def update_tournament_player_standing(
    db: AsyncSession,
    tournament_id: int,
    player_id: int,
    reg_points: float | None = None,
    bonus_points: int | None = None,
    avg_score: float | None = None,
) -> TournamentPlayer:
    tp = await get_tournament_player(db, tournament_id, player_id)
    if tp is None:
        raise ValueError(
            f"TournamentPlayer ({tournament_id}, {player_id}) not found"
        )
    if reg_points is not None:
        tp.reg_points = reg_points
    if bonus_points is not None:
        tp.bonus_points = bonus_points
    if avg_score is not None:
        tp.avg_score = avg_score
    await db.flush()
    return tp


async def list_tournament_players(
    db: AsyncSession,
    tournament_id: int,
) -> list[TournamentPlayer]:
    result = await db.execute(
        select(TournamentPlayer).where(
            TournamentPlayer.tournament_id == tournament_id
        )
    )
    return list(result.scalars().all())

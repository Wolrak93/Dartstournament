"""Repository for Tournament CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tournament import Tournament, TournamentMode, TournamentStatus


async def create_tournament(
    db: AsyncSession,
    player_count: int,
    mode: TournamentMode = TournamentMode.swiss,
) -> Tournament:
    tournament = Tournament(
        player_count=player_count,
        mode=mode,
        status=TournamentStatus.pending,
    )
    db.add(tournament)
    await db.flush()
    return tournament


async def get_tournament_by_id(
    db: AsyncSession,
    tournament_id: int,
    with_players: bool = False,
) -> Tournament | None:
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    if with_players:
        stmt = stmt.options(selectinload(Tournament.players))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_tournament_status(
    db: AsyncSession,
    tournament_id: int,
    status: TournamentStatus,
) -> Tournament:
    tournament = await get_tournament_by_id(db, tournament_id)
    if tournament is None:
        raise ValueError(f"Tournament {tournament_id} not found")
    tournament.status = status
    await db.flush()
    return tournament

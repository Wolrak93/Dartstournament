"""Repository for Tournament CRUD operations."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.match import Match, Visit
from app.models.special_event import SpecialEvent
from app.models.tournament import (
    Tournament,
    TournamentMode,
    TournamentPlayer,
    TournamentStatus,
)


async def create_tournament(
    db: AsyncSession,
    player_count: int,
    mode: TournamentMode = TournamentMode.swiss,
    name: str | None = None,
) -> Tournament:
    tournament = Tournament(
        player_count=player_count,
        mode=mode,
        status=TournamentStatus.pending,
        name=name,
    )
    db.add(tournament)
    await db.flush()
    return tournament


async def list_all_tournaments(db: AsyncSession) -> list[Tournament]:
    stmt = select(Tournament).order_by(Tournament.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


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


async def delete_tournament(db: AsyncSession, tournament_id: int) -> None:
    """Delete a tournament and all its related data (cascade via SQL DELETE)."""
    # Collect match IDs for this tournament
    match_ids_result = await db.execute(
        select(Match.id).where(Match.tournament_id == tournament_id)
    )
    match_ids = list(match_ids_result.scalars().all())

    if match_ids:
        # Collect visit IDs for cascading into special_events
        visit_ids_result = await db.execute(
            select(Visit.id).where(Visit.match_id.in_(match_ids))
        )
        visit_ids = list(visit_ids_result.scalars().all())

        if visit_ids:
            await db.execute(
                delete(SpecialEvent).where(SpecialEvent.visit_id.in_(visit_ids))
            )
        await db.execute(delete(Visit).where(Visit.match_id.in_(match_ids)))
        await db.execute(delete(Match).where(Match.tournament_id == tournament_id))

    await db.execute(
        delete(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament_id)
    )
    await db.execute(delete(Tournament).where(Tournament.id == tournament_id))
    await db.flush()

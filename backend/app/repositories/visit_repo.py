"""Repository for Visit CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Visit


async def create_visit(
    db: AsyncSession,
    match_id: int,
    player_id: int,
    visit_number: int,
    dart1: int,
    dart2: int,
    dart3: int,
    total: int,
    is_bust: bool,
) -> Visit:
    visit = Visit(
        match_id=match_id,
        player_id=player_id,
        visit_number=visit_number,
        dart1=dart1,
        dart2=dart2,
        dart3=dart3,
        total=total,
        is_bust=is_bust,
    )
    db.add(visit)
    await db.flush()
    return visit


async def list_visits_by_match_and_player(
    db: AsyncSession,
    match_id: int,
    player_id: int,
) -> list[Visit]:
    result = await db.execute(
        select(Visit)
        .where(Visit.match_id == match_id, Visit.player_id == player_id)
        .order_by(Visit.visit_number)
    )
    return list(result.scalars().all())


async def list_visits_by_match(
    db: AsyncSession,
    match_id: int,
) -> list[Visit]:
    result = await db.execute(
        select(Visit)
        .where(Visit.match_id == match_id)
        .order_by(Visit.visit_number, Visit.id)
    )
    return list(result.scalars().all())


async def get_last_visit_by_match(
    db: AsyncSession,
    match_id: int,
) -> Visit | None:
    """Return the most recently recorded visit in a match (highest id)."""
    result = await db.execute(
        select(Visit)
        .where(Visit.match_id == match_id)
        .order_by(Visit.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_visits_by_match_recent_first(
    db: AsyncSession,
    match_id: int,
) -> list[Visit]:
    """Return all visits for a match ordered most recent first."""
    result = await db.execute(
        select(Visit)
        .where(Visit.match_id == match_id)
        .order_by(Visit.id.desc())
    )
    return list(result.scalars().all())


async def list_visits_by_tournament_and_player(
    db: AsyncSession,
    tournament_id: int,
    player_id: int,
) -> list[Visit]:
    """Return all non-bust visits for a player across an entire tournament."""
    from app.models.match import Match  # local import to avoid circular dependency

    result = await db.execute(
        select(Visit)
        .join(Match, Visit.match_id == Match.id)
        .where(
            Match.tournament_id == tournament_id,
            Visit.player_id == player_id,
            Visit.is_bust == False,  # noqa: E712
        )
        .order_by(Visit.id)
    )
    return list(result.scalars().all())

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

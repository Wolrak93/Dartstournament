"""Repository for SpecialEvent CRUD operations."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match, RoundType, Visit
from app.models.special_event import EventType, SpecialEvent


async def create_special_event(
    db: AsyncSession,
    visit_id: int,
    player_id: int,
    event_type: EventType,
    bonus_value: int,
    count: int = 1,
) -> SpecialEvent:
    event = SpecialEvent(
        visit_id=visit_id,
        player_id=player_id,
        event_type=event_type,
        bonus_value=bonus_value,
        count=count,
    )
    db.add(event)
    await db.flush()
    return event


async def sum_bonus_by_player_and_tournament(
    db: AsyncSession,
    tournament_id: int,
    player_id: int,
) -> int:
    """Sum total bonus (bonus_value * count) for a player across all Vorrunde visits.

    Only Vorrunde matches are counted; KO/Lightning events have bonus_value=0
    but we filter by round_type=vorrunde for explicitness.
    """
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(SpecialEvent.bonus_value * SpecialEvent.count), 0
            )
        )
        .join(Visit, SpecialEvent.visit_id == Visit.id)
        .join(Match, Visit.match_id == Match.id)
        .where(
            Match.tournament_id == tournament_id,
            Match.round_type == RoundType.vorrunde,
            SpecialEvent.player_id == player_id,
        )
    )
    return int(result.scalar_one())


async def count_event_by_type_in_tournament(
    db: AsyncSession,
    tournament_id: int,
    event_type: EventType,
) -> int:
    """Return the total occurrence count of event_type across all matches in tournament.

    Sums the ``count`` column so that events that fire multiple times per visit
    (e.g. Tripel, Bull) are counted correctly.
    """
    result = await db.execute(
        select(func.coalesce(func.sum(SpecialEvent.count), 0))
        .join(Visit, SpecialEvent.visit_id == Visit.id)
        .join(Match, Visit.match_id == Match.id)
        .where(
            Match.tournament_id == tournament_id,
            SpecialEvent.event_type == event_type,
        )
    )
    return int(result.scalar_one())


async def list_events_by_visit(
    db: AsyncSession,
    visit_id: int,
) -> list[SpecialEvent]:
    result = await db.execute(
        select(SpecialEvent).where(SpecialEvent.visit_id == visit_id)
    )
    return list(result.scalars().all())

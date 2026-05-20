"""Repository for Player CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player


async def create_player(
    db: AsyncSession,
    name: str,
    photo_path: str | None = None,
    music_path: str | None = None,
    championship_count: int = 0,
) -> Player:
    player = Player(
        name=name,
        photo_path=photo_path,
        music_path=music_path,
        championship_count=championship_count,
    )
    db.add(player)
    await db.flush()
    return player


async def get_player_by_id(db: AsyncSession, player_id: int) -> Player | None:
    result = await db.execute(select(Player).where(Player.id == player_id))
    return result.scalar_one_or_none()


async def list_all_players(db: AsyncSession) -> list[Player]:
    result = await db.execute(select(Player).order_by(Player.name))
    return list(result.scalars().all())


async def update_championship_count(
    db: AsyncSession, player_id: int, count: int
) -> Player:
    player = await get_player_by_id(db, player_id)
    if player is None:
        raise ValueError(f"Player {player_id} not found")
    player.championship_count = count
    await db.flush()
    return player

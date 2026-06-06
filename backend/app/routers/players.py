"""Player endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import not_found
from app.repositories.player_repo import (
    create_player,
    get_player_by_id,
    list_all_players,
)
from app.schemas.player import PlayerCreate, PlayerRead

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=list[PlayerRead])
async def list_players(db: AsyncSession = Depends(get_db)) -> list[PlayerRead]:
    players = await list_all_players(db)
    return [PlayerRead.model_validate(p) for p in players]


@router.post("", response_model=PlayerRead, status_code=201)
async def create_new_player(
    body: PlayerCreate,
    db: AsyncSession = Depends(get_db),
) -> PlayerRead:
    player = await create_player(
        db,
        name=body.name,
        photo_path=body.photo_path,
        music_path=body.music_path,
        championship_count=body.championship_count,
    )
    await db.commit()
    await db.refresh(player)
    return PlayerRead.model_validate(player)


@router.get("/{player_id}", response_model=PlayerRead)
async def get_player(
    player_id: int,
    db: AsyncSession = Depends(get_db),
) -> PlayerRead:
    player = await get_player_by_id(db, player_id)
    if player is None:
        raise not_found("Player", player_id)
    return PlayerRead.model_validate(player)

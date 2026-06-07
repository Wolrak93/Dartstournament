from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_mobile_token, verify_mobile_token
from app.database import get_db
from app.models.player import Player
from app.schemas.mobile import MobileLoginRequest, MobileLoginResponse

router = APIRouter(prefix="/mobile", tags=["mobile"])
_bearer = HTTPBearer()


async def _get_current_player(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Player:
    payload = verify_mobile_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        player_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")
    player = await db.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=401, detail="Player not found")
    return player


@router.post("/auth/login", response_model=MobileLoginResponse)
async def mobile_login(body: MobileLoginRequest, db: AsyncSession = Depends(get_db)):
    player = await db.get(Player, body.player_id)
    # 4-digit tournament PIN, plaintext acceptable for this use case
    if player is None or player.pin != body.pin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_mobile_token(player_id=player.id, name=player.name)
    return MobileLoginResponse(token=token, player_id=player.id, name=player.name)

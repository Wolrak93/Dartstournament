from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_mobile_token, verify_mobile_token
from app.database import get_db
from app.models.match import Match, MatchStatus, RoundType
from app.models.player import Player
from app.models.special_event import SpecialEvent
from app.models.tournament import Tournament, TournamentPlayer, TournamentStatus
from app.schemas.mobile import (
    MobileBracketMatch,
    MobileBracketResponse,
    MobileBracketRound,
    MobileCompletedMatch,
    MobileLiveMatch,
    MobileLoginRequest,
    MobileLoginResponse,
    MobileMatchesResponse,
    MobileNebenrundeMatch,
    MobilePlayerStats,
    MobileProfileResponse,
    MobileStandingEntry,
    MobileStandingsResponse,
    MobileStatsResponse,
    MobileUpcomingMatch,
)

router = APIRouter(prefix="/mobile", tags=["mobile"])
_bearer = HTTPBearer()


async def _get_active_tournament(db: AsyncSession) -> Tournament | None:
    result = await db.execute(
        select(Tournament)
        .where(Tournament.status.in_([TournamentStatus.vorrunde, TournamentStatus.ko]))
        .order_by(Tournament.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_current_player(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Player:
    payload = verify_mobile_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    player = await db.get(Player, int(payload["sub"]))
    if player is None:
        raise HTTPException(status_code=401, detail="Player not found")
    return player


@router.post("/auth/login", response_model=MobileLoginResponse)
async def mobile_login(body: MobileLoginRequest, db: AsyncSession = Depends(get_db)):
    player = await db.get(Player, body.player_id)
    if player is None or player.pin != body.pin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_mobile_token(player_id=player.id, name=player.name)
    return MobileLoginResponse(token=token, player_id=player.id, name=player.name)

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.tournament import TournamentMode, TournamentStatus


class TournamentCreate(BaseModel):
    player_count: int = Field(..., ge=9, le=13)
    mode: TournamentMode = TournamentMode.swiss


class TournamentUpdate(BaseModel):
    status: TournamentStatus | None = None
    mode: TournamentMode | None = None


class TournamentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    player_count: int
    mode: TournamentMode
    status: TournamentStatus


class TournamentPlayerUpdate(BaseModel):
    reg_points: float | None = None
    bonus_points: int | None = None
    avg_score: float | None = None


class TournamentPlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tournament_id: int
    player_id: int
    reg_points: float
    bonus_points: int
    avg_score: float

from pydantic import BaseModel, ConfigDict, Field

from app.models.match import MatchStatus, RoundType


class MatchCreate(BaseModel):
    tournament_id: int
    round_type: RoundType
    round_number: int = Field(..., ge=1)
    player1_id: int
    player2_id: int
    player3_id: int | None = None
    player4_id: int | None = None
    starting_score_p1: int = Field(default=301, ge=1)
    starting_score_p2: int = Field(default=301, ge=1)


class MatchUpdate(BaseModel):
    winner_id: int | None = None
    status: MatchStatus | None = None


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    round_type: RoundType
    round_number: int
    player1_id: int
    player2_id: int
    player3_id: int | None
    player4_id: int | None
    starting_score_p1: int
    starting_score_p2: int
    winner_id: int | None
    status: MatchStatus


class VisitCreate(BaseModel):
    match_id: int
    player_id: int
    visit_number: int = Field(..., ge=1)
    dart1: int = Field(..., ge=0, le=60)
    dart2: int = Field(..., ge=0, le=60)
    dart3: int = Field(..., ge=0, le=60)
    total: int = Field(..., ge=0, le=180)
    is_bust: bool = False


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    player_id: int
    visit_number: int
    dart1: int
    dart2: int
    dart3: int
    total: int
    is_bust: bool

from __future__ import annotations

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
    starting_player_id: int | None
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


# ---------------------------------------------------------------------------
# API-level request / response schemas
# ---------------------------------------------------------------------------


class BullThrowRequest(BaseModel):
    """Bull throw result.

    Singles: set winner_id to the player who threw closer to the bull.
    Doubles: set best_player_id (overall best) and best_opponent_id
    (best from the opposing team).
    """

    winner_id: int | None = None
    best_player_id: int | None = None
    best_opponent_id: int | None = None


class BullThrowResponse(BaseModel):
    starting_player_id: int
    play_order: list[int]


class VisitRequest(BaseModel):
    """Visit (3 darts) submitted by the referee.

    player_id: the player who threw this visit.
    dart1–dart3: raw score per dart (0–60; 25 = bull; 50 = bullseye).
    bounce_flags: True if that dart bounced out (scores 0).
    robin_hood_flags: True if that dart stuck in another dart (scores 0).
    """

    player_id: int
    dart1: int = Field(..., ge=0, le=60)
    dart2: int = Field(..., ge=0, le=60)
    dart3: int = Field(..., ge=0, le=60)
    bounce_flags: list[bool] = Field(default_factory=lambda: [False, False, False])
    robin_hood_flags: list[bool] = Field(default_factory=lambda: [False, False, False])


class SpecialEventItem(BaseModel):
    event_type: str
    bonus_value: int
    count: int


class VisitResponse(BaseModel):
    visit_id: int
    player_id: int
    visit_number: int
    total: int
    is_bust: bool
    remaining_after: int
    match_finished: bool
    winner_id: int | None
    special_events: list[SpecialEventItem]


class CheckoutSuggestionResponse(BaseModel):
    darts: list[str]
    is_finish: bool
    leave: int


class MatchStateResponse(BaseModel):
    match_id: int
    status: MatchStatus
    round_type: RoundType
    starting_player_id: int | None
    current_player_id: int | None
    remaining_p1: int
    remaining_p2: int
    visit_count_p1: int
    visit_count_p2: int
    single_out_mode: bool
    checkout_suggestion: CheckoutSuggestionResponse | None


class FinishMatchRequest(BaseModel):
    winner_id: int

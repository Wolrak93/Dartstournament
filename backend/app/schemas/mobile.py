from __future__ import annotations

from pydantic import BaseModel, Field

# --- Auth ---

class MobileLoginRequest(BaseModel):
    player_id: int
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")


class MobileLoginResponse(BaseModel):
    token: str
    player_id: int
    name: str


# --- Matches ---

class MobileLiveMatch(BaseModel):
    match_id: int
    round_type: str
    player1_id: int
    player1_name: str
    player2_id: int
    player2_name: str


class MobileUpcomingMatch(BaseModel):
    match_id: int
    round_type: str
    player1_name: str
    player2_name: str


class MobileCompletedMatch(BaseModel):
    match_id: int
    round_type: str
    player1_name: str
    player2_name: str
    winner_name: str


class MobileMatchesResponse(BaseModel):
    tournament_id: int | None
    live: list[MobileLiveMatch]
    upcoming: list[MobileUpcomingMatch]
    completed: list[MobileCompletedMatch]


# --- Standings ---

class MobileStandingEntry(BaseModel):
    rank: int
    player_id: int
    name: str
    wins: int
    losses: int
    avg_score: float
    reg_points: float
    bonus_points: int
    ko_qualified: bool


class MobileStandingsResponse(BaseModel):
    tournament_id: int | None
    phase: str
    entries: list[MobileStandingEntry]


# --- Bracket ---

class MobileBracketMatch(BaseModel):
    match_id: int | None
    player1_name: str | None
    player2_name: str | None
    winner_name: str | None
    is_completed: bool


class MobileBracketRound(BaseModel):
    label: str
    matches: list[MobileBracketMatch]


class MobileNebenrundeMatch(BaseModel):
    match_id: int
    round_number: int
    player1_name: str
    player2_name: str
    winner_name: str | None
    is_completed: bool


class MobileBracketResponse(BaseModel):
    tournament_id: int | None
    ko_rounds: list[MobileBracketRound]
    nebenrunde: list[MobileNebenrundeMatch]


# --- Stats ---

class MobilePlayerStats(BaseModel):
    player_id: int
    name: str
    avg_score: float
    wins: int
    losses: int
    bonus_points: int
    event_counts: dict[str, int]


class MobileStatsResponse(BaseModel):
    tournament_id: int | None
    players: list[MobilePlayerStats]
    totals: dict[str, int]


# --- Profile ---

class MobileProfileResponse(BaseModel):
    player_id: int
    name: str
    photo_url: str | None
    rank: int | None
    reg_points: float
    bonus_points: int
    wins: int
    losses: int
    avg_score: float

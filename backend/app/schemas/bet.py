from pydantic import BaseModel, ConfigDict, Field


class BettingAccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    player_id: int | None = None
    balance: float = Field(default=1000.0, ge=0)


class BettingAccountUpdate(BaseModel):
    balance: float | None = Field(default=None, ge=0)


class BettingAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    player_id: int | None
    name: str
    balance: float


class BetCreate(BaseModel):
    match_id: int
    account_id: int
    amount: float = Field(..., gt=0)
    picked_player_id: int


class BetUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    picked_player_id: int | None = None
    payout: float | None = Field(default=None, ge=0)


class BetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    account_id: int
    amount: float
    picked_player_id: int
    payout: float | None

from pydantic import BaseModel, ConfigDict, Field

from app.models.special_event import EventType


class SpecialEventCreate(BaseModel):
    visit_id: int
    player_id: int
    event_type: EventType
    bonus_value: int = 0
    count: int = Field(default=1, ge=1)


class SpecialEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    player_id: int
    event_type: EventType
    bonus_value: int
    count: int

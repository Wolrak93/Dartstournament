from pydantic import BaseModel, ConfigDict, Field


class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    photo_path: str | None = None
    music_path: str | None = None
    championship_count: int = Field(default=0, ge=0)


class PlayerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    photo_path: str | None = None
    music_path: str | None = None
    championship_count: int | None = Field(default=None, ge=0)


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    photo_path: str | None
    music_path: str | None
    championship_count: int

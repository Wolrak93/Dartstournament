from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Single source of truth: EventType lives in the service layer.
# The model re-exports it so that schema and test imports via
# `app.models.special_event` continue to work without changes.
from app.services.events import EventType as EventType  # noqa: F401


class SpecialEvent(Base):
    __tablename__ = "special_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("visits.id"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType), nullable=False
    )
    # bonus_value is 0 for KO/Lightning matches (events tracked but no points)
    bonus_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # For events that can trigger multiple times per visit (e.g. Tripel, Bull)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    visit: Mapped["Visit"] = relationship(back_populates="special_events")  # noqa: F821

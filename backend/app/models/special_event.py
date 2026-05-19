import enum

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventType(enum.StrEnum):
    score_26 = "score_26"
    score_180 = "score_180"
    rest_170 = "rest_170"
    kack_rest = "kack_rest"
    bogey = "bogey"
    tripel = "tripel"
    tripel_20 = "tripel_20"
    bull = "bull"
    bulls_eye = "bulls_eye"
    bounce = "bounce"
    robin_hood = "robin_hood"
    be_finish = "be_finish"
    odd_finish = "odd_finish"
    double_double = "double_double"
    mad_house = "mad_house"
    shanghai = "shanghai"
    bust = "bust"
    doppel_treffer = "doppel_treffer"
    gleiche_zahl = "gleiche_zahl"


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

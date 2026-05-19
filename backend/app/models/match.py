import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoundType(enum.StrEnum):
    vorrunde = "vorrunde"
    ko = "ko"
    lightning = "lightning"


class MatchStatus(enum.StrEnum):
    pending = "pending"
    bull_throw = "bull_throw"
    in_progress = "in_progress"
    finished = "finished"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=False
    )
    round_type: Mapped[RoundType] = mapped_column(Enum(RoundType), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Singles: player1_id vs player2_id
    # Doubles: player1_id + player3_id vs player2_id + player4_id
    player1_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    player2_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    player3_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    player4_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )

    # Handicap-adjusted starting scores (default 301 or 501)
    starting_score_p1: Mapped[int] = mapped_column(Integer, nullable=False)
    starting_score_p2: Mapped[int] = mapped_column(Integer, nullable=False)

    winner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), nullable=False, default=MatchStatus.pending
    )

    # Relationships
    tournament: Mapped["Tournament"] = relationship(  # noqa: F821
        back_populates="matches"
    )
    visits: Mapped[list["Visit"]] = relationship(back_populates="match")


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    visit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    dart1: Mapped[int] = mapped_column(Integer, nullable=False)
    dart2: Mapped[int] = mapped_column(Integer, nullable=False)
    dart3: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    is_bust: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    match: Mapped["Match"] = relationship(back_populates="visits")
    special_events: Mapped[list["SpecialEvent"]] = relationship(  # noqa: F821
        back_populates="visit"
    )

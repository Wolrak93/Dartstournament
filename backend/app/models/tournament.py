import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TournamentMode(enum.StrEnum):
    swiss = "swiss"
    fixed = "fixed"


class TournamentStatus(enum.StrEnum):
    pending = "pending"
    vorrunde = "vorrunde"
    ko = "ko"
    finished = "finished"


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    player_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[TournamentMode] = mapped_column(
        Enum(TournamentMode), nullable=False, default=TournamentMode.swiss
    )
    status: Mapped[TournamentStatus] = mapped_column(
        Enum(TournamentStatus), nullable=False, default=TournamentStatus.pending
    )

    # Relationships
    players: Mapped[list["TournamentPlayer"]] = relationship(
        back_populates="tournament"
    )
    matches: Mapped[list["Match"]] = relationship(  # noqa: F821
        back_populates="tournament"
    )


class TournamentPlayer(Base):
    __tablename__ = "tournament_players"

    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), primary_key=True
    )
    reg_points: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bonus_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    tournament: Mapped["Tournament"] = relationship(back_populates="players")
    player: Mapped["Player"] = relationship(back_populates="tournament_entries")  # noqa: F821

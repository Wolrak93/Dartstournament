from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    music_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    championship_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    tournament_entries: Mapped[list["TournamentPlayer"]] = relationship(  # noqa: F821
        back_populates="player"
    )
    betting_account: Mapped["BettingAccount | None"] = relationship(  # noqa: F821
        back_populates="player"
    )

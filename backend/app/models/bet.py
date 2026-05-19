from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BettingAccount(Base):
    __tablename__ = "betting_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Nullable: spectators have no player entry
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True, unique=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)

    # Relationships
    player: Mapped["Player | None"] = relationship(  # noqa: F821
        back_populates="betting_account"
    )
    bets: Mapped[list["Bet"]] = relationship(back_populates="account")


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("betting_accounts.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    picked_player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    # Payout is null until the match finishes and bets are settled
    payout: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    account: Mapped["BettingAccount"] = relationship(back_populates="bets")

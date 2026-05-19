"""Tests for SQLAlchemy models: DB relations and constraints."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.database import Base
from app.models.bet import Bet, BettingAccount
from app.models.match import Match, MatchStatus, RoundType, Visit
from app.models.player import Player
from app.models.special_event import EventType, SpecialEvent
from app.models.tournament import (
    Tournament,
    TournamentMode,
    TournamentPlayer,
    TournamentStatus,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _create_player(
    session: AsyncSession, name: str, championships: int = 0
) -> Player:
    player = Player(name=name, championship_count=championships)
    session.add(player)
    await session.flush()
    return player


async def _create_tournament(
    session: AsyncSession, player_count: int = 9
) -> Tournament:
    tournament = Tournament(
        player_count=player_count,
        mode=TournamentMode.swiss,
        status=TournamentStatus.pending,
    )
    session.add(tournament)
    await session.flush()
    return tournament


class TestPlayerModel:
    async def test_create_player_minimal(self, db_session: AsyncSession):
        player = Player(name="Henrik")
        db_session.add(player)
        await db_session.flush()

        assert player.id is not None
        assert player.name == "Henrik"
        assert player.championship_count == 0
        assert player.photo_path is None
        assert player.music_path is None

    async def test_create_player_full(self, db_session: AsyncSession):
        player = Player(
            name="Mike",
            photo_path="pics/mike.jpg",
            music_path="music/mike.mp3",
            championship_count=3,
        )
        db_session.add(player)
        await db_session.flush()

        assert player.name == "Mike"
        assert player.photo_path == "pics/mike.jpg"
        assert player.music_path == "music/mike.mp3"
        assert player.championship_count == 3

    async def test_player_name_unique(self, db_session: AsyncSession):
        from sqlalchemy.exc import IntegrityError

        db_session.add(Player(name="Lars"))
        await db_session.flush()

        db_session.add(Player(name="Lars"))
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestTournamentWithPlayers:
    async def test_create_tournament_with_players(self, db_session: AsyncSession):
        """Create a tournament with multiple players and verify DB relations."""
        players = [await _create_player(db_session, f"Player{i}") for i in range(9)]
        tournament = await _create_tournament(db_session, player_count=9)

        for player in players:
            tp = TournamentPlayer(
                tournament_id=tournament.id,
                player_id=player.id,
                reg_points=0.0,
                bonus_points=0,
                avg_score=0.0,
            )
            db_session.add(tp)
        await db_session.commit()

        # Use selectinload to eagerly load relations in async context
        result = await db_session.execute(
            select(Tournament)
            .where(Tournament.id == tournament.id)
            .options(selectinload(Tournament.players))
        )
        loaded = result.scalar_one()
        assert len(loaded.players) == 9

    async def test_tournament_player_defaults(self, db_session: AsyncSession):
        player = await _create_player(db_session, "Jonas")
        tournament = await _create_tournament(db_session)

        tp = TournamentPlayer(tournament_id=tournament.id, player_id=player.id)
        db_session.add(tp)
        await db_session.flush()

        assert tp.reg_points == 0.0
        assert tp.bonus_points == 0
        assert tp.avg_score == 0.0

    async def test_tournament_defaults(self, db_session: AsyncSession):
        tournament = Tournament(player_count=10)
        db_session.add(tournament)
        await db_session.flush()

        assert tournament.mode == TournamentMode.swiss
        assert tournament.status == TournamentStatus.pending
        assert tournament.created_at is not None

    async def test_tournament_player_count_stored(self, db_session: AsyncSession):
        for count in [9, 10, 11, 12, 13]:
            t = Tournament(player_count=count)
            db_session.add(t)
        await db_session.flush()


class TestMatchModel:
    async def test_create_singles_match(self, db_session: AsyncSession):
        p1 = await _create_player(db_session, "Philipp")
        p2 = await _create_player(db_session, "Jens")
        tournament = await _create_tournament(db_session)

        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.vorrunde,
            round_number=1,
            player1_id=p1.id,
            player2_id=p2.id,
            starting_score_p1=301,
            starting_score_p2=301,
        )
        db_session.add(match)
        await db_session.flush()

        assert match.id is not None
        assert match.player3_id is None
        assert match.player4_id is None
        assert match.winner_id is None
        assert match.status == MatchStatus.pending

    async def test_create_doubles_match(self, db_session: AsyncSession):
        players = [await _create_player(db_session, f"P{i}") for i in range(4)]
        tournament = await _create_tournament(db_session, player_count=12)

        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.vorrunde,
            round_number=1,
            player1_id=players[0].id,
            player2_id=players[1].id,
            player3_id=players[2].id,
            player4_id=players[3].id,
            starting_score_p1=301,
            starting_score_p2=301,
        )
        db_session.add(match)
        await db_session.flush()

        assert match.player3_id == players[2].id
        assert match.player4_id == players[3].id

    async def test_match_handicap_starting_scores(self, db_session: AsyncSession):
        p1 = await _create_player(db_session, "Elina", championships=5)
        p2 = await _create_player(db_session, "Lena", championships=0)
        tournament = await _create_tournament(db_session)

        # diff=5 → +180 for stronger side → 501+180=681
        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.ko,
            round_number=1,
            player1_id=p1.id,
            player2_id=p2.id,
            starting_score_p1=681,
            starting_score_p2=501,
        )
        db_session.add(match)
        await db_session.flush()

        assert match.starting_score_p1 == 681
        assert match.starting_score_p2 == 501

    async def test_all_round_types(self, db_session: AsyncSession):
        p1 = await _create_player(db_session, "Janni")
        p2 = await _create_player(db_session, "Joachim")
        tournament = await _create_tournament(db_session)

        for rt in RoundType:
            match = Match(
                tournament_id=tournament.id,
                round_type=rt,
                round_number=1,
                player1_id=p1.id,
                player2_id=p2.id,
                starting_score_p1=301,
                starting_score_p2=301,
            )
            db_session.add(match)
        await db_session.flush()


class TestVisitModel:
    async def test_create_visit(self, db_session: AsyncSession):
        p1 = await _create_player(db_session, "VisitP1")
        p2 = await _create_player(db_session, "VisitP2")
        tournament = await _create_tournament(db_session)
        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.vorrunde,
            round_number=1,
            player1_id=p1.id,
            player2_id=p2.id,
            starting_score_p1=301,
            starting_score_p2=301,
        )
        db_session.add(match)
        await db_session.flush()

        visit = Visit(
            match_id=match.id,
            player_id=p1.id,
            visit_number=1,
            dart1=60,
            dart2=60,
            dart3=60,
            total=180,
            is_bust=False,
        )
        db_session.add(visit)
        await db_session.flush()

        assert visit.id is not None
        assert visit.total == 180
        assert visit.is_bust is False

    async def test_bust_visit(self, db_session: AsyncSession):
        p1 = await _create_player(db_session, "BustP1")
        p2 = await _create_player(db_session, "BustP2")
        tournament = await _create_tournament(db_session)
        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.vorrunde,
            round_number=1,
            player1_id=p1.id,
            player2_id=p2.id,
            starting_score_p1=301,
            starting_score_p2=301,
        )
        db_session.add(match)
        await db_session.flush()

        visit = Visit(
            match_id=match.id,
            player_id=p1.id,
            visit_number=5,
            dart1=20,
            dart2=15,
            dart3=1,
            total=36,
            is_bust=True,
        )
        db_session.add(visit)
        await db_session.flush()

        assert visit.is_bust is True


class TestSpecialEventModel:
    async def test_create_special_event(self, db_session: AsyncSession):
        p1 = await _create_player(db_session, "EventP1")
        p2 = await _create_player(db_session, "EventP2")
        tournament = await _create_tournament(db_session)
        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.vorrunde,
            round_number=1,
            player1_id=p1.id,
            player2_id=p2.id,
            starting_score_p1=301,
            starting_score_p2=301,
        )
        db_session.add(match)
        await db_session.flush()

        visit = Visit(
            match_id=match.id,
            player_id=p1.id,
            visit_number=1,
            dart1=60,
            dart2=60,
            dart3=60,
            total=180,
            is_bust=False,
        )
        db_session.add(visit)
        await db_session.flush()

        event = SpecialEvent(
            visit_id=visit.id,
            player_id=p1.id,
            event_type=EventType.score_180,
            bonus_value=1800,
            count=1,
        )
        db_session.add(event)
        await db_session.flush()

        assert event.id is not None
        assert event.event_type == EventType.score_180
        assert event.bonus_value == 1800

    async def test_ko_event_zero_bonus(self, db_session: AsyncSession):
        """KO match events should be stored with bonus_value=0."""
        p1 = await _create_player(db_session, "KOP1")
        p2 = await _create_player(db_session, "KOP2")
        tournament = await _create_tournament(db_session)
        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.ko,
            round_number=1,
            player1_id=p1.id,
            player2_id=p2.id,
            starting_score_p1=501,
            starting_score_p2=501,
        )
        db_session.add(match)
        await db_session.flush()

        visit = Visit(
            match_id=match.id,
            player_id=p1.id,
            visit_number=1,
            dart1=60,
            dart2=60,
            dart3=60,
            total=180,
            is_bust=False,
        )
        db_session.add(visit)
        await db_session.flush()

        event = SpecialEvent(
            visit_id=visit.id,
            player_id=p1.id,
            event_type=EventType.score_180,
            bonus_value=0,
            count=1,
        )
        db_session.add(event)
        await db_session.flush()

        assert event.bonus_value == 0


class TestBettingModels:
    async def test_create_player_betting_account(self, db_session: AsyncSession):
        player = await _create_player(db_session, "BetPlayer")
        account = BettingAccount(
            player_id=player.id, name="BetPlayer", balance=1000.0
        )
        db_session.add(account)
        await db_session.flush()

        assert account.id is not None
        assert account.balance == 1000.0

    async def test_create_spectator_account(self, db_session: AsyncSession):
        """Spectators have no player_id."""
        account = BettingAccount(player_id=None, name="Uncle Bob", balance=1000.0)
        db_session.add(account)
        await db_session.flush()

        assert account.player_id is None
        assert account.name == "Uncle Bob"

    async def test_create_bet(self, db_session: AsyncSession):
        p1 = await _create_player(db_session, "BetP1")
        p2 = await _create_player(db_session, "BetP2")
        tournament = await _create_tournament(db_session)
        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.vorrunde,
            round_number=1,
            player1_id=p1.id,
            player2_id=p2.id,
            starting_score_p1=301,
            starting_score_p2=301,
        )
        db_session.add(match)
        await db_session.flush()

        account = BettingAccount(name="Bettor", balance=500.0)
        db_session.add(account)
        await db_session.flush()

        bet = Bet(
            match_id=match.id,
            account_id=account.id,
            amount=100.0,
            picked_player_id=p1.id,
        )
        db_session.add(bet)
        await db_session.flush()

        assert bet.id is not None
        assert bet.payout is None  # not settled yet

    async def test_bet_payout_nullable(self, db_session: AsyncSession):
        p1 = await _create_player(db_session, "PayP1")
        p2 = await _create_player(db_session, "PayP2")
        tournament = await _create_tournament(db_session)
        match = Match(
            tournament_id=tournament.id,
            round_type=RoundType.ko,
            round_number=1,
            player1_id=p1.id,
            player2_id=p2.id,
            starting_score_p1=501,
            starting_score_p2=501,
        )
        db_session.add(match)
        await db_session.flush()

        account = BettingAccount(name="PayBettor", balance=500.0)
        db_session.add(account)
        await db_session.flush()

        bet = Bet(
            match_id=match.id,
            account_id=account.id,
            amount=50.0,
            picked_player_id=p1.id,
            payout=150.0,
        )
        db_session.add(bet)
        await db_session.flush()

        assert bet.payout == 150.0

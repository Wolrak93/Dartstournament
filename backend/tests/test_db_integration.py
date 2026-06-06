"""Integration tests for the database persistence layer.

Uses an in-memory SQLite database so every test starts clean.
These tests verify that repositories and service-wiring persistence
helpers interact correctly with the DB schema.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure all models are registered with Base.metadata before create_all.
import app.models  # noqa: F401
from app.database import Base
from app.models.match import Match, MatchStatus, RoundType
from app.models.player import Player
from app.models.special_event import EventType
from app.models.tournament import (
    Tournament,
    TournamentStatus,
)
from app.repositories.match_repo import (
    create_match,
    get_match_by_id,
    list_matches_by_tournament,
    update_match_status,
    update_match_winner,
)
from app.repositories.player_repo import (
    create_player,
    get_player_by_id,
    list_all_players,
    update_championship_count,
)
from app.repositories.special_event_repo import (
    create_special_event,
    list_events_by_visit,
    sum_bonus_by_player_and_tournament,
)
from app.repositories.tournament_player_repo import (
    add_player_to_tournament,
    get_tournament_player,
    list_tournament_players,
    update_tournament_player_standing,
)
from app.repositories.tournament_repo import (
    create_tournament,
    get_tournament_by_id,
    update_tournament_status,
)
from app.repositories.visit_repo import (
    create_visit,
    list_visits_by_match_and_player,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _player(db: AsyncSession, name: str, championships: int = 0) -> Player:
    return await create_player(db, name=name, championship_count=championships)


async def _tournament(db: AsyncSession, count: int = 9) -> Tournament:
    return await create_tournament(db, player_count=count)


async def _match(
    db: AsyncSession,
    tournament: Tournament,
    p1: Player,
    p2: Player,
    score: int = 301,
    round_type: RoundType = RoundType.vorrunde,
) -> Match:
    return await create_match(
        db,
        tournament_id=tournament.id,
        round_type=round_type,
        round_number=1,
        player1_id=p1.id,
        player2_id=p2.id,
        starting_score_p1=score,
        starting_score_p2=score,
    )


# ---------------------------------------------------------------------------
# Player repository tests
# ---------------------------------------------------------------------------


async def test_create_and_read_player(db_session: AsyncSession) -> None:
    player = await _player(db_session, "Alice", championships=2)
    await db_session.commit()

    fetched = await get_player_by_id(db_session, player.id)
    assert fetched is not None
    assert fetched.name == "Alice"
    assert fetched.championship_count == 2


async def test_list_all_players(db_session: AsyncSession) -> None:
    await _player(db_session, "Bob")
    await _player(db_session, "Alice")
    await db_session.commit()

    players = await list_all_players(db_session)
    names = [p.name for p in players]
    assert "Alice" in names
    assert "Bob" in names


async def test_update_championship_count(db_session: AsyncSession) -> None:
    player = await _player(db_session, "Carol")
    await db_session.commit()

    updated = await update_championship_count(db_session, player.id, 5)
    assert updated.championship_count == 5


async def test_get_player_not_found(db_session: AsyncSession) -> None:
    result = await get_player_by_id(db_session, 9999)
    assert result is None


# ---------------------------------------------------------------------------
# Tournament repository tests
# ---------------------------------------------------------------------------


async def test_create_tournament(db_session: AsyncSession) -> None:
    t = await _tournament(db_session, count=10)
    await db_session.commit()

    fetched = await get_tournament_by_id(db_session, t.id)
    assert fetched is not None
    assert fetched.player_count == 10
    assert fetched.status == TournamentStatus.pending


async def test_update_tournament_status(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    await db_session.commit()

    updated = await update_tournament_status(
        db_session, t.id, TournamentStatus.vorrunde
    )
    assert updated.status == TournamentStatus.vorrunde


async def test_get_tournament_with_players(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p = await _player(db_session, "Dave")
    await add_player_to_tournament(db_session, t.id, p.id)
    await db_session.commit()

    fetched = await get_tournament_by_id(db_session, t.id, with_players=True)
    assert fetched is not None
    assert len(fetched.players) == 1
    assert fetched.players[0].player_id == p.id


# ---------------------------------------------------------------------------
# TournamentPlayer repository tests
# ---------------------------------------------------------------------------


async def test_add_player_to_tournament(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p = await _player(db_session, "Eve")
    tp = await add_player_to_tournament(db_session, t.id, p.id)
    await db_session.commit()

    assert tp.tournament_id == t.id
    assert tp.player_id == p.id
    assert tp.reg_points == 0.0
    assert tp.bonus_points == 0


async def test_update_tournament_player_standing(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p = await _player(db_session, "Frank")
    await add_player_to_tournament(db_session, t.id, p.id)
    await db_session.commit()

    tp = await update_tournament_player_standing(
        db_session, t.id, p.id, reg_points=3.5, bonus_points=120, avg_score=62.5
    )
    assert tp.reg_points == 3.5
    assert tp.bonus_points == 120
    assert tp.avg_score == 62.5


async def test_list_tournament_players(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    for name in ["Grace", "Hank", "Ivy"]:
        p = await _player(db_session, name)
        await add_player_to_tournament(db_session, t.id, p.id)
    await db_session.commit()

    tps = await list_tournament_players(db_session, t.id)
    assert len(tps) == 3


# ---------------------------------------------------------------------------
# Match repository tests
# ---------------------------------------------------------------------------


async def test_create_match(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Jack")
    p2 = await _player(db_session, "Kim")
    match = await _match(db_session, t, p1, p2)
    await db_session.commit()

    fetched = await get_match_by_id(db_session, match.id)
    assert fetched is not None
    assert fetched.status == MatchStatus.pending
    assert fetched.round_type == RoundType.vorrunde


async def test_update_match_status(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Liam")
    p2 = await _player(db_session, "Mia")
    match = await _match(db_session, t, p1, p2)
    await db_session.commit()

    updated = await update_match_status(db_session, match.id, MatchStatus.in_progress)
    assert updated.status == MatchStatus.in_progress


async def test_update_match_winner(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Noah")
    p2 = await _player(db_session, "Olivia")
    match = await _match(db_session, t, p1, p2)
    await db_session.commit()

    updated = await update_match_winner(db_session, match.id, winner_id=p1.id)
    assert updated.winner_id == p1.id
    assert updated.status == MatchStatus.finished


async def test_list_matches_by_tournament(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Pete")
    p2 = await _player(db_session, "Quinn")
    await _match(db_session, t, p1, p2)
    await _match(db_session, t, p1, p2)
    await db_session.commit()

    matches = await list_matches_by_tournament(db_session, t.id)
    assert len(matches) == 2


# ---------------------------------------------------------------------------
# Visit repository tests
# ---------------------------------------------------------------------------


async def test_create_visit(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Rosa")
    p2 = await _player(db_session, "Sam")
    match = await _match(db_session, t, p1, p2)
    await db_session.commit()

    visit = await create_visit(
        db_session,
        match_id=match.id,
        player_id=p1.id,
        visit_number=1,
        dart1=60,
        dart2=60,
        dart3=60,
        total=180,
        is_bust=False,
    )
    await db_session.commit()

    assert visit.id is not None
    assert visit.total == 180
    assert not visit.is_bust


async def test_list_visits_by_match_and_player(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Tina")
    p2 = await _player(db_session, "Uma")
    match = await _match(db_session, t, p1, p2)
    await db_session.commit()

    for i in range(3):
        await create_visit(
            db_session,
            match_id=match.id,
            player_id=p1.id,
            visit_number=i + 1,
            dart1=20,
            dart2=20,
            dart3=20,
            total=60,
            is_bust=False,
        )
    await db_session.commit()

    visits = await list_visits_by_match_and_player(db_session, match.id, p1.id)
    assert len(visits) == 3
    assert [v.visit_number for v in visits] == [1, 2, 3]


# ---------------------------------------------------------------------------
# SpecialEvent repository tests
# ---------------------------------------------------------------------------


async def test_create_special_event(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Vera")
    p2 = await _player(db_session, "Will")
    match = await _match(db_session, t, p1, p2)
    await db_session.commit()

    visit = await create_visit(
        db_session,
        match_id=match.id,
        player_id=p1.id,
        visit_number=1,
        dart1=60,
        dart2=60,
        dart3=60,
        total=180,
        is_bust=False,
    )
    await db_session.commit()

    event = await create_special_event(
        db_session,
        visit_id=visit.id,
        player_id=p1.id,
        event_type=EventType.GEWORFEN_180,
        bonus_value=1800,
        count=1,
    )
    await db_session.commit()

    assert event.id is not None
    assert event.bonus_value == 1800


async def test_sum_bonus_by_player_and_tournament(db_session: AsyncSession) -> None:
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Xena")
    p2 = await _player(db_session, "Yogi")
    # Vorrunde match → bonus counts
    match = await _match(db_session, t, p1, p2, round_type=RoundType.vorrunde)
    await db_session.commit()

    visit = await create_visit(
        db_session,
        match_id=match.id,
        player_id=p1.id,
        visit_number=1,
        dart1=60,
        dart2=60,
        dart3=60,
        total=180,
        is_bust=False,
    )
    await create_special_event(
        db_session,
        visit_id=visit.id,
        player_id=p1.id,
        event_type=EventType.GEWORFEN_180,
        bonus_value=1800,
        count=1,
    )
    # Tripel_20 hits 3 times in same visit
    await create_special_event(
        db_session,
        visit_id=visit.id,
        player_id=p1.id,
        event_type=EventType.TRIPEL_20,
        bonus_value=17,
        count=3,
    )
    await db_session.commit()

    total = await sum_bonus_by_player_and_tournament(db_session, t.id, p1.id)
    assert total == 1800 + 17 * 3  # 1851


async def test_sum_bonus_excludes_ko_matches(db_session: AsyncSession) -> None:
    """Bonus from KO matches must not count.

    bonus_value should be 0 in real usage, but we verify the round_type filter.
    """
    t = await _tournament(db_session)
    p1 = await _player(db_session, "Zara")
    p2 = await _player(db_session, "Adam")
    ko_match = await _match(db_session, t, p1, p2, score=501, round_type=RoundType.ko)
    await db_session.commit()

    visit = await create_visit(
        db_session,
        match_id=ko_match.id,
        player_id=p1.id,
        visit_number=1,
        dart1=60,
        dart2=60,
        dart3=60,
        total=180,
        is_bust=False,
    )
    # Even if someone accidentally stores bonus_value > 0 in KO, filter must exclude it
    await create_special_event(
        db_session,
        visit_id=visit.id,
        player_id=p1.id,
        event_type=EventType.GEWORFEN_180,
        bonus_value=1800,  # should be 0 in real usage, but test the filter
        count=1,
    )
    await db_session.commit()

    total = await sum_bonus_by_player_and_tournament(db_session, t.id, p1.id)
    assert total == 0  # KO match is excluded by round_type filter


# ---------------------------------------------------------------------------
# Full flow integration test
# ---------------------------------------------------------------------------


async def test_full_flow_create_tournament_and_record_visit(
    db_session: AsyncSession,
) -> None:
    """Full integration: create tournament, players, match, visit, event, standings."""
    # Setup
    t = await create_tournament(db_session, player_count=9)
    p1 = await create_player(db_session, "Player1")
    p2 = await create_player(db_session, "Player2")
    await add_player_to_tournament(db_session, t.id, p1.id)
    await add_player_to_tournament(db_session, t.id, p2.id)
    await update_tournament_status(db_session, t.id, TournamentStatus.vorrunde)
    await db_session.commit()

    # Verify tournament state
    fetched = await get_tournament_by_id(db_session, t.id, with_players=True)
    assert fetched is not None
    assert fetched.status == TournamentStatus.vorrunde
    assert len(fetched.players) == 2

    # Create and play a match
    match = await create_match(
        db_session,
        tournament_id=t.id,
        round_type=RoundType.vorrunde,
        round_number=1,
        player1_id=p1.id,
        player2_id=p2.id,
        starting_score_p1=301,
        starting_score_p2=301,
    )
    await update_match_status(db_session, match.id, MatchStatus.in_progress)

    # Record a visit
    visit = await create_visit(
        db_session,
        match_id=match.id,
        player_id=p1.id,
        visit_number=1,
        dart1=60,
        dart2=60,
        dart3=60,
        total=180,
        is_bust=False,
    )

    # Record 180-special event
    await create_special_event(
        db_session,
        visit_id=visit.id,
        player_id=p1.id,
        event_type=EventType.GEWORFEN_180,
        bonus_value=1800,
        count=1,
    )

    # Finish match
    await update_match_winner(db_session, match.id, winner_id=p1.id)

    # Update standings
    await update_tournament_player_standing(
        db_session, t.id, p1.id, reg_points=1.0, bonus_points=1800, avg_score=180.0
    )
    await db_session.commit()

    # Verify
    tp = await get_tournament_player(db_session, t.id, p1.id)
    assert tp is not None
    assert tp.reg_points == 1.0
    assert tp.bonus_points == 1800

    bonus = await sum_bonus_by_player_and_tournament(db_session, t.id, p1.id)
    assert bonus == 1800

    events = await list_events_by_visit(db_session, visit.id)
    assert len(events) == 1
    assert events[0].event_type == EventType.GEWORFEN_180


# ---------------------------------------------------------------------------
# Service wiring: persist_visit helper
# ---------------------------------------------------------------------------


async def test_persist_visit_helper(db_session: AsyncSession) -> None:
    """Test that match.persist_visit() creates Visit and SpecialEvent records."""
    from app.services.events import EventType as SvcEventType
    from app.services.events import detect_events
    from app.services.match import (
        Dart,
        DartBand,
        VisitResult,
        persist_visit,
    )

    t = await create_tournament(db_session, player_count=9)
    p1 = await create_player(db_session, "Mover")
    p2 = await create_player(db_session, "Shaker")
    await add_player_to_tournament(db_session, t.id, p1.id)
    await add_player_to_tournament(db_session, t.id, p2.id)
    match = await create_match(
        db_session,
        tournament_id=t.id,
        round_type=RoundType.vorrunde,
        round_number=1,
        player1_id=p1.id,
        player2_id=p2.id,
        starting_score_p1=301,
        starting_score_p2=301,
    )
    await db_session.commit()

    darts = [
        Dart(score=60, band=DartBand.TRIPLE, number=20),
        Dart(score=60, band=DartBand.TRIPLE, number=20),
        Dart(score=60, band=DartBand.TRIPLE, number=20),
    ]
    result = VisitResult(
        darts=darts,
        total=180,
        is_bust=False,
        remaining_after=121,
        finishing_dart=None,
        single_out_mode=False,
    )
    events = detect_events(result, remaining_before=301, is_vorrunde=True)

    visit = await persist_visit(
        db_session,
        match_id=match.id,
        player_id=p1.id,
        visit_number=1,
        darts=darts,
        result=result,
        events=events,
    )
    await db_session.commit()

    assert visit.id is not None
    assert visit.total == 180
    assert not visit.is_bust

    stored_events = await list_events_by_visit(db_session, visit.id)
    event_types = {e.event_type for e in stored_events}
    # 180 visit should trigger GEWORFEN_180, TRIPEL_20 (x3), TRIPEL (x3), GLEICHE_ZAHL
    assert SvcEventType.GEWORFEN_180 in event_types


# ---------------------------------------------------------------------------
# Service wiring: persist_standings helper
# ---------------------------------------------------------------------------


async def test_persist_standings_helper(db_session: AsyncSession) -> None:
    """Test that vorrunde.persist_standings() updates TournamentPlayer rows."""
    from app.services.vorrunde import PlayerStanding, persist_standings

    t = await create_tournament(db_session, player_count=9)
    p1 = await create_player(db_session, "SidA")
    p2 = await create_player(db_session, "SidB")
    await add_player_to_tournament(db_session, t.id, p1.id)
    await add_player_to_tournament(db_session, t.id, p2.id)
    await db_session.commit()

    standings = {
        p1.id: PlayerStanding(
            player_id=p1.id,
            reg_points=2.0,
            bonus_points=180,
            total_score=540,
            total_visits=3,
        ),
        p2.id: PlayerStanding(
            player_id=p2.id,
            reg_points=1.0,
            bonus_points=0,
            total_score=120,
            total_visits=2,
        ),
    }

    await persist_standings(db_session, t.id, standings)
    await db_session.commit()

    tp1 = await get_tournament_player(db_session, t.id, p1.id)
    assert tp1 is not None
    assert tp1.reg_points == 2.0
    assert tp1.bonus_points == 180
    assert tp1.avg_score == pytest.approx(180.0)  # 540 / 3

    tp2 = await get_tournament_player(db_session, t.id, p2.id)
    assert tp2 is not None
    assert tp2.reg_points == 1.0


# ---------------------------------------------------------------------------
# Service wiring: load_bonus_from_db helper
# ---------------------------------------------------------------------------


async def test_load_bonus_from_db_helper(db_session: AsyncSession) -> None:
    """Test that bonus.load_bonus_from_db() reads correct total from DB."""
    from app.services.bonus import load_bonus_from_db

    t = await create_tournament(db_session, player_count=9)
    p1 = await create_player(db_session, "BonusKing")
    p2 = await create_player(db_session, "Opponent")
    match = await create_match(
        db_session,
        tournament_id=t.id,
        round_type=RoundType.vorrunde,
        round_number=1,
        player1_id=p1.id,
        player2_id=p2.id,
        starting_score_p1=301,
        starting_score_p2=301,
    )
    await db_session.commit()

    visit = await create_visit(
        db_session, match_id=match.id, player_id=p1.id,
        visit_number=1, dart1=60, dart2=60, dart3=60, total=180, is_bust=False,
    )
    await create_special_event(
        db_session, visit_id=visit.id, player_id=p1.id,
        event_type=EventType.GEWORFEN_180, bonus_value=1800, count=1,
    )
    await db_session.commit()

    total = await load_bonus_from_db(db_session, t.id, p1.id)
    assert total == 1800

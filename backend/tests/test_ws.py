"""WebSocket endpoint tests.

Uses FastAPI's synchronous TestClient which supports websocket_connect().
Each test gets a fresh in-memory SQLite database via a dependency override.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM models before create_all()
from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client(event_loop):
    """TestClient wired to an isolated in-memory DB."""
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    event_loop.run_until_complete(create_tables())

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    event_loop.run_until_complete(drop_tables())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_player(client: TestClient, name: str, champ: int = 0) -> int:
    r = client.post("/players", json={"name": name, "championship_count": champ})
    assert r.status_code == 201
    return r.json()["id"]


def _create_and_start_tournament(client: TestClient) -> tuple[int, list[int]]:
    """Create 9 players + a tournament and start the vorrunde.

    Returns (tournament_id, match_ids).
    """
    player_ids = [_create_player(client, f"P{i}") for i in range(9)]
    r = client.post("/tournaments", json={"player_ids": player_ids, "mode": "fixed"})
    assert r.status_code == 201
    tournament_id = r.json()["id"]
    r = client.post(f"/tournaments/{tournament_id}/start")
    assert r.status_code == 201
    match_ids = [m["id"] for m in r.json()]
    return tournament_id, match_ids


# ---------------------------------------------------------------------------
# ConnectionManager unit behaviour
# ---------------------------------------------------------------------------


def test_ws_match_initial_message(client):
    """Connecting to a match channel immediately yields a match_state message."""
    _, match_ids = _create_and_start_tournament(client)
    match_id = match_ids[0]

    with client.websocket_connect(f"/ws/match/{match_id}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "match_state"
        assert msg["data"]["match_id"] == match_id
        assert "status" in msg["data"]
        assert "player1_id" in msg["data"]
        assert "player2_id" in msg["data"]
        assert "starting_score_p1" in msg["data"]
        assert "starting_score_p2" in msg["data"]


def test_ws_match_unknown_match_closes(client):
    """Connecting to a non-existent match should close with code 4004."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/match/99999") as ws:
            ws.receive_json()


def test_ws_match_ping_pong(client):
    """Client ping returns pong."""
    _, match_ids = _create_and_start_tournament(client)
    match_id = match_ids[0]

    with client.websocket_connect(f"/ws/match/{match_id}") as ws:
        ws.receive_json()  # consume initial match_state
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


# ---------------------------------------------------------------------------
# Tournament channel
# ---------------------------------------------------------------------------


def test_ws_tournament_initial_message(client):
    """Connecting to a tournament channel immediately yields standings_update."""
    tournament_id, _ = _create_and_start_tournament(client)

    with client.websocket_connect(f"/ws/tournament/{tournament_id}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "standings_update"
        assert msg["data"]["tournament_id"] == tournament_id


def test_ws_tournament_unknown_tournament_closes(client):
    """Connecting to a non-existent tournament should close with code 4004."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/tournament/99999") as ws:
            ws.receive_json()


def test_ws_tournament_ping_pong(client):
    """Client ping on tournament channel returns pong."""
    tournament_id, _ = _create_and_start_tournament(client)

    with client.websocket_connect(f"/ws/tournament/{tournament_id}") as ws:
        ws.receive_json()  # consume initial standings_update
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


# ---------------------------------------------------------------------------
# Broadcast integration: REST → WebSocket
# ---------------------------------------------------------------------------


def test_ws_receives_match_state_after_bull_throw(client):
    """Recording a bull throw broadcasts a match_state event to WS subscribers."""
    _, match_ids = _create_and_start_tournament(client)
    match_id = match_ids[0]

    # Fetch player IDs for this match.
    # Need player IDs — fetch from the initial WS message.
    with client.websocket_connect(f"/ws/match/{match_id}") as ws:
        init_msg = ws.receive_json()
        player1_id = init_msg["data"]["player1_id"]

        # Record bull throw via REST.
        bt_r = client.post(
            f"/matches/{match_id}/bull-throw",
            json={"winner_id": player1_id},
        )
        assert bt_r.status_code == 200

        # Should receive a broadcast match_state.
        broadcast = ws.receive_json()
        assert broadcast["type"] == "match_state"
        assert broadcast["data"]["match_id"] == match_id
        assert broadcast["data"]["status"] == "bull_throw"
        assert broadcast["data"]["starting_player_id"] == player1_id


def test_ws_receives_match_state_after_start(client):
    """Starting a match broadcasts a match_state(in_progress) event."""
    _, match_ids = _create_and_start_tournament(client)
    match_id = match_ids[0]

    with client.websocket_connect(f"/ws/match/{match_id}") as ws:
        init_msg = ws.receive_json()
        player1_id = init_msg["data"]["player1_id"]

        client.post(f"/matches/{match_id}/bull-throw", json={"winner_id": player1_id})
        ws.receive_json()  # consume bull_throw broadcast

        client.post(f"/matches/{match_id}/start")

        broadcast = ws.receive_json()
        assert broadcast["type"] == "match_state"
        assert broadcast["data"]["status"] == "in_progress"


def test_ws_receives_score_update_after_visit(client):
    """Recording a visit broadcasts a score_update event."""
    _, match_ids = _create_and_start_tournament(client)
    match_id = match_ids[0]

    with client.websocket_connect(f"/ws/match/{match_id}") as ws:
        init_msg = ws.receive_json()
        player1_id = init_msg["data"]["player1_id"]

        client.post(f"/matches/{match_id}/bull-throw", json={"winner_id": player1_id})
        ws.receive_json()  # bull_throw broadcast
        client.post(f"/matches/{match_id}/start")
        ws.receive_json()  # in_progress broadcast

        visit_r = client.post(
            f"/matches/{match_id}/visits",
            json={
                "player_id": player1_id,
                "dart1": 20,
                "dart2": 20,
                "dart3": 20,
                "bounce_flags": [False, False, False],
                "robin_hood_flags": [False, False, False],
            },
        )
        assert visit_r.status_code == 201

        broadcast = ws.receive_json()
        assert broadcast["type"] == "score_update"
        d = broadcast["data"]
        assert d["match_id"] == match_id
        assert d["player_id"] == player1_id
        assert d["total"] == 60
        assert not d["is_bust"]
        assert d["remaining_after"] == init_msg["data"]["starting_score_p1"] - 60


def test_ws_receives_match_finished_on_checkout(client):
    """Finishing a match by checkout broadcasts match_finished."""
    _, match_ids = _create_and_start_tournament(client)
    match_id = match_ids[0]

    with client.websocket_connect(f"/ws/match/{match_id}") as ws:
        init_msg = ws.receive_json()
        player1_id = init_msg["data"]["player1_id"]
        starting_score = init_msg["data"]["starting_score_p1"]

        client.post(f"/matches/{match_id}/bull-throw", json={"winner_id": player1_id})
        ws.receive_json()
        client.post(f"/matches/{match_id}/start")
        ws.receive_json()

        # Score down to a double-outable remainder.
        # starting_score is 301 (no handicap for same-level players).
        # Throw 60 per visit until remainder == 40 (D20 checkout).
        remaining = starting_score
        while remaining > 40:
            score_per_visit = min(60, remaining - 40)
            client.post(
                f"/matches/{match_id}/visits",
                json={
                    "player_id": player1_id,
                    "dart1": score_per_visit,
                    "dart2": 0,
                    "dart3": 0,
                    "bounce_flags": [False, False, False],
                    "robin_hood_flags": [False, False, False],
                },
            )
            remaining -= score_per_visit
            # Drain broadcasts (score_update + possible special_event msgs).
            msg = ws.receive_json()
            while msg["type"] != "score_update":
                msg = ws.receive_json()

        # Final checkout: D20 = 40.
        client.post(
            f"/matches/{match_id}/visits",
            json={
                "player_id": player1_id,
                "dart1": 40,  # treated as double-20 by dart_from_score
                "dart2": 0,
                "dart3": 0,
                "bounce_flags": [False, False, False],
                "robin_hood_flags": [False, False, False],
            },
        )

        # Collect messages until we see match_finished.
        messages = []
        for _ in range(10):  # safety limit
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "match_finished":
                break

        types = [m["type"] for m in messages]
        assert "match_finished" in types
        finished_msg = next(m for m in messages if m["type"] == "match_finished")
        assert finished_msg["data"]["match_id"] == match_id
        assert finished_msg["data"]["winner_id"] == player1_id


def test_ws_tournament_receives_standings_update_after_match_finish(client):
    """Referee-override finish broadcasts standings_update on the tournament channel."""
    tournament_id, match_ids = _create_and_start_tournament(client)
    match_id = match_ids[0]

    # Get player IDs for the match.
    r = client.websocket_connect(f"/ws/match/{match_id}")
    with r as ws_match:
        init_msg = ws_match.receive_json()
        player1_id = init_msg["data"]["player1_id"]

    with client.websocket_connect(f"/ws/tournament/{tournament_id}") as ws_t:
        ws_t.receive_json()  # consume initial standings_update

        # Start match and finish via referee override.
        client.post(f"/matches/{match_id}/bull-throw", json={"winner_id": player1_id})
        client.post(f"/matches/{match_id}/start")
        finish_r = client.post(
            f"/matches/{match_id}/finish", json={"winner_id": player1_id}
        )
        assert finish_r.status_code == 200

        broadcast = ws_t.receive_json()
        assert broadcast["type"] == "standings_update"
        assert broadcast["data"]["tournament_id"] == tournament_id

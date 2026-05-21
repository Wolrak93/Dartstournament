"""API tests for match endpoints.

State machine tests:
- can't record visit before bull throw
- can't start match twice
- visit recording happy path
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
PLAYER_NAMES = ["Philipp", "Mike", "Henrik", "Lars", "Joachim", "Jonas", "Janni", "Jens", "Elina"]


@pytest.fixture
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client(event_loop):
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def teardown():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    event_loop.run_until_complete(setup())

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    event_loop.run_until_complete(teardown())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_match(client) -> tuple[int, int, int, int]:
    """Create 9 players, a tournament, start it, and return (tournament_id, match_id, p1_id, p2_id)."""
    player_ids = []
    for name in PLAYER_NAMES:
        r = client.post("/players", json={"name": name})
        player_ids.append(r.json()["id"])

    tour_r = client.post("/tournaments", json={"player_ids": player_ids, "mode": "fixed"})
    tid = tour_r.json()["id"]
    matches_r = client.post(f"/tournaments/{tid}/start")
    matches = matches_r.json()
    mid = matches[0]["id"]
    p1 = matches[0]["player1_id"]
    p2 = matches[0]["player2_id"]
    return tid, mid, p1, p2


# ---------------------------------------------------------------------------
# Bull throw
# ---------------------------------------------------------------------------


def test_bull_throw_singles(client):
    _, mid, p1, p2 = _setup_match(client)
    response = client.post(f"/matches/{mid}/bull-throw", json={"winner_id": p1})
    assert response.status_code == 200
    data = response.json()
    assert data["starting_player_id"] == p1
    assert data["play_order"][0] == p1


def test_bull_throw_updates_status(client):
    _, mid, p1, p2 = _setup_match(client)
    client.post(f"/matches/{mid}/bull-throw", json={"winner_id": p2})

    state = client.get(f"/matches/{mid}/state").json()
    assert state["starting_player_id"] == p2


def test_bull_throw_wrong_player(client):
    _, mid, p1, p2 = _setup_match(client)
    response = client.post(f"/matches/{mid}/bull-throw", json={"winner_id": 9999})
    assert response.status_code in (400, 422)


def test_bull_throw_not_found(client):
    response = client.post("/matches/9999/bull-throw", json={"winner_id": 1})
    assert response.status_code == 404
    assert response.json()["code"] == "match_not_found"


# ---------------------------------------------------------------------------
# Start match
# ---------------------------------------------------------------------------


def test_start_match(client):
    _, mid, p1, p2 = _setup_match(client)
    client.post(f"/matches/{mid}/bull-throw", json={"winner_id": p1})
    response = client.post(f"/matches/{mid}/start")
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_cannot_start_match_before_bull_throw(client):
    _, mid, p1, p2 = _setup_match(client)
    response = client.post(f"/matches/{mid}/start")
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_match_status"


def test_cannot_start_match_twice(client):
    _, mid, p1, p2 = _setup_match(client)
    client.post(f"/matches/{mid}/bull-throw", json={"winner_id": p1})
    client.post(f"/matches/{mid}/start")
    response = client.post(f"/matches/{mid}/start")
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Visit recording
# ---------------------------------------------------------------------------


def _start_match(client, mid, p1):
    client.post(f"/matches/{mid}/bull-throw", json={"winner_id": p1})
    client.post(f"/matches/{mid}/start")


def test_record_visit_happy_path(client):
    _, mid, p1, p2 = _setup_match(client)
    _start_match(client, mid, p1)

    response = client.post(
        f"/matches/{mid}/visits",
        json={"player_id": p1, "dart1": 20, "dart2": 20, "dart3": 20},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["player_id"] == p1
    assert data["visit_number"] == 1
    assert data["total"] == 60
    assert data["is_bust"] is False
    assert data["remaining_after"] == 301 - 60
    assert data["match_finished"] is False


def test_record_visit_cannot_before_in_progress(client):
    _, mid, p1, p2 = _setup_match(client)
    response = client.post(
        f"/matches/{mid}/visits",
        json={"player_id": p1, "dart1": 20, "dart2": 20, "dart3": 20},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_match_status"


def test_record_visit_invalid_player(client):
    _, mid, p1, p2 = _setup_match(client)
    _start_match(client, mid, p1)

    response = client.post(
        f"/matches/{mid}/visits",
        json={"player_id": 9999, "dart1": 20, "dart2": 20, "dart3": 20},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "player_not_in_match"


def test_record_bust(client):
    _, mid, p1, p2 = _setup_match(client)
    _start_match(client, mid, p1)

    # Visit 1 for p1: score 180, remaining = 301 - 180 = 121
    client.post(
        f"/matches/{mid}/visits",
        json={"player_id": p1, "dart1": 60, "dart2": 60, "dart3": 60},
    )
    client.post(
        f"/matches/{mid}/visits",
        json={"player_id": p2, "dart1": 0, "dart2": 0, "dart3": 0},
    )
    # Visit 2 for p1: score 60, remaining = 121 - 60 = 61
    client.post(
        f"/matches/{mid}/visits",
        json={"player_id": p1, "dart1": 60, "dart2": 0, "dart3": 0},
    )
    client.post(
        f"/matches/{mid}/visits",
        json={"player_id": p2, "dart1": 0, "dart2": 0, "dart3": 0},
    )
    # Visit 3 for p1: score 60 → remaining would be 1 → bust in double-out
    bust_resp = client.post(
        f"/matches/{mid}/visits",
        json={"player_id": p1, "dart1": 60, "dart2": 0, "dart3": 0},
    )
    assert bust_resp.status_code == 201
    data = bust_resp.json()
    assert data["is_bust"] is True
    assert data["remaining_after"] == 61  # unchanged on bust


def test_record_visit_bounce_scores_zero(client):
    _, mid, p1, p2 = _setup_match(client)
    _start_match(client, mid, p1)

    response = client.post(
        f"/matches/{mid}/visits",
        json={
            "player_id": p1,
            "dart1": 60,
            "dart2": 60,
            "dart3": 60,
            "bounce_flags": [True, False, False],
        },
    )
    assert response.status_code == 201
    data = response.json()
    # dart1 bounced out → only dart2 + dart3 scored
    assert data["total"] == 120
    # Bounce event should be detected
    assert any(e["event_type"] == "bounce" for e in data["special_events"])


# ---------------------------------------------------------------------------
# Match state
# ---------------------------------------------------------------------------


def test_get_match_state_before_start(client):
    _, mid, p1, p2 = _setup_match(client)
    response = client.get(f"/matches/{mid}/state")
    assert response.status_code == 200
    data = response.json()
    assert data["remaining_p1"] == 301
    assert data["remaining_p2"] == 301
    assert data["visit_count_p1"] == 0
    assert data["visit_count_p2"] == 0


def test_get_match_state_after_visit(client):
    _, mid, p1, p2 = _setup_match(client)
    _start_match(client, mid, p1)

    client.post(
        f"/matches/{mid}/visits",
        json={"player_id": p1, "dart1": 60, "dart2": 60, "dart3": 60},
    )

    state = client.get(f"/matches/{mid}/state").json()
    assert state["remaining_p1"] == 301 - 180
    assert state["remaining_p2"] == 301
    assert state["visit_count_p1"] == 1
    assert state["visit_count_p2"] == 0
    # Current player should now be p2
    assert state["current_player_id"] == p2


# ---------------------------------------------------------------------------
# Force finish (referee override)
# ---------------------------------------------------------------------------


def test_finish_match_override(client):
    _, mid, p1, p2 = _setup_match(client)
    _start_match(client, mid, p1)

    response = client.post(f"/matches/{mid}/finish", json={"winner_id": p1})
    assert response.status_code == 200
    data = response.json()
    assert data["winner_id"] == p1
    assert data["status"] == "finished"


def test_finish_match_invalid_winner(client):
    _, mid, p1, p2 = _setup_match(client)
    _start_match(client, mid, p1)

    response = client.post(f"/matches/{mid}/finish", json={"winner_id": 9999})
    assert response.status_code == 400
    assert response.json()["code"] == "player_not_in_match"


def test_finish_match_pending_fails(client):
    _, mid, p1, p2 = _setup_match(client)
    response = client.post(f"/matches/{mid}/finish", json={"winner_id": p1})
    assert response.status_code == 409

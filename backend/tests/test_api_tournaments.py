"""API tests for tournament endpoints."""

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


def _create_players(client, names: list[str]) -> list[int]:
    """Create players and return their IDs."""
    ids = []
    for name in names:
        r = client.post("/players", json={"name": name})
        assert r.status_code == 201
        ids.append(r.json()["id"])
    return ids


# ---------------------------------------------------------------------------
# POST /tournaments
# ---------------------------------------------------------------------------


def test_create_tournament(client):
    ids = _create_players(client, PLAYER_NAMES)
    payload = {"player_ids": ids, "mode": "swiss"}
    response = client.post("/tournaments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["player_count"] == 9
    assert data["mode"] == "swiss"
    assert data["status"] == "pending"


def test_create_tournament_too_few_players(client):
    ids = _create_players(client, PLAYER_NAMES[:8])
    response = client.post("/tournaments", json={"player_ids": ids, "mode": "swiss"})
    assert response.status_code == 422


def test_create_tournament_unknown_player(client):
    ids = _create_players(client, PLAYER_NAMES)
    ids[-1] = 9999  # replace last with nonexistent
    response = client.post("/tournaments", json={"player_ids": ids, "mode": "swiss"})
    assert response.status_code == 404
    assert response.json()["code"] == "player_not_found"


def test_create_tournament_duplicate_players(client):
    ids = _create_players(client, PLAYER_NAMES)
    ids[-1] = ids[0]  # duplicate
    response = client.post("/tournaments", json={"player_ids": ids, "mode": "swiss"})
    assert response.status_code == 400
    assert response.json()["code"] == "duplicate_player_ids"


# ---------------------------------------------------------------------------
# GET /tournaments/{id}
# ---------------------------------------------------------------------------


def test_get_tournament(client):
    ids = _create_players(client, PLAYER_NAMES)
    create_r = client.post("/tournaments", json={"player_ids": ids, "mode": "fixed"})
    tid = create_r.json()["id"]

    response = client.get(f"/tournaments/{tid}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tid
    assert data["player_count"] == 9
    assert len(data["players"]) == 9


def test_get_tournament_not_found(client):
    response = client.get("/tournaments/9999")
    assert response.status_code == 404
    assert response.json()["code"] == "tournament_not_found"


# ---------------------------------------------------------------------------
# POST /tournaments/{id}/start
# ---------------------------------------------------------------------------


def test_start_tournament_fixed(client):
    ids = _create_players(client, PLAYER_NAMES)
    create_r = client.post("/tournaments", json={"player_ids": ids, "mode": "fixed"})
    tid = create_r.json()["id"]

    response = client.post(f"/tournaments/{tid}/start")
    assert response.status_code == 201
    matches = response.json()
    assert len(matches) > 0
    # All matches should be vorrunde
    assert all(m["round_type"] == "vorrunde" for m in matches)
    # Each match has valid player IDs
    for m in matches:
        assert m["player1_id"] in ids
        assert m["player2_id"] in ids


def test_start_tournament_swiss(client):
    ids = _create_players(client, PLAYER_NAMES)
    create_r = client.post("/tournaments", json={"player_ids": ids, "mode": "swiss"})
    tid = create_r.json()["id"]

    response = client.post(f"/tournaments/{tid}/start")
    assert response.status_code == 201
    matches = response.json()
    assert len(matches) > 0


def test_start_tournament_cannot_start_twice(client):
    ids = _create_players(client, PLAYER_NAMES)
    create_r = client.post("/tournaments", json={"player_ids": ids, "mode": "fixed"})
    tid = create_r.json()["id"]

    client.post(f"/tournaments/{tid}/start")
    response = client.post(f"/tournaments/{tid}/start")
    assert response.status_code == 409
    assert response.json()["code"] == "tournament_already_started"


# ---------------------------------------------------------------------------
# GET /tournaments/{id}/standings
# ---------------------------------------------------------------------------


def test_get_standings(client):
    ids = _create_players(client, PLAYER_NAMES)
    create_r = client.post("/tournaments", json={"player_ids": ids, "mode": "fixed"})
    tid = create_r.json()["id"]
    client.post(f"/tournaments/{tid}/start")

    response = client.get(f"/tournaments/{tid}/standings")
    assert response.status_code == 200
    standings = response.json()
    assert len(standings) == 9
    ranks = [s["rank"] for s in standings]
    assert ranks == list(range(1, 10))


# ---------------------------------------------------------------------------
# GET /tournaments/{id}/matches
# ---------------------------------------------------------------------------


def test_get_matches(client):
    ids = _create_players(client, PLAYER_NAMES)
    create_r = client.post("/tournaments", json={"player_ids": ids, "mode": "fixed"})
    tid = create_r.json()["id"]
    client.post(f"/tournaments/{tid}/start")

    response = client.get(f"/tournaments/{tid}/matches")
    assert response.status_code == 200
    matches = response.json()
    assert len(matches) > 0


# ---------------------------------------------------------------------------
# GET /tournaments/{id}/matches/next
# ---------------------------------------------------------------------------


def test_get_next_matches(client):
    ids = _create_players(client, PLAYER_NAMES)
    create_r = client.post("/tournaments", json={"player_ids": ids, "mode": "fixed"})
    tid = create_r.json()["id"]
    client.post(f"/tournaments/{tid}/start")

    response = client.get(f"/tournaments/{tid}/matches/next")
    assert response.status_code == 200
    next_matches = response.json()
    assert len(next_matches) > 0
    # Fixed draw: returns all active (pending/bull_throw/in_progress) matches across all rounds
    active_statuses = {"pending", "bull_throw", "in_progress"}
    assert all(m["status"] in active_statuses for m in next_matches)
    # Ordered by round_number ascending
    round_numbers = [m["round_number"] for m in next_matches]
    assert round_numbers == sorted(round_numbers)
    # Fixed draw with 9 players generates multiple rounds (at least 2)
    assert len(set(round_numbers)) > 1

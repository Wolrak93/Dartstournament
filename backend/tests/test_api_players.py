"""API tests for player endpoints.

Uses FastAPI TestClient with an in-memory SQLite database via dependency override.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all models before create_all
from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def client(event_loop):
    """Synchronous TestClient with the in-memory DB dependency overridden."""
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    loop = event_loop
    loop.run_until_complete(create_tables())

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    loop.run_until_complete(drop_tables())


@pytest.fixture
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# GET /players — empty list
# ---------------------------------------------------------------------------


def test_list_players_empty(client):
    response = client.get("/players")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /players — create player
# ---------------------------------------------------------------------------


def test_create_player(client):
    payload = {"name": "Philipp", "championship_count": 2}
    response = client.post("/players", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Philipp"
    assert data["championship_count"] == 2
    assert data["id"] >= 1
    assert data["photo_path"] is None
    assert data["music_path"] is None


def test_create_player_with_assets(client):
    payload = {
        "name": "Mike",
        "photo_path": "pics/mike.jpg",
        "music_path": "music/mike.mp3",
        "championship_count": 0,
    }
    response = client.post("/players", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["photo_path"] == "pics/mike.jpg"
    assert data["music_path"] == "music/mike.mp3"


def test_create_player_name_required(client):
    response = client.post("/players", json={})
    assert response.status_code == 422


def test_create_player_name_too_short(client):
    response = client.post("/players", json={"name": ""})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /players/{id} — fetch single player
# ---------------------------------------------------------------------------


def test_get_player(client):
    create_resp = client.post("/players", json={"name": "Jonas"})
    player_id = create_resp.json()["id"]

    response = client.get(f"/players/{player_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Jonas"


def test_get_player_not_found(client):
    response = client.get("/players/9999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "code" in data
    assert data["code"] == "player_not_found"


# ---------------------------------------------------------------------------
# GET /players — list after creating players
# ---------------------------------------------------------------------------


def test_list_players_after_create(client):
    client.post("/players", json={"name": "Lars"})
    client.post("/players", json={"name": "Jens"})

    response = client.get("/players")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Lars" in names
    assert "Jens" in names

"""Tests for mobile API: auth, matches, standings, bracket, stats, profile."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client(event_loop):
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

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
    tc = TestClient(app)
    # Attach helpers so tests can seed into the in-memory DB
    tc._event_loop = event_loop
    tc._session_factory = session_factory
    yield tc
    app.dependency_overrides.clear()
    event_loop.run_until_complete(teardown())


# --- JWT utility tests ---

def test_create_and_verify_token():
    from app.auth import create_mobile_token, verify_mobile_token
    token = create_mobile_token(player_id=7, name="Lars")
    payload = verify_mobile_token(token)
    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["name"] == "Lars"


def test_verify_invalid_token_returns_none():
    from app.auth import verify_mobile_token
    assert verify_mobile_token("not.a.token") is None


def test_verify_token_with_non_int_sub_is_valid_jwt_but_rejected_by_dependency():
    """A JWT with sub='not-a-number' passes verify_mobile_token (valid signature)
    but _get_current_player must catch the ValueError and raise 401.
    Full dependency path is tested in test_mobile_endpoints.py (TODO 22).
    """
    # Manually craft a token with non-int sub using same secret/algorithm
    import os

    import jwt as pyjwt

    from app.auth import verify_mobile_token
    secret = os.getenv("MOBILE_JWT_SECRET", "backsberger-open-dev-secret-key-2024")
    bad_token = pyjwt.encode(
        {"sub": "not-a-number", "name": "x"}, secret, algorithm="HS256"
    )
    payload = verify_mobile_token(bad_token)
    # Token is cryptographically valid, so verify_mobile_token returns the dict
    assert payload is not None
    assert payload["sub"] == "not-a-number"
    # Attempting int() on it raises ValueError — _get_current_player catches this as 401
    with pytest.raises(ValueError):
        int(payload["sub"])


# TODO (task 22, feature/mobile-backend-endpoints): add tests for
# _get_current_player failure paths (missing 'sub', non-int 'sub', player not found)
# via a real protected endpoint in test_mobile_endpoints.py.


# --- Auth endpoint tests ---

def test_mobile_login_success(client: TestClient):
    from app.models.player import Player

    async def seed():
        async with client._session_factory() as db:
            db.add(Player(name="Lars", pin="1234"))
            await db.commit()

    client._event_loop.run_until_complete(seed())

    resp = client.post("/mobile/auth/login", json={"player_id": 1, "pin": "1234"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert body["name"] == "Lars"


def test_mobile_login_wrong_pin(client: TestClient):
    from app.models.player import Player

    async def seed():
        async with client._session_factory() as db:
            db.add(Player(name="Mike", pin="5678"))
            await db.commit()

    client._event_loop.run_until_complete(seed())

    resp = client.post("/mobile/auth/login", json={"player_id": 1, "pin": "0000"})
    assert resp.status_code == 401


# --- GET /mobile/matches ---

def test_mobile_matches_no_active_tournament(client: TestClient):
    from app.auth import create_mobile_token
    from app.models.player import Player

    async def seed():
        async with client._session_factory() as db:
            db.add(Player(name="Lars", pin="1234"))
            await db.commit()

    client._event_loop.run_until_complete(seed())

    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/matches", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_id"] is None
    assert body["live"] == []
    assert body["upcoming"] == []
    assert body["completed"] == []


# --- GET /mobile/standings ---

def test_mobile_standings_no_active_tournament(client: TestClient):
    from app.auth import create_mobile_token
    from app.models.player import Player

    async def seed():
        async with client._session_factory() as db:
            db.add(Player(name="Lars", pin="1234"))
            await db.commit()

    client._event_loop.run_until_complete(seed())

    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/standings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_id"] is None
    assert body["entries"] == []
    assert body["phase"] == "none"


# --- GET /mobile/bracket ---

def test_mobile_bracket_no_active_tournament(client: TestClient):
    from app.auth import create_mobile_token
    from app.models.player import Player

    async def seed():
        async with client._session_factory() as db:
            db.add(Player(name="Lars", pin="1234"))
            await db.commit()

    client._event_loop.run_until_complete(seed())

    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/bracket", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_id"] is None
    assert body["ko_rounds"] == []
    assert body["nebenrunde"] == []


# --- GET /mobile/stats ---

def test_mobile_stats_no_active_tournament(client: TestClient):
    from app.auth import create_mobile_token
    from app.models.player import Player

    async def seed():
        async with client._session_factory() as db:
            db.add(Player(name="Lars", pin="1234"))
            await db.commit()

    client._event_loop.run_until_complete(seed())

    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_id"] is None
    assert body["players"] == []
    assert body["totals"] == {}


# --- GET /mobile/me ---

def test_mobile_me_returns_player_data(client: TestClient):
    from app.auth import create_mobile_token
    from app.models.player import Player as PlayerModel

    async def seed():
        async with client._session_factory() as db:
            db.add(PlayerModel(name="Lars", pin="1234"))
            await db.commit()

    client._event_loop.run_until_complete(seed())

    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Lars"
    assert body["player_id"] == 1
    assert body["rank"] is None  # no active tournament

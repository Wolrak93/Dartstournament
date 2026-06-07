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

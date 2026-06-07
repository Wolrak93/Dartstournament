# Cycle 3 — Mobile Web Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-first web interface at `/mobile/*` for players and remote spectators to follow the Backsberger Open live, protected by a name + 4-digit PIN login and served over Cloudflare Tunnel.

**Architecture:** New `/mobile/*` route tree inside the existing React/Vite frontend. New `backend/app/routers/mobile.py` handles all `/mobile/*` REST endpoints (auth + data). The existing `useWebSocket` hook is reused unchanged for real-time score updates. JWT stored in `localStorage` protects all mobile routes.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React + react-router-dom v6 + TypeScript (frontend), PyJWT (new dependency), Vitest + Testing Library (frontend tests), pytest + TestClient (backend tests).

---

## File Map

**New backend files:**
- `backend/app/auth.py` — JWT sign/verify utilities
- `backend/app/schemas/mobile.py` — Pydantic schemas for all mobile endpoints
- `backend/app/routers/mobile.py` — All `/mobile/*` endpoints
- `backend/tests/test_mobile.py` — All mobile backend tests

**Modified backend files:**
- `backend/app/models/player.py` — add `pin` column
- `backend/app/database.py` — add migration for `pin` column
- `backend/app/main.py` — register mobile router, update CORS to `["*"]`
- `backend/pyproject.toml` — add `PyJWT` dependency

**New frontend files:**
- `frontend/src/mobile/mobileAuth.ts` — token storage utilities
- `frontend/src/mobile/MobileLayout.tsx` — header wrapper + `<Outlet />`
- `frontend/src/mobile/MobileGuard.tsx` — auth redirect gate
- `frontend/src/mobile/screens/LoginScreen.tsx`
- `frontend/src/mobile/screens/HomeScreen.tsx`
- `frontend/src/mobile/screens/SpielePage.tsx`
- `frontend/src/mobile/screens/VorrundeSeite.tsx`
- `frontend/src/mobile/screens/BracketPage.tsx`
- `frontend/src/mobile/screens/StatisticsPage.tsx`
- `frontend/src/mobile/screens/ProfilPage.tsx`
- `frontend/src/__tests__/mobile/` — one test file per screen

**Modified frontend files:**
- `frontend/src/api/client.ts` — add `apiGetAuth`, `apiPostAuth`, and all mobile API functions
- `frontend/src/api/types.ts` — add mobile response types
- `frontend/src/App.tsx` — add `/mobile/*` route tree
- `.gitignore` — add `.superpowers/`

---

## Task 1: Add `pin` column to Player model

**Files:**
- Modify: `backend/app/models/player.py`
- Modify: `backend/app/database.py`

- [ ] **Step 1: Add `pin` column to Player**

In `backend/app/models/player.py`, add after `championship_count`:

```python
pin: Mapped[str | None] = mapped_column(String(4), nullable=True)
```

- [ ] **Step 2: Add migration in `init_db`**

In `backend/app/database.py`, add inside the `async with engine.begin() as conn:` block in `init_db()`, after the existing `name` migration:

```python
result = await conn.execute(text("PRAGMA table_info(players)"))
columns = [row[1] for row in result.fetchall()]
if "pin" not in columns:
    await conn.execute(text("ALTER TABLE players ADD COLUMN pin VARCHAR(4)"))
```

- [ ] **Step 3: Run existing tests to confirm nothing broke**

```
cd backend
uv run python -m pytest tests/ -x -q
```

Expected: all tests pass (401+).

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/player.py backend/app/database.py
git commit -m "feat: add pin column to Player model"
```

---

## Task 2: Add PyJWT and write JWT utilities

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/auth.py`

- [ ] **Step 1: Add PyJWT dependency**

```
cd backend
uv add PyJWT
```

Verify `pyproject.toml` now lists `PyJWT` under `dependencies`.

- [ ] **Step 2: Write failing test**

Create `backend/tests/test_mobile.py`:

```python
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
    yield TestClient(app)
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
```

- [ ] **Step 3: Run test to confirm it fails**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_create_and_verify_token -v
```

Expected: `ModuleNotFoundError: No module named 'app.auth'`

- [ ] **Step 4: Create `backend/app/auth.py`**

```python
import os

import jwt

_SECRET = os.getenv("MOBILE_JWT_SECRET", "backsberger-dev-secret")
_ALGORITHM = "HS256"


def create_mobile_token(player_id: int, name: str) -> str:
    return jwt.encode({"sub": str(player_id), "name": name}, _SECRET, algorithm=_ALGORITHM)


def verify_mobile_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
```

- [ ] **Step 5: Run tests to confirm they pass**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_create_and_verify_token tests/test_mobile.py::test_verify_invalid_token_returns_none -v
```

Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/app/auth.py backend/tests/test_mobile.py
git commit -m "feat: add PyJWT and mobile token utilities"
```

---

## Task 3: Mobile Pydantic schemas

**Files:**
- Create: `backend/app/schemas/mobile.py`

No tests needed — schemas are validated by usage in later tasks.

- [ ] **Step 1: Create `backend/app/schemas/mobile.py`**

```python
from __future__ import annotations

from pydantic import BaseModel


# --- Auth ---

class MobileLoginRequest(BaseModel):
    player_id: int
    pin: str


class MobileLoginResponse(BaseModel):
    token: str
    player_id: int
    name: str


# --- Matches ---

class MobileLiveMatch(BaseModel):
    match_id: int
    round_type: str
    player1_id: int
    player1_name: str
    player2_id: int
    player2_name: str


class MobileUpcomingMatch(BaseModel):
    match_id: int
    round_type: str
    player1_name: str
    player2_name: str


class MobileCompletedMatch(BaseModel):
    match_id: int
    round_type: str
    player1_name: str
    player2_name: str
    winner_name: str


class MobileMatchesResponse(BaseModel):
    tournament_id: int | None
    live: list[MobileLiveMatch]
    upcoming: list[MobileUpcomingMatch]
    completed: list[MobileCompletedMatch]


# --- Standings ---

class MobileStandingEntry(BaseModel):
    rank: int
    player_id: int
    name: str
    wins: int
    losses: int
    avg_score: float
    reg_points: float
    bonus_points: int
    ko_qualified: bool


class MobileStandingsResponse(BaseModel):
    tournament_id: int | None
    phase: str
    entries: list[MobileStandingEntry]


# --- Bracket ---

class MobileBracketMatch(BaseModel):
    match_id: int | None
    player1_name: str | None
    player2_name: str | None
    winner_name: str | None
    is_completed: bool


class MobileBracketRound(BaseModel):
    label: str
    matches: list[MobileBracketMatch]


class MobileNebenrundeMatch(BaseModel):
    match_id: int
    round_number: int
    player1_name: str
    player2_name: str
    winner_name: str | None
    is_completed: bool


class MobileBracketResponse(BaseModel):
    tournament_id: int | None
    ko_rounds: list[MobileBracketRound]
    nebenrunde: list[MobileNebenrundeMatch]


# --- Stats ---

class MobilePlayerStats(BaseModel):
    player_id: int
    name: str
    avg_score: float
    wins: int
    losses: int
    bonus_points: int
    event_counts: dict[str, int]


class MobileStatsResponse(BaseModel):
    tournament_id: int | None
    players: list[MobilePlayerStats]
    totals: dict[str, int]


# --- Profile ---

class MobileProfileResponse(BaseModel):
    player_id: int
    name: str
    photo_url: str | None
    rank: int | None
    reg_points: float
    bonus_points: int
    wins: int
    losses: int
    avg_score: float
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/mobile.py
git commit -m "feat: add mobile Pydantic schemas"
```

---

## Task 4: Mobile router — auth endpoint

**Files:**
- Create: `backend/app/routers/mobile.py`
- Modify: `backend/tests/test_mobile.py`

- [ ] **Step 1: Write failing test** — add to `backend/tests/test_mobile.py`:

```python
# --- Auth endpoint tests ---

def test_mobile_login_success(client: TestClient):
    # Create player with PIN
    from app.models.player import Player
    from app.database import AsyncSessionLocal
    import asyncio

    async def seed():
        async with AsyncSessionLocal() as db:
            db.add(Player(name="Lars", pin="1234"))
            await db.commit()

    asyncio.get_event_loop().run_until_complete(seed())

    resp = client.post("/mobile/auth/login", json={"player_id": 1, "pin": "1234"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert body["name"] == "Lars"


def test_mobile_login_wrong_pin(client: TestClient):
    from app.models.player import Player
    from app.database import AsyncSessionLocal
    import asyncio

    async def seed():
        async with AsyncSessionLocal() as db:
            db.add(Player(name="Mike", pin="5678"))
            await db.commit()

    asyncio.get_event_loop().run_until_complete(seed())

    resp = client.post("/mobile/auth/login", json={"player_id": 1, "pin": "0000"})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run to confirm failure**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_login_success -v
```

Expected: 404 (route not found yet).

- [ ] **Step 3: Create `backend/app/routers/mobile.py`** with the auth endpoint and `_get_active_tournament` helper:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_mobile_token, verify_mobile_token
from app.database import get_db
from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.special_event import SpecialEvent
from app.models.tournament import Tournament, TournamentPlayer, TournamentStatus
from app.schemas.mobile import (
    MobileBracketMatch,
    MobileBracketResponse,
    MobileBracketRound,
    MobileCompletedMatch,
    MobileLiveMatch,
    MobileLoginRequest,
    MobileLoginResponse,
    MobileMatchesResponse,
    MobileNebenrundeMatch,
    MobilePlayerStats,
    MobileProfileResponse,
    MobileStandingEntry,
    MobileStandingsResponse,
    MobileStatsResponse,
    MobileUpcomingMatch,
)

router = APIRouter(prefix="/mobile", tags=["mobile"])
_bearer = HTTPBearer()


async def _get_active_tournament(db: AsyncSession) -> Tournament | None:
    result = await db.execute(
        select(Tournament)
        .where(Tournament.status.in_([TournamentStatus.vorrunde, TournamentStatus.ko]))
        .order_by(Tournament.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_current_player(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Player:
    payload = verify_mobile_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    player = await db.get(Player, int(payload["sub"]))
    if player is None:
        raise HTTPException(status_code=401, detail="Player not found")
    return player


@router.post("/auth/login", response_model=MobileLoginResponse)
async def mobile_login(body: MobileLoginRequest, db: AsyncSession = Depends(get_db)):
    player = await db.get(Player, body.player_id)
    if player is None or player.pin != body.pin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_mobile_token(player_id=player.id, name=player.name)
    return MobileLoginResponse(token=token, player_id=player.id, name=player.name)
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

Add import and `include_router` call. In `main.py`:

```python
from app.routers import matches, mobile, players, tournaments, ws
```

And after the existing `app.include_router(ws.router)` line:

```python
app.include_router(mobile.router)
```

Also change the CORS origins from `["http://localhost:5173", "http://127.0.0.1:5173"]` to `["*"]` to support the Cloudflare Tunnel URL.

- [ ] **Step 5: Run auth tests**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_login_success tests/test_mobile.py::test_mobile_login_wrong_pin -v
```

Expected: both PASS.

- [ ] **Step 6: Run full test suite to confirm no regressions**

```
cd backend
uv run python -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/mobile.py backend/app/main.py backend/tests/test_mobile.py
git commit -m "feat: add mobile auth endpoint and router"
```

---

## Task 5: GET /mobile/matches

**Files:**
- Modify: `backend/app/routers/mobile.py`
- Modify: `backend/tests/test_mobile.py`

- [ ] **Step 1: Write failing test** — add to `test_mobile.py`:

```python
def test_mobile_matches_no_active_tournament(client: TestClient):
    from app.auth import create_mobile_token
    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/matches", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_id"] is None
    assert body["live"] == []
    assert body["upcoming"] == []
    assert body["completed"] == []
```

- [ ] **Step 2: Run to confirm failure** (route doesn't exist yet)

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_matches_no_active_tournament -v
```

Expected: 404.

- [ ] **Step 3: Add the endpoint** to `backend/app/routers/mobile.py`:

```python
@router.get("/matches", response_model=MobileMatchesResponse)
async def mobile_matches(
    _player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    tournament = await _get_active_tournament(db)
    if tournament is None:
        return MobileMatchesResponse(tournament_id=None, live=[], upcoming=[], completed=[])

    # Load all players for name lookup
    players_result = await db.execute(select(Player))
    player_map: dict[int, str] = {p.id: p.name for p in players_result.scalars().all()}

    matches_result = await db.execute(
        select(Match)
        .where(Match.tournament_id == tournament.id)
        .order_by(Match.id)
    )
    matches = matches_result.scalars().all()

    live, upcoming, completed = [], [], []
    for m in matches:
        p1 = player_map.get(m.player1_id, "?")
        p2 = player_map.get(m.player2_id, "?")
        if m.status == MatchStatus.in_progress:
            live.append(MobileLiveMatch(
                match_id=m.id,
                round_type=m.round_type,
                player1_id=m.player1_id,
                player1_name=p1,
                player2_id=m.player2_id,
                player2_name=p2,
            ))
        elif m.status in (MatchStatus.pending, MatchStatus.bull_throw):
            upcoming.append(MobileUpcomingMatch(
                match_id=m.id,
                round_type=m.round_type,
                player1_name=p1,
                player2_name=p2,
            ))
        elif m.status == MatchStatus.finished and m.winner_id is not None:
            completed.append(MobileCompletedMatch(
                match_id=m.id,
                round_type=m.round_type,
                player1_name=p1,
                player2_name=p2,
                winner_name=player_map.get(m.winner_id, "?"),
            ))

    return MobileMatchesResponse(
        tournament_id=tournament.id,
        live=live,
        upcoming=upcoming,
        completed=completed,
    )
```

- [ ] **Step 4: Run test**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_matches_no_active_tournament -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/mobile.py backend/tests/test_mobile.py
git commit -m "feat: add GET /mobile/matches endpoint"
```

---

## Task 6: GET /mobile/standings

**Files:**
- Modify: `backend/app/routers/mobile.py`
- Modify: `backend/tests/test_mobile.py`

- [ ] **Step 1: Write failing test** — add to `test_mobile.py`:

```python
def test_mobile_standings_no_active_tournament(client: TestClient):
    from app.auth import create_mobile_token
    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/standings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_id"] is None
    assert body["entries"] == []
    assert body["phase"] == "none"
```

- [ ] **Step 2: Run to confirm failure**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_standings_no_active_tournament -v
```

Expected: 404.

- [ ] **Step 3: Add the endpoint** to `backend/app/routers/mobile.py`:

```python
@router.get("/standings", response_model=MobileStandingsResponse)
async def mobile_standings(
    _player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    tournament = await _get_active_tournament(db)
    if tournament is None:
        return MobileStandingsResponse(tournament_id=None, phase="none", entries=[])

    result = await db.execute(
        select(TournamentPlayer, Player)
        .join(Player, TournamentPlayer.player_id == Player.id)
        .where(TournamentPlayer.tournament_id == tournament.id)
        .order_by(TournamentPlayer.reg_points.desc())
    )
    rows = result.all()

    entries = []
    for rank, (tp, player) in enumerate(rows, start=1):
        # Count wins and losses from finished matches
        wins_result = await db.execute(
            select(Match).where(
                Match.tournament_id == tournament.id,
                Match.winner_id == player.id,
                Match.status == MatchStatus.finished,
            )
        )
        wins = len(wins_result.scalars().all())
        games_result = await db.execute(
            select(Match).where(
                Match.tournament_id == tournament.id,
                Match.status == MatchStatus.finished,
                (Match.player1_id == player.id) | (Match.player2_id == player.id),
            )
        )
        games = len(games_result.scalars().all())
        losses = games - wins

        entries.append(MobileStandingEntry(
            rank=rank,
            player_id=player.id,
            name=player.name,
            wins=wins,
            losses=losses,
            avg_score=tp.avg_score,
            reg_points=tp.reg_points,
            bonus_points=tp.bonus_points,
            ko_qualified=(rank <= 6),
        ))

    return MobileStandingsResponse(
        tournament_id=tournament.id,
        phase=tournament.status,
        entries=entries,
    )
```

- [ ] **Step 4: Run test**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_standings_no_active_tournament -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/mobile.py backend/tests/test_mobile.py
git commit -m "feat: add GET /mobile/standings endpoint"
```

---

## Task 7: GET /mobile/bracket

**Files:**
- Modify: `backend/app/routers/mobile.py`
- Modify: `backend/tests/test_mobile.py`

- [ ] **Step 1: Write failing test** — add to `test_mobile.py`:

```python
def test_mobile_bracket_no_active_tournament(client: TestClient):
    from app.auth import create_mobile_token
    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/bracket", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_id"] is None
    assert body["ko_rounds"] == []
    assert body["nebenrunde"] == []
```

- [ ] **Step 2: Run to confirm failure**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_bracket_no_active_tournament -v
```

Expected: 404.

- [ ] **Step 3: Add the endpoint** to `backend/app/routers/mobile.py`. Import `RoundType` from match models at the top of the file (add to existing imports):

```python
from app.models.match import Match, MatchStatus, RoundType
```

Then add:

```python
_KO_STAGE_LABELS = {"qf": "Viertelfinale", "sf": "Halbfinale", "final": "Finale", "third_place": "Spiel um Platz 3"}


@router.get("/bracket", response_model=MobileBracketResponse)
async def mobile_bracket(
    _player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    tournament = await _get_active_tournament(db)
    if tournament is None:
        return MobileBracketResponse(tournament_id=None, ko_rounds=[], nebenrunde=[])

    players_result = await db.execute(select(Player))
    player_map: dict[int, str] = {p.id: p.name for p in players_result.scalars().all()}

    ko_result = await db.execute(
        select(Match)
        .where(Match.tournament_id == tournament.id, Match.round_type == RoundType.ko)
        .order_by(Match.id)
    )
    ko_matches = ko_result.scalars().all()

    # Group KO matches by stage (qf=4 matches, sf=2, final=1, third_place=1)
    # Determine stage by position: first 4 → QF, next 2 → SF, next → 3rd, last → Final
    # In practice stages are stored as round_number; use count heuristic
    stages = [
        ("qf", "Viertelfinale", ko_matches[:4]),
        ("sf", "Halbfinale", ko_matches[4:6]),
        ("third_place", "Spiel um Platz 3", ko_matches[6:7]),
        ("final", "Finale", ko_matches[7:8]),
    ]
    ko_rounds = []
    for _stage, label, stage_matches in stages:
        if not stage_matches:
            continue
        ko_rounds.append(MobileBracketRound(
            label=label,
            matches=[
                MobileBracketMatch(
                    match_id=m.id,
                    player1_name=player_map.get(m.player1_id),
                    player2_name=player_map.get(m.player2_id),
                    winner_name=player_map.get(m.winner_id) if m.winner_id else None,
                    is_completed=(m.status == MatchStatus.finished),
                )
                for m in stage_matches
            ],
        ))

    lightning_result = await db.execute(
        select(Match)
        .where(Match.tournament_id == tournament.id, Match.round_type == RoundType.lightning)
        .order_by(Match.round_number, Match.id)
    )
    lightning_matches = lightning_result.scalars().all()

    nebenrunde = [
        MobileNebenrundeMatch(
            match_id=m.id,
            round_number=m.round_number,
            player1_name=player_map.get(m.player1_id, "?"),
            player2_name=player_map.get(m.player2_id, "?"),
            winner_name=player_map.get(m.winner_id) if m.winner_id else None,
            is_completed=(m.status == MatchStatus.finished),
        )
        for m in lightning_matches
    ]

    return MobileBracketResponse(
        tournament_id=tournament.id,
        ko_rounds=ko_rounds,
        nebenrunde=nebenrunde,
    )
```

- [ ] **Step 4: Run test**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_bracket_no_active_tournament -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/mobile.py backend/tests/test_mobile.py
git commit -m "feat: add GET /mobile/bracket endpoint"
```

---

## Task 8: GET /mobile/stats

**Files:**
- Modify: `backend/app/routers/mobile.py`
- Modify: `backend/tests/test_mobile.py`

- [ ] **Step 1: Write failing test** — add to `test_mobile.py`:

```python
def test_mobile_stats_no_active_tournament(client: TestClient):
    from app.auth import create_mobile_token
    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_id"] is None
    assert body["players"] == []
    assert body["totals"] == {}
```

- [ ] **Step 2: Run to confirm failure**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_stats_no_active_tournament -v
```

Expected: 404.

- [ ] **Step 3: Add the endpoint** to `backend/app/routers/mobile.py`. Verify `SpecialEvent` is imported (add to imports if missing):

```python
from app.models.special_event import SpecialEvent
```

Then add:

```python
@router.get("/stats", response_model=MobileStatsResponse)
async def mobile_stats(
    _player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    tournament = await _get_active_tournament(db)
    if tournament is None:
        return MobileStatsResponse(tournament_id=None, players=[], totals={})

    # Load tournament players
    tp_result = await db.execute(
        select(TournamentPlayer, Player)
        .join(Player, TournamentPlayer.player_id == Player.id)
        .where(TournamentPlayer.tournament_id == tournament.id)
    )
    tp_rows = tp_result.all()
    player_map: dict[int, str] = {player.id: player.name for _, player in tp_rows}
    tp_map: dict[int, TournamentPlayer] = {player.id: tp for tp, player in tp_rows}

    # Load all special events for this tournament's matches
    events_result = await db.execute(
        select(SpecialEvent)
        .join(Match, SpecialEvent.match_id == Match.id)
        .where(Match.tournament_id == tournament.id)
    )
    all_events = events_result.scalars().all()

    # Aggregate per player
    from collections import defaultdict
    player_events: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: dict[str, int] = defaultdict(int)
    for ev in all_events:
        player_events[ev.player_id][ev.event_type] += 1
        totals[ev.event_type] += 1

    # Count wins per player
    wins_result = await db.execute(
        select(Match.winner_id, Match.id)
        .where(Match.tournament_id == tournament.id, Match.status == MatchStatus.finished)
    )
    wins_per_player: dict[int, int] = defaultdict(int)
    for winner_id, _ in wins_result.all():
        if winner_id:
            wins_per_player[winner_id] += 1

    games_result = await db.execute(
        select(Match).where(
            Match.tournament_id == tournament.id,
            Match.status == MatchStatus.finished,
        )
    )
    games_per_player: dict[int, int] = defaultdict(int)
    for m in games_result.scalars().all():
        games_per_player[m.player1_id] += 1
        games_per_player[m.player2_id] += 1

    player_stats = []
    for pid, name in player_map.items():
        tp = tp_map[pid]
        wins = wins_per_player[pid]
        losses = games_per_player[pid] - wins
        player_stats.append(MobilePlayerStats(
            player_id=pid,
            name=name,
            avg_score=tp.avg_score,
            wins=wins,
            losses=losses,
            bonus_points=tp.bonus_points,
            event_counts=dict(player_events[pid]),
        ))

    return MobileStatsResponse(
        tournament_id=tournament.id,
        players=sorted(player_stats, key=lambda x: x.avg_score, reverse=True),
        totals=dict(totals),
    )
```

- [ ] **Step 4: Run test**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_stats_no_active_tournament -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/mobile.py backend/tests/test_mobile.py
git commit -m "feat: add GET /mobile/stats endpoint"
```

---

## Task 9: GET /mobile/me

**Files:**
- Modify: `backend/app/routers/mobile.py`
- Modify: `backend/tests/test_mobile.py`

- [ ] **Step 1: Write failing test** — add to `test_mobile.py`:

```python
def test_mobile_me_returns_player_data(client: TestClient):
    from app.models.player import Player
    from app.database import AsyncSessionLocal
    from app.auth import create_mobile_token
    import asyncio

    async def seed():
        async with AsyncSessionLocal() as db:
            db.add(Player(name="Lars", pin="1234"))
            await db.commit()

    asyncio.get_event_loop().run_until_complete(seed())

    token = create_mobile_token(player_id=1, name="Lars")
    resp = client.get("/mobile/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Lars"
    assert body["player_id"] == 1
    assert body["rank"] is None  # no active tournament
```

- [ ] **Step 2: Run to confirm failure**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_me_returns_player_data -v
```

Expected: 404.

- [ ] **Step 3: Add the endpoint** to `backend/app/routers/mobile.py`:

```python
@router.get("/me", response_model=MobileProfileResponse)
async def mobile_me(
    current_player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    from app.main import API_BASE  # avoid circular; use relative URL instead
    photo_url = (
        f"/static/{current_player.photo_path}" if current_player.photo_path else None
    )

    tournament = await _get_active_tournament(db)
    rank = None
    reg_points = 0.0
    bonus_points = 0
    wins = 0
    losses = 0
    avg_score = 0.0

    if tournament:
        tp_result = await db.execute(
            select(TournamentPlayer, Player)
            .join(Player, TournamentPlayer.player_id == Player.id)
            .where(TournamentPlayer.tournament_id == tournament.id)
            .order_by(TournamentPlayer.reg_points.desc())
        )
        rows = tp_result.all()
        for pos, (tp, player) in enumerate(rows, start=1):
            if player.id == current_player.id:
                rank = pos
                reg_points = tp.reg_points
                bonus_points = tp.bonus_points
                avg_score = tp.avg_score
                break

        wins_result = await db.execute(
            select(Match).where(
                Match.tournament_id == tournament.id,
                Match.winner_id == current_player.id,
                Match.status == MatchStatus.finished,
            )
        )
        wins = len(wins_result.scalars().all())
        games_result = await db.execute(
            select(Match).where(
                Match.tournament_id == tournament.id,
                Match.status == MatchStatus.finished,
                (Match.player1_id == current_player.id) | (Match.player2_id == current_player.id),
            )
        )
        losses = len(games_result.scalars().all()) - wins

    return MobileProfileResponse(
        player_id=current_player.id,
        name=current_player.name,
        photo_url=photo_url,
        rank=rank,
        reg_points=reg_points,
        bonus_points=bonus_points,
        wins=wins,
        losses=losses,
        avg_score=avg_score,
    )
```

**Note:** The `photo_url` is a relative path (e.g. `/static/Lars.jpg`). The frontend builds the full URL using `API_BASE + photo_url`.

- [ ] **Step 4: Run test**

```
cd backend
uv run python -m pytest tests/test_mobile.py::test_mobile_me_returns_player_data -v
```

Expected: PASS.

- [ ] **Step 5: Run full backend test suite**

```
cd backend
uv run python -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/mobile.py backend/tests/test_mobile.py
git commit -m "feat: add GET /mobile/me endpoint"
```

---

## Task 10: Mobile types + API client additions (frontend)

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/mobile/mobileAuth.ts`
- Create: `frontend/src/__tests__/mobile/mobileAuth.test.ts`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/mobileAuth.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { getToken, setToken, clearToken, isLoggedIn } from '../../mobile/mobileAuth'

describe('mobileAuth', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('isLoggedIn returns false when no token stored', () => {
    expect(isLoggedIn()).toBe(false)
  })

  it('setToken + getToken round-trips the token', () => {
    setToken('abc123')
    expect(getToken()).toBe('abc123')
  })

  it('isLoggedIn returns true after setToken', () => {
    setToken('abc123')
    expect(isLoggedIn()).toBe(true)
  })

  it('clearToken removes the token', () => {
    setToken('abc123')
    clearToken()
    expect(getToken()).toBeNull()
    expect(isLoggedIn()).toBe(false)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/mobileAuth.test.ts
```

Expected: module not found error.

- [ ] **Step 3: Create `frontend/src/mobile/mobileAuth.ts`**

```typescript
const TOKEN_KEY = 'mobile_token'
const PLAYER_ID_KEY = 'mobile_player_id'

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY)

export const setToken = (token: string, playerId?: number): void => {
  localStorage.setItem(TOKEN_KEY, token)
  if (playerId !== undefined) localStorage.setItem(PLAYER_ID_KEY, String(playerId))
}

export const clearToken = (): void => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(PLAYER_ID_KEY)
}

export const isLoggedIn = (): boolean => getToken() !== null

export const getStoredPlayerId = (): number | null => {
  const v = localStorage.getItem(PLAYER_ID_KEY)
  return v !== null ? parseInt(v, 10) : null
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```
cd frontend
npx vitest run src/__tests__/mobile/mobileAuth.test.ts
```

Expected: all 4 PASS.

- [ ] **Step 5: Add mobile TypeScript types** to `frontend/src/api/types.ts` — append at the end:

```typescript
// ---------------------------------------------------------------------------
// Mobile API types
// ---------------------------------------------------------------------------

export interface MobileLoginResponse {
  token: string
  player_id: number
  name: string
}

export interface MobileLiveMatch {
  match_id: number
  round_type: RoundType
  player1_id: number
  player1_name: string
  player2_id: number
  player2_name: string
}

export interface MobileUpcomingMatch {
  match_id: number
  round_type: RoundType
  player1_name: string
  player2_name: string
}

export interface MobileCompletedMatch {
  match_id: number
  round_type: RoundType
  player1_name: string
  player2_name: string
  winner_name: string
}

export interface MobileMatchesResponse {
  tournament_id: number | null
  live: MobileLiveMatch[]
  upcoming: MobileUpcomingMatch[]
  completed: MobileCompletedMatch[]
}

export interface MobileStandingEntry {
  rank: number
  player_id: number
  name: string
  wins: number
  losses: number
  avg_score: number
  reg_points: number
  bonus_points: number
  ko_qualified: boolean
}

export interface MobileStandingsResponse {
  tournament_id: number | null
  phase: string
  entries: MobileStandingEntry[]
}

export interface MobileBracketMatch {
  match_id: number | null
  player1_name: string | null
  player2_name: string | null
  winner_name: string | null
  is_completed: boolean
}

export interface MobileBracketRound {
  label: string
  matches: MobileBracketMatch[]
}

export interface MobileNebenrundeMatch {
  match_id: number
  round_number: number
  player1_name: string
  player2_name: string
  winner_name: string | null
  is_completed: boolean
}

export interface MobileBracketResponse {
  tournament_id: number | null
  ko_rounds: MobileBracketRound[]
  nebenrunde: MobileNebenrundeMatch[]
}

export interface MobilePlayerStats {
  player_id: number
  name: string
  avg_score: number
  wins: number
  losses: number
  bonus_points: number
  event_counts: Record<string, number>
}

export interface MobileStatsResponse {
  tournament_id: number | null
  players: MobilePlayerStats[]
  totals: Record<string, number>
}

export interface MobileProfileResponse {
  player_id: number
  name: string
  photo_url: string | null
  rank: number | null
  reg_points: number
  bonus_points: number
  wins: number
  losses: number
  avg_score: number
}
```

- [ ] **Step 6: Add mobile API functions** to `frontend/src/api/client.ts`

First add `apiGetAuth` and `apiPostAuth` private helpers (after the existing `apiPost` function):

```typescript
async function apiGetAuth<T>(path: string): Promise<T> {
  const token = localStorage.getItem('mobile_token')
  const response = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

async function apiPostAuth<T, B = unknown>(path: string, body?: B): Promise<T> {
  const token = localStorage.getItem('mobile_token')
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}
```

Then add the import at the top of client.ts (add to the existing import from `./types`):

```typescript
import type {
  // ... existing imports ...
  MobileLoginResponse,
  MobileMatchesResponse,
  MobileStandingsResponse,
  MobileBracketResponse,
  MobileStatsResponse,
  MobileProfileResponse,
} from './types'
```

And add mobile API functions at the end of client.ts:

```typescript
// ---------------------------------------------------------------------------
// Mobile endpoints
// ---------------------------------------------------------------------------

export const mobileLogin = (playerId: number, pin: string): Promise<MobileLoginResponse> =>
  apiPostAuth<MobileLoginResponse, { player_id: number; pin: string }>(
    '/mobile/auth/login',
    { player_id: playerId, pin },
  )

export const getMobileMatches = (): Promise<MobileMatchesResponse> =>
  apiGetAuth<MobileMatchesResponse>('/mobile/matches')

export const getMobileStandings = (): Promise<MobileStandingsResponse> =>
  apiGetAuth<MobileStandingsResponse>('/mobile/standings')

export const getMobileBracket = (): Promise<MobileBracketResponse> =>
  apiGetAuth<MobileBracketResponse>('/mobile/bracket')

export const getMobileStats = (): Promise<MobileStatsResponse> =>
  apiGetAuth<MobileStatsResponse>('/mobile/stats')

export const getMobileMe = (): Promise<MobileProfileResponse> =>
  apiGetAuth<MobileProfileResponse>('/mobile/me')
```

- [ ] **Step 7: Run full frontend test suite to confirm no regressions**

```
cd frontend
npm run test:run
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/mobile/mobileAuth.ts frontend/src/__tests__/mobile/mobileAuth.test.ts frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat: add mobile auth utilities and API client functions"
```

---

## Task 11: MobileLayout + MobileGuard + routing + .gitignore

**Files:**
- Create: `frontend/src/mobile/MobileLayout.tsx`
- Create: `frontend/src/mobile/MobileGuard.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `.gitignore`
- Create: `frontend/src/__tests__/mobile/MobileGuard.test.tsx`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/MobileGuard.test.tsx`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import MobileGuard from '../../mobile/MobileGuard'

describe('MobileGuard', () => {
  beforeEach(() => localStorage.clear())

  it('redirects to /mobile/login when not logged in', () => {
    render(
      <MemoryRouter initialEntries={['/mobile']}>
        <Routes>
          <Route path="/mobile/login" element={<div>Login Page</div>} />
          <Route path="/mobile" element={<MobileGuard />}>
            <Route index element={<div>Protected</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Login Page')).toBeTruthy()
  })

  it('renders children when logged in', () => {
    localStorage.setItem('mobile_token', 'valid-token')
    render(
      <MemoryRouter initialEntries={['/mobile']}>
        <Routes>
          <Route path="/mobile/login" element={<div>Login Page</div>} />
          <Route path="/mobile" element={<MobileGuard />}>
            <Route index element={<div>Protected</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Protected')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/MobileGuard.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Create `frontend/src/mobile/MobileGuard.tsx`**

```typescript
import { Navigate, Outlet } from 'react-router-dom'
import { isLoggedIn } from './mobileAuth'

export default function MobileGuard() {
  if (!isLoggedIn()) return <Navigate to="/mobile/login" replace />
  return <Outlet />
}
```

- [ ] **Step 4: Run guard tests**

```
cd frontend
npx vitest run src/__tests__/mobile/MobileGuard.test.tsx
```

Expected: both PASS.

- [ ] **Step 5: Create `frontend/src/mobile/MobileLayout.tsx`**

```typescript
import { Outlet, useNavigate } from 'react-router-dom'

export default function MobileLayout() {
  const navigate = useNavigate()
  return (
    <div style={{ minHeight: '100vh', background: '#0f0f1a', color: '#fff', fontFamily: 'sans-serif' }}>
      <header
        style={{
          background: '#1a1a2e',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          borderBottom: '1px solid #222',
        }}
      >
        <span
          onClick={() => navigate('/mobile')}
          style={{ cursor: 'pointer', fontSize: 20 }}
          aria-label="Home"
        >
          🎯
        </span>
        <span style={{ fontWeight: 'bold', fontSize: 16 }}>Backsberger Open</span>
      </header>
      <main style={{ padding: 16 }}>
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 6: Add `/mobile/*` routes** to `frontend/src/App.tsx`

Add the necessary imports at the top of App.tsx:

```typescript
import MobileLayout from './mobile/MobileLayout'
import MobileGuard from './mobile/MobileGuard'
import LoginScreen from './mobile/screens/LoginScreen'
import MobileHomeScreen from './mobile/screens/HomeScreen'
import SpielePage from './mobile/screens/SpielePage'
import VorrundeSeite from './mobile/screens/VorrundeSeite'
import BracketPage from './mobile/screens/BracketPage'
import StatisticsPage from './mobile/screens/StatisticsPage'
import ProfilPage from './mobile/screens/ProfilPage'
```

Add a new route entry inside `createBrowserRouter([...])`, after the last existing entry:

```typescript
{
  path: '/mobile',
  element: <MobileLayout />,
  children: [
    { path: 'login', element: <LoginScreen /> },
    {
      element: <MobileGuard />,
      children: [
        { index: true, element: <MobileHomeScreen /> },
        { path: 'spiele', element: <SpielePage /> },
        { path: 'vorrunde', element: <VorrundeSeite /> },
        { path: 'bracket', element: <BracketPage /> },
        { path: 'statistiken', element: <StatisticsPage /> },
        { path: 'profil', element: <ProfilPage /> },
      ],
    },
  ],
},
```

**Note:** The screen components will be created in Tasks 12–18. TypeScript will error until they exist — leave the import/route structure in place and create stub components in the next step to unblock compilation.

- [ ] **Step 7: Create placeholder stubs** for each mobile screen (one-liner files) so TypeScript compiles. Create each file with just a default export placeholder — these will be replaced in Tasks 12–18:

`frontend/src/mobile/screens/LoginScreen.tsx`:
```typescript
export default function LoginScreen() { return <div>Login</div> }
```

`frontend/src/mobile/screens/HomeScreen.tsx`:
```typescript
export default function MobileHomeScreen() { return <div>Home</div> }
```

`frontend/src/mobile/screens/SpielePage.tsx`:
```typescript
export default function SpielePage() { return <div>Spiele</div> }
```

`frontend/src/mobile/screens/VorrundeSeite.tsx`:
```typescript
export default function VorrundeSeite() { return <div>Vorrunde</div> }
```

`frontend/src/mobile/screens/BracketPage.tsx`:
```typescript
export default function BracketPage() { return <div>Bracket</div> }
```

`frontend/src/mobile/screens/StatisticsPage.tsx`:
```typescript
export default function StatisticsPage() { return <div>Statistiken</div> }
```

`frontend/src/mobile/screens/ProfilPage.tsx`:
```typescript
export default function ProfilPage() { return <div>Profil</div> }
```

- [ ] **Step 8: Verify TypeScript compiles**

```
cd frontend
npm run build 2>&1 | head -30
```

Expected: no TypeScript errors (build may warn about unused vars, that's OK).

- [ ] **Step 9: Add `.superpowers/` to `.gitignore`**

Open `.gitignore` at the repo root and add at the end:

```
.superpowers/
```

- [ ] **Step 10: Commit**

```bash
git add frontend/src/mobile/ frontend/src/App.tsx .gitignore
git commit -m "feat: add MobileLayout, MobileGuard, routing, and screen stubs"
```

---

## Task 12: LoginScreen

**Files:**
- Replace: `frontend/src/mobile/screens/LoginScreen.tsx`
- Create: `frontend/src/__tests__/mobile/LoginScreen.test.tsx`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/LoginScreen.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginScreen from '../../mobile/screens/LoginScreen'

vi.mock('../../api/client', () => ({
  getPlayers: vi.fn().mockResolvedValue([
    { id: 1, name: 'Lars', photo_path: null, music_path: null, championship_count: 3 },
    { id: 2, name: 'Mike', photo_path: null, music_path: null, championship_count: 1 },
  ]),
  mobileLogin: vi.fn(),
}))

describe('LoginScreen', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders name dropdown and PIN boxes', async () => {
    render(<MemoryRouter><LoginScreen /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getByRole('combobox')).toBeTruthy()
    expect(screen.getByRole('button', { name: /anmelden/i })).toBeTruthy()
  })

  it('shows error on wrong PIN', async () => {
    const { mobileLogin } = await import('../../api/client')
    vi.mocked(mobileLogin).mockRejectedValue(new Error('Invalid credentials'))
    render(<MemoryRouter><LoginScreen /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: /anmelden/i }))
    await waitFor(() => screen.getByText(/ungültig|invalid/i))
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/LoginScreen.test.tsx
```

Expected: test fails (stub renders only `<div>Login</div>`).

- [ ] **Step 3: Replace the stub** with the full `frontend/src/mobile/screens/LoginScreen.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPlayers, mobileLogin } from '../../api/client'
import type { Player } from '../../api/types'
import { setToken } from '../mobileAuth'

export default function LoginScreen() {
  const navigate = useNavigate()
  const [players, setPlayers] = useState<Player[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [pin, setPin] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getPlayers().then((ps) => {
      setPlayers(ps)
      if (ps.length > 0) setSelectedId(ps[0].id)
    })
  }, [])

  const handlePinInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value.replace(/\D/g, '').slice(0, 4)
    setPin(v)
  }

  const handleSubmit = async () => {
    if (!selectedId || pin.length !== 4) return
    setLoading(true)
    setError(null)
    try {
      const resp = await mobileLogin(selectedId, pin)
      setToken(resp.token, resp.player_id)
      navigate('/mobile')
    } catch {
      setError('Ungültige PIN. Bitte nochmal versuchen.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 320, margin: '60px auto', textAlign: 'center' }}>
      <div style={{ fontSize: 40, marginBottom: 8 }}>🎯</div>
      <h2 style={{ marginBottom: 4 }}>Backsberger Open</h2>
      <p style={{ color: '#888', marginBottom: 24 }}>Wer bist du?</p>

      <div style={{ marginBottom: 16, textAlign: 'left' }}>
        <label style={{ color: '#888', fontSize: 12, display: 'block', marginBottom: 4 }}>NAME</label>
        <select
          value={selectedId ?? ''}
          onChange={(e) => setSelectedId(Number(e.target.value))}
          style={{ width: '100%', padding: '10px', background: '#1e3a5f', color: '#4fc3f7', border: 'none', borderRadius: 6, fontSize: 14 }}
        >
          {players.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: 20, textAlign: 'left' }}>
        <label style={{ color: '#888', fontSize: 12, display: 'block', marginBottom: 4 }}>PIN</label>
        <input
          type="password"
          inputMode="numeric"
          maxLength={4}
          value={pin}
          onChange={handlePinInput}
          placeholder="••••"
          style={{ width: '100%', padding: '10px', background: '#222', color: '#fff', border: 'none', borderRadius: 6, fontSize: 20, textAlign: 'center', boxSizing: 'border-box' }}
        />
      </div>

      {error && <p style={{ color: '#f44336', marginBottom: 12 }}>{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={loading || pin.length !== 4 || !selectedId}
        style={{ width: '100%', padding: 12, background: '#1e3a5f', color: '#4fc3f7', border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 'bold', cursor: 'pointer' }}
        aria-label="Anmelden"
      >
        {loading ? 'Lädt…' : 'Anmelden'}
      </button>
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```
cd frontend
npx vitest run src/__tests__/mobile/LoginScreen.test.tsx
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/mobile/screens/LoginScreen.tsx frontend/src/__tests__/mobile/LoginScreen.test.tsx
git commit -m "feat: implement LoginScreen"
```

---

## Task 13: Mobile HomeScreen

**Files:**
- Replace: `frontend/src/mobile/screens/HomeScreen.tsx`
- Create: `frontend/src/__tests__/mobile/HomeScreen.test.tsx`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/HomeScreen.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import MobileHomeScreen from '../../mobile/screens/HomeScreen'

vi.mock('../../api/client', () => ({
  getMobileMatches: vi.fn().mockResolvedValue({
    tournament_id: 1,
    live: [{ match_id: 1, round_type: 'vorrunde', player1_id: 1, player1_name: 'Lars', player2_id: 2, player2_name: 'Mike' }],
    upcoming: [],
    completed: [],
  }),
}))

describe('MobileHomeScreen', () => {
  it('renders all 6 tiles', async () => {
    render(<MemoryRouter><MobileHomeScreen /></MemoryRouter>)
    await waitFor(() => screen.getByText('Spiele'))
    expect(screen.getByText('Vorrunde')).toBeTruthy()
    expect(screen.getByText('KO-Bracket')).toBeTruthy()
    expect(screen.getByText('Statistiken')).toBeTruthy()
    expect(screen.getByText('Profil')).toBeTruthy()
    expect(screen.getByText('Wetten')).toBeTruthy()
  })

  it('Wetten tile is not a navigation link', async () => {
    render(<MemoryRouter><MobileHomeScreen /></MemoryRouter>)
    await waitFor(() => screen.getByText('Wetten'))
    const wettenTile = screen.getByText('Wetten').closest('div')
    expect(wettenTile).toBeTruthy()
    // Should not be a link (disabled tile)
    expect(wettenTile?.tagName).not.toBe('A')
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/HomeScreen.test.tsx
```

- [ ] **Step 3: Replace stub** with `frontend/src/mobile/screens/HomeScreen.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getMobileMatches } from '../../api/client'

const tileStyle = (active: boolean): React.CSSProperties => ({
  background: active ? '#1e3a5f' : '#2a2a2a',
  borderRadius: 8,
  padding: 16,
  textAlign: 'center',
  color: active ? '#4fc3f7' : '#555',
  cursor: active ? 'pointer' : 'default',
  border: active ? 'none' : '1px dashed #444',
  userSelect: 'none',
})

export default function MobileHomeScreen() {
  const navigate = useNavigate()
  const [liveCount, setLiveCount] = useState<number | null>(null)

  useEffect(() => {
    getMobileMatches()
      .then((r) => setLiveCount(r.live.length))
      .catch(() => setLiveCount(0))
  }, [])

  const tiles = [
    { icon: '⚡', label: 'Spiele', sub: liveCount !== null ? `${liveCount} Match${liveCount !== 1 ? 'es' : ''} aktiv` : '…', path: '/mobile/spiele', active: true },
    { icon: '📊', label: 'Vorrunde', sub: 'Tabelle', path: '/mobile/vorrunde', active: true },
    { icon: '🏆', label: 'KO-Bracket', sub: 'Bracket', path: '/mobile/bracket', active: true },
    { icon: '📈', label: 'Statistiken', sub: 'Gesamt + Spieler', path: '/mobile/statistiken', active: true },
    { icon: '👤', label: 'Profil', sub: 'Foto + Stats', path: '/mobile/profil', active: true },
    { icon: '¥$', label: 'Wetten', sub: 'Coming soon', path: null, active: false },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 400, margin: '0 auto' }}>
      {tiles.map((tile) => (
        <div
          key={tile.label}
          style={tileStyle(tile.active)}
          onClick={() => tile.path && navigate(tile.path)}
        >
          <div style={{ fontSize: 24, marginBottom: 6 }}>{tile.icon}</div>
          <div style={{ fontWeight: 'bold', fontSize: 13 }}>{tile.label}</div>
          <div style={{ fontSize: 11, marginTop: 2, opacity: 0.8 }}>{tile.sub}</div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```
cd frontend
npx vitest run src/__tests__/mobile/HomeScreen.test.tsx
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/mobile/screens/HomeScreen.tsx frontend/src/__tests__/mobile/HomeScreen.test.tsx
git commit -m "feat: implement mobile HomeScreen with 6 tiles"
```

---

## Task 14: SpielePage

**Files:**
- Replace: `frontend/src/mobile/screens/SpielePage.tsx`
- Create: `frontend/src/__tests__/mobile/SpielePage.test.tsx`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/SpielePage.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SpielePage from '../../mobile/screens/SpielePage'

vi.mock('../../api/client', () => ({
  getMobileMatches: vi.fn().mockResolvedValue({
    tournament_id: 1,
    live: [{ match_id: 5, round_type: 'vorrunde', player1_id: 1, player1_name: 'Lars', player2_id: 2, player2_name: 'Mike' }],
    upcoming: [{ match_id: 6, round_type: 'vorrunde', player1_name: 'Jonas', player2_name: 'Lena' }],
    completed: [{ match_id: 3, round_type: 'vorrunde', player1_name: 'Philipp', player2_name: 'Henrik', winner_name: 'Philipp' }],
  }),
}))

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn().mockReturnValue({ lastEvent: null, isConnected: false }),
}))

describe('SpielePage', () => {
  it('shows live match players', async () => {
    render(<MemoryRouter><SpielePage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getByText('Mike')).toBeTruthy()
  })

  it('shows upcoming match', async () => {
    render(<MemoryRouter><SpielePage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Jonas'))
    expect(screen.getByText(/Lena/)).toBeTruthy()
  })

  it('shows completed match with winner', async () => {
    render(<MemoryRouter><SpielePage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Philipp'))
    expect(screen.getByText(/Philipp/)).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/SpielePage.test.tsx
```

- [ ] **Step 3: Replace stub** with `frontend/src/mobile/screens/SpielePage.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { getMobileMatches } from '../../api/client'
import type { MobileMatchesResponse, MobileLiveMatch } from '../../api/types'
import { useWebSocket } from '../../hooks/useWebSocket'

function LiveMatchCard({ match, tournamentId }: { match: MobileLiveMatch; tournamentId: number }) {
  const { lastEvent } = useWebSocket('match', match.match_id)
  const [remaining, setRemaining] = useState<{ p1: number; p2: number } | null>(null)
  const [visitInfo, setVisitInfo] = useState<string>('')

  useEffect(() => {
    if (!lastEvent) return
    if (lastEvent.type === 'score_update') {
      const d = lastEvent.data as { remaining_p1?: number; remaining_p2?: number; visit_number?: number }
      if (d.remaining_p1 !== undefined) setRemaining({ p1: d.remaining_p1, p2: d.remaining_p2 ?? 0 })
      if (d.visit_number !== undefined) setVisitInfo(`Visit ${d.visit_number}`)
    }
  }, [lastEvent])

  const _ = tournamentId // used by parent for WebSocket context

  return (
    <div style={{ background: '#1e2a1e', borderRadius: 8, padding: 12, border: '1px solid #2a4a2a', marginBottom: 12 }}>
      <div style={{ color: '#ff7043', fontSize: 11, fontWeight: 'bold', marginBottom: 8 }}>● LIVE</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ color: '#fff', fontWeight: 'bold' }}>{match.player1_name}</div>
          <div style={{ color: '#4fc3f7', fontSize: 28, fontWeight: 'bold' }}>{remaining?.p1 ?? '—'}</div>
        </div>
        <div style={{ color: '#555' }}>vs</div>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ color: '#fff', fontWeight: 'bold' }}>{match.player2_name}</div>
          <div style={{ color: '#4fc3f7', fontSize: 28, fontWeight: 'bold' }}>{remaining?.p2 ?? '—'}</div>
        </div>
      </div>
      {visitInfo && <div style={{ textAlign: 'center', color: '#81c784', fontSize: 11, marginTop: 6 }}>{visitInfo}</div>}
    </div>
  )
}

export default function SpielePage() {
  const [data, setData] = useState<MobileMatchesResponse | null>(null)

  useEffect(() => {
    getMobileMatches().then(setData)
  }, [])

  if (!data) return <p style={{ color: '#888' }}>Lädt…</p>

  return (
    <div style={{ maxWidth: 400, margin: '0 auto' }}>
      {data.live.length > 0 ? (
        data.live.map((m) => (
          <LiveMatchCard key={m.match_id} match={m} tournamentId={data.tournament_id ?? 0} />
        ))
      ) : (
        <p style={{ color: '#888', textAlign: 'center' }}>Kein Match gerade aktiv.</p>
      )}

      {data.upcoming.length > 0 && (
        <>
          <div style={{ color: '#888', fontSize: 11, fontWeight: 'bold', letterSpacing: 1, marginTop: 16, marginBottom: 6 }}>NÄCHSTE MATCHES</div>
          {data.upcoming.map((m) => (
            <div key={m.match_id} style={{ background: '#1a1a2e', borderRadius: 6, padding: '8px 12px', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#aaa' }}>{m.player1_name} vs {m.player2_name}</span>
              <span style={{ color: '#555', fontSize: 11 }}>{m.round_type}</span>
            </div>
          ))}
        </>
      )}

      {data.completed.length > 0 && (
        <>
          <div style={{ color: '#888', fontSize: 11, fontWeight: 'bold', letterSpacing: 1, marginTop: 16, marginBottom: 6 }}>ABGESCHLOSSEN</div>
          {data.completed.map((m) => (
            <div key={m.match_id} style={{ background: '#1a1a2e', borderRadius: 6, padding: '8px 12px', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#666' }}>{m.player1_name} vs {m.player2_name}</span>
              <span style={{ color: '#81c784', fontWeight: 'bold' }}>{m.winner_name}</span>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```
cd frontend
npx vitest run src/__tests__/mobile/SpielePage.test.tsx
```

Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/mobile/screens/SpielePage.tsx frontend/src/__tests__/mobile/SpielePage.test.tsx
git commit -m "feat: implement SpielePage with live WebSocket score"
```

---

## Task 15: VorrundeSeite

**Files:**
- Replace: `frontend/src/mobile/screens/VorrundeSeite.tsx`
- Create: `frontend/src/__tests__/mobile/VorrundeSeite.test.tsx`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/VorrundeSeite.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import VorrundeSeite from '../../mobile/screens/VorrundeSeite'

vi.mock('../../api/client', () => ({
  getMobileStandings: vi.fn().mockResolvedValue({
    tournament_id: 1,
    phase: 'vorrunde',
    entries: [
      { rank: 1, player_id: 1, name: 'Lars', wins: 4, losses: 1, avg_score: 72.4, reg_points: 4.72, bonus_points: 430, ko_qualified: true },
      { rank: 7, player_id: 7, name: 'Janni', wins: 1, losses: 4, avg_score: 41.0, reg_points: 1.41, bonus_points: 10, ko_qualified: false },
    ],
  }),
}))

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn().mockReturnValue({ lastEvent: null, isConnected: false }),
}))

describe('VorrundeSeite', () => {
  it('renders standings table with player names', async () => {
    render(<MemoryRouter><VorrundeSeite /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getByText('Janni')).toBeTruthy()
  })

  it('shows W/L columns', async () => {
    render(<MemoryRouter><VorrundeSeite /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getAllByText(/4/).length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/VorrundeSeite.test.tsx
```

- [ ] **Step 3: Replace stub** with `frontend/src/mobile/screens/VorrundeSeite.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { getMobileStandings } from '../../api/client'
import type { MobileStandingsResponse } from '../../api/types'
import { useWebSocket } from '../../hooks/useWebSocket'

export default function VorrundeSeite() {
  const [data, setData] = useState<MobileStandingsResponse | null>(null)
  const { lastEvent } = useWebSocket('tournament', data?.tournament_id ?? 0)

  useEffect(() => {
    getMobileStandings().then(setData)
  }, [])

  useEffect(() => {
    if (lastEvent?.type === 'standings_update') {
      getMobileStandings().then(setData)
    }
  }, [lastEvent])

  if (!data) return <p style={{ color: '#888' }}>Lädt…</p>

  return (
    <div style={{ maxWidth: 500, margin: '0 auto' }}>
      <h3 style={{ marginBottom: 12 }}>Vorrunde — Tabelle</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ color: '#666', borderBottom: '1px solid #333' }}>
              <th style={{ textAlign: 'left', padding: '4px 6px' }}>#</th>
              <th style={{ textAlign: 'left', padding: '4px 6px' }}>Name</th>
              <th style={{ textAlign: 'right', padding: '4px 6px' }}>W/L</th>
              <th style={{ textAlign: 'right', padding: '4px 6px' }}>Avg</th>
              <th style={{ textAlign: 'right', padding: '4px 6px' }}>Pkt</th>
              <th style={{ textAlign: 'right', padding: '4px 6px' }}>Bonus</th>
            </tr>
          </thead>
          <tbody>
            {data.entries.map((e) => (
              <tr
                key={e.player_id}
                style={{ borderBottom: '1px solid #222', background: e.ko_qualified ? '#1e3a1e' : 'transparent' }}
              >
                <td style={{ padding: '6px', color: e.ko_qualified ? '#81c784' : '#aaa', fontWeight: 'bold' }}>{e.rank}</td>
                <td style={{ padding: '6px', color: '#fff', fontWeight: e.ko_qualified ? 'bold' : 'normal' }}>{e.name}</td>
                <td style={{ padding: '6px', color: '#aaa', textAlign: 'right' }}>{e.wins}/{e.losses}</td>
                <td style={{ padding: '6px', color: '#aaa', textAlign: 'right' }}>{e.avg_score.toFixed(1)}</td>
                <td style={{ padding: '6px', color: '#4fc3f7', textAlign: 'right', fontWeight: 'bold' }}>{e.reg_points.toFixed(2)}</td>
                <td style={{ padding: '6px', color: '#ffb74d', textAlign: 'right' }}>+{e.bonus_points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ color: '#555', fontSize: 10, textAlign: 'center', marginTop: 8 }}>Grün = KO-qualifiziert</p>
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```
cd frontend
npx vitest run src/__tests__/mobile/VorrundeSeite.test.tsx
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/mobile/screens/VorrundeSeite.tsx frontend/src/__tests__/mobile/VorrundeSeite.test.tsx
git commit -m "feat: implement VorrundeSeite standings table"
```

---

## Task 16: BracketPage

**Files:**
- Replace: `frontend/src/mobile/screens/BracketPage.tsx`
- Create: `frontend/src/__tests__/mobile/BracketPage.test.tsx`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/BracketPage.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import BracketPage from '../../mobile/screens/BracketPage'

vi.mock('../../api/client', () => ({
  getMobileBracket: vi.fn().mockResolvedValue({
    tournament_id: 1,
    ko_rounds: [
      {
        label: 'Viertelfinale',
        matches: [
          { match_id: 10, player1_name: 'Lars', player2_name: 'Jonas', winner_name: 'Lars', is_completed: true },
        ],
      },
    ],
    nebenrunde: [
      { match_id: 20, round_number: 1, player1_name: 'Janni', player2_name: 'Elina', winner_name: null, is_completed: false },
    ],
  }),
}))

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn().mockReturnValue({ lastEvent: null, isConnected: false }),
}))

describe('BracketPage', () => {
  it('shows KO tab with Viertelfinale', async () => {
    render(<MemoryRouter><BracketPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Viertelfinale'))
    expect(screen.getByText('Lars')).toBeTruthy()
  })

  it('switches to Nebenrunde tab', async () => {
    render(<MemoryRouter><BracketPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Nebenrunde'))
    fireEvent.click(screen.getByText('Nebenrunde'))
    expect(screen.getByText('Janni')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/BracketPage.test.tsx
```

- [ ] **Step 3: Replace stub** with `frontend/src/mobile/screens/BracketPage.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { getMobileBracket } from '../../api/client'
import type { MobileBracketResponse } from '../../api/types'
import { useWebSocket } from '../../hooks/useWebSocket'

export default function BracketPage() {
  const [data, setData] = useState<MobileBracketResponse | null>(null)
  const [tab, setTab] = useState<'ko' | 'nebenrunde'>('ko')
  const { lastEvent } = useWebSocket('tournament', data?.tournament_id ?? 0)

  useEffect(() => {
    getMobileBracket().then(setData)
  }, [])

  useEffect(() => {
    if (lastEvent?.type === 'bracket_update') {
      getMobileBracket().then(setData)
    }
  }, [lastEvent])

  if (!data) return <p style={{ color: '#888' }}>Lädt…</p>

  const tabStyle = (active: boolean): React.CSSProperties => ({
    flex: 1,
    padding: '10px',
    textAlign: 'center',
    background: active ? '#1e3a5f' : '#1a1a2e',
    color: active ? '#4fc3f7' : '#666',
    fontWeight: active ? 'bold' : 'normal',
    cursor: 'pointer',
    borderBottom: active ? '2px solid #4fc3f7' : '2px solid transparent',
  })

  return (
    <div style={{ maxWidth: 400, margin: '0 auto' }}>
      <div style={{ display: 'flex', marginBottom: 16, borderBottom: '1px solid #333' }}>
        <div style={tabStyle(tab === 'ko')} onClick={() => setTab('ko')}>KO</div>
        <div style={tabStyle(tab === 'nebenrunde')} onClick={() => setTab('nebenrunde')}>Nebenrunde</div>
      </div>

      {tab === 'ko' && (
        <>
          {data.ko_rounds.map((round) => (
            <div key={round.label} style={{ marginBottom: 16 }}>
              <div style={{ color: '#888', fontSize: 11, letterSpacing: 1, marginBottom: 6 }}>{round.label.toUpperCase()}</div>
              {round.matches.map((m, i) => (
                <div
                  key={i}
                  style={{ background: m.is_completed ? '#1e3a1e' : '#1a1a2e', borderRadius: 6, padding: '8px 12px', marginBottom: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <span style={{ color: m.is_completed ? '#81c784' : '#aaa' }}>{m.player1_name ?? '?'}</span>
                  <span style={{ color: '#555', fontSize: 12 }}>{m.is_completed && m.winner_name ? `✓ ${m.winner_name}` : 'vs'}</span>
                  <span style={{ color: m.is_completed ? '#81c784' : '#aaa' }}>{m.player2_name ?? '?'}</span>
                </div>
              ))}
            </div>
          ))}
          {data.ko_rounds.length === 0 && <p style={{ color: '#555', textAlign: 'center' }}>Noch kein KO-Bracket.</p>}
        </>
      )}

      {tab === 'nebenrunde' && (
        <>
          {data.nebenrunde.length === 0 && <p style={{ color: '#555', textAlign: 'center' }}>Noch keine Nebenrunde.</p>}
          {data.nebenrunde.map((m) => (
            <div
              key={m.match_id}
              style={{ background: m.is_completed ? '#1e3a1e' : '#1a1a2e', borderRadius: 6, padding: '8px 12px', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}
            >
              <span style={{ color: '#aaa' }}>{m.player1_name} vs {m.player2_name}</span>
              <span style={{ color: '#81c784' }}>{m.winner_name ?? '—'}</span>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```
cd frontend
npx vitest run src/__tests__/mobile/BracketPage.test.tsx
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/mobile/screens/BracketPage.tsx frontend/src/__tests__/mobile/BracketPage.test.tsx
git commit -m "feat: implement BracketPage with KO and Nebenrunde tabs"
```

---

## Task 17: StatisticsPage

**Files:**
- Replace: `frontend/src/mobile/screens/StatisticsPage.tsx`
- Create: `frontend/src/__tests__/mobile/StatisticsPage.test.tsx`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/StatisticsPage.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import StatisticsPage from '../../mobile/screens/StatisticsPage'

vi.mock('../../api/client', () => ({
  getMobileStats: vi.fn().mockResolvedValue({
    tournament_id: 1,
    players: [
      { player_id: 1, name: 'Lars', avg_score: 72.4, wins: 4, losses: 1, bonus_points: 430, event_counts: { '180 geworfen': 2, 'Bulls Eye': 3 } },
      { player_id: 2, name: 'Mike', avg_score: 68.1, wins: 3, losses: 2, bonus_points: 210, event_counts: { 'Tripel 20': 5 } },
    ],
    totals: { '180 geworfen': 3, 'Bulls Eye': 4, 'Tripel 20': 12, 'Bounce': 2 },
  }),
}))

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn().mockReturnValue({ lastEvent: null, isConnected: false }),
}))

describe('StatisticsPage', () => {
  it('renders player names', async () => {
    render(<MemoryRouter><StatisticsPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getByText('Mike')).toBeTruthy()
  })

  it('shows total event counts', async () => {
    render(<MemoryRouter><StatisticsPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getByText('3×')).toBeTruthy()  // 180s total
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/StatisticsPage.test.tsx
```

- [ ] **Step 3: Replace stub** with `frontend/src/mobile/screens/StatisticsPage.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { getMobileStats } from '../../api/client'
import type { MobileStatsResponse, MobilePlayerStats } from '../../api/types'
import { useWebSocket } from '../../hooks/useWebSocket'

const HIGHLIGHT_EVENTS = ['180 geworfen', 'Bulls Eye', 'Tripel 20', 'Bounce']

export default function StatisticsPage() {
  const [data, setData] = useState<MobileStatsResponse | null>(null)
  const [selectedId, setSelectedId] = useState<number | 'all'>('all')
  const { lastEvent } = useWebSocket('tournament', data?.tournament_id ?? 0)

  useEffect(() => {
    getMobileStats().then(setData)
  }, [])

  useEffect(() => {
    if (lastEvent?.type === 'standings_update') getMobileStats().then(setData)
  }, [lastEvent])

  if (!data) return <p style={{ color: '#888' }}>Lädt…</p>

  const displayed: MobilePlayerStats[] =
    selectedId === 'all' ? data.players : data.players.filter((p) => p.player_id === selectedId)

  const maxAvg = Math.max(...data.players.map((p) => p.avg_score), 1)

  return (
    <div style={{ maxWidth: 400, margin: '0 auto' }}>
      <select
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value === 'all' ? 'all' : Number(e.target.value))}
        style={{ width: '100%', padding: '8px 10px', background: '#1e3a5f', color: '#4fc3f7', border: 'none', borderRadius: 6, marginBottom: 16, fontSize: 13 }}
      >
        <option value="all">Alle Spieler</option>
        {data.players.map((p) => (
          <option key={p.player_id} value={p.player_id}>{p.name}</option>
        ))}
      </select>

      <div style={{ color: '#888', fontSize: 11, letterSpacing: 1, marginBottom: 8 }}>TOP AVERAGES</div>
      {displayed.map((p) => (
        <div key={p.player_id} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span style={{ color: '#fff', width: 70, fontSize: 12 }}>{p.name}</span>
          <div style={{ flex: 1, background: '#222', borderRadius: 2, height: 8 }}>
            <div style={{ background: '#4fc3f7', width: `${(p.avg_score / maxAvg) * 100}%`, height: '100%', borderRadius: 2 }} />
          </div>
          <span style={{ color: '#4fc3f7', fontWeight: 'bold', width: 36, textAlign: 'right', fontSize: 12 }}>{p.avg_score.toFixed(1)}</span>
        </div>
      ))}

      <div style={{ color: '#888', fontSize: 11, letterSpacing: 1, margin: '16px 0 8px' }}>BESONDERE EREIGNISSE</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {HIGHLIGHT_EVENTS.map((ev) => {
          const count = selectedId === 'all'
            ? (data.totals[ev] ?? 0)
            : (displayed[0]?.event_counts[ev] ?? 0)
          return (
            <div key={ev} style={{ background: '#1a1a2e', borderRadius: 6, padding: '10px', textAlign: 'center' }}>
              <div style={{ color: '#888', fontSize: 10 }}>{ev}</div>
              <div style={{ color: '#fff', fontWeight: 'bold', marginTop: 4 }}>{count}×</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```
cd frontend
npx vitest run src/__tests__/mobile/StatisticsPage.test.tsx
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/mobile/screens/StatisticsPage.tsx frontend/src/__tests__/mobile/StatisticsPage.test.tsx
git commit -m "feat: implement StatisticsPage with averages and event highlights"
```

---

## Task 18: ProfilPage

**Files:**
- Replace: `frontend/src/mobile/screens/ProfilPage.tsx`
- Create: `frontend/src/__tests__/mobile/ProfilPage.test.tsx`

- [ ] **Step 1: Write failing test** — create `frontend/src/__tests__/mobile/ProfilPage.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ProfilPage from '../../mobile/screens/ProfilPage'

vi.mock('../../api/client', () => ({
  getMobileMe: vi.fn().mockResolvedValue({
    player_id: 1,
    name: 'Lars',
    photo_url: null,
    rank: 1,
    reg_points: 4.72,
    bonus_points: 430,
    wins: 4,
    losses: 1,
    avg_score: 72.4,
  }),
}))

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn().mockReturnValue({ lastEvent: null, isConnected: false }),
}))

describe('ProfilPage', () => {
  it('shows player name and rank', async () => {
    render(<MemoryRouter><ProfilPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getByText(/Platz 1/)).toBeTruthy()
  })

  it('shows Spielstärke section as coming soon', async () => {
    render(<MemoryRouter><ProfilPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getByText(/Coming soon/i)).toBeTruthy()
  })

  it('shows stats grid', async () => {
    render(<MemoryRouter><ProfilPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Lars'))
    expect(screen.getByText('72.4')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```
cd frontend
npx vitest run src/__tests__/mobile/ProfilPage.test.tsx
```

- [ ] **Step 3: Read `frontend/src/data/playerProfiles.json`** to understand the structure, then replace stub with `frontend/src/mobile/screens/ProfilPage.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { getMobileMe } from '../../api/client'
import type { MobileProfileResponse } from '../../api/types'
import { useWebSocket } from '../../hooks/useWebSocket'
import { API_BASE } from '../../api/client'
import playerProfiles from '../../data/playerProfiles.json'

interface PlayerProfile {
  nickname?: string
  funFact?: string
  bestPerformance?: string
}

function getProfile(name: string): PlayerProfile {
  return (playerProfiles as Record<string, PlayerProfile>)[name] ?? {}
}

export default function ProfilPage() {
  const [data, setData] = useState<MobileProfileResponse | null>(null)
  const { lastEvent } = useWebSocket('tournament', 0)

  useEffect(() => {
    getMobileMe().then(setData)
  }, [])

  useEffect(() => {
    if (lastEvent?.type === 'standings_update') getMobileMe().then(setData)
  }, [lastEvent])

  if (!data) return <p style={{ color: '#888' }}>Lädt…</p>

  const profile = getProfile(data.name)

  return (
    <div style={{ maxWidth: 360, margin: '0 auto' }}>
      {/* Photo + name */}
      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        {data.photo_url ? (
          <img
            src={`${API_BASE}${data.photo_url}`}
            alt={data.name}
            style={{ width: 80, height: 80, borderRadius: '50%', border: '2px solid #4fc3f7', objectFit: 'cover', marginBottom: 8 }}
          />
        ) : (
          <div style={{ width: 80, height: 80, borderRadius: '50%', background: '#1e3a5f', border: '2px solid #4fc3f7', margin: '0 auto 8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32 }}>👤</div>
        )}
        <div style={{ fontWeight: 'bold', fontSize: 18 }}>{data.name}</div>
        {profile.nickname && <div style={{ color: '#888', fontSize: 12 }}>"{profile.nickname}"</div>}
        {profile.funFact && <div style={{ color: '#555', fontSize: 11, fontStyle: 'italic', marginTop: 2 }}>"{profile.funFact}"</div>}
      </div>

      {/* Aktueller Stand */}
      <div style={{ background: '#1e3a1e', borderRadius: 8, padding: 12, textAlign: 'center', marginBottom: 16, border: '1px solid #2a4a2a' }}>
        <div style={{ color: '#888', fontSize: 11 }}>AKTUELLER STAND</div>
        <div style={{ color: '#81c784', fontSize: 24, fontWeight: 'bold' }}>
          {data.rank !== null ? `🥇 Platz ${data.rank}` : '—'}
        </div>
        <div style={{ color: '#4fc3f7', fontSize: 13 }}>{data.reg_points.toFixed(2)} Punkte</div>
      </div>

      {/* Spielstärke-Profil — Coming soon */}
      <div style={{ color: '#555', fontSize: 11, letterSpacing: 1, marginBottom: 6 }}>SPIELSTÄRKE-PROFIL</div>
      <div style={{ background: '#1e1e1e', borderRadius: 8, padding: 12, border: '1px dashed #444', marginBottom: 16, opacity: 0.7 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
          {[['σ normal', '—'], ['σ stark', '—']].map(([label, val]) => (
            <div key={label} style={{ background: '#2a2a2a', borderRadius: 5, padding: 8, textAlign: 'center' }}>
              <div style={{ color: '#555', fontSize: 10 }}>{label}</div>
              <div style={{ color: '#555', fontWeight: 'bold' }}>{val}</div>
            </div>
          ))}
        </div>
        <div style={{ background: '#2a2a2a', borderRadius: 5, padding: 8, textAlign: 'center' }}>
          <div style={{ color: '#555', fontSize: 10 }}>Starke Felder</div>
          <div style={{ color: '#555', fontSize: 10 }}>T20 · D16 · Bull · …</div>
        </div>
        <div style={{ textAlign: 'center', marginTop: 8, color: '#555', fontSize: 10 }}>Coming soon (Cycle 6)</div>
      </div>

      {/* Stats */}
      <div style={{ color: '#888', fontSize: 11, letterSpacing: 1, marginBottom: 6 }}>MEINE STATS</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        {[
          ['W/L', `${data.wins} / ${data.losses}`],
          ['Avg', data.avg_score.toFixed(1)],
          ['Bonus-Pkt', `+${data.bonus_points}`],
        ].map(([label, val]) => (
          <div key={label} style={{ background: '#1a1a2e', borderRadius: 5, padding: 10, textAlign: 'center' }}>
            <div style={{ color: '#888', fontSize: 10 }}>{label}</div>
            <div style={{ color: '#fff', fontWeight: 'bold' }}>{val}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```
cd frontend
npx vitest run src/__tests__/mobile/ProfilPage.test.tsx
```

Expected: all 3 PASS.

- [ ] **Step 5: Run full frontend test suite**

```
cd frontend
npm run test:run
```

Expected: all pass.

- [ ] **Step 6: Run full backend test suite**

```
cd backend
uv run python -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/mobile/screens/ProfilPage.tsx frontend/src/__tests__/mobile/ProfilPage.test.tsx
git commit -m "feat: implement ProfilPage with Spielstärke placeholder"
```

---

## Post-Implementation Notes

**Setting player PINs before the tournament:**

Run from `backend/`:

```python
# One-off script: set_pins.py
import asyncio
from app.database import AsyncSessionLocal
from app.models.player import Player
from sqlalchemy import select

PINS = {
    "Lars": "1234",
    "Mike": "2345",
    # ... add all players and spectators
}

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player))
        for player in result.scalars().all():
            if player.name in PINS:
                player.pin = PINS[player.name]
        await db.commit()

asyncio.run(main())
```

Run: `uv run python set_pins.py`

**Starting Cloudflare Tunnel before the tournament:**

```bash
cloudflared tunnel --url http://localhost:8000
```

This prints a public URL (e.g. `https://abc-def.trycloudflare.com`). Share it with remote spectators. Stop the tunnel when the tournament ends.

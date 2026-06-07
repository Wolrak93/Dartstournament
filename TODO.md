# TODO — Cycle 3: Mobile Web Interface

Phone-accessible view for players and spectators (local + remote via Cloudflare Tunnel).
Backend tasks first (Tasks 21–23), then frontend foundation (Task 24), then screens (Tasks 25–31).
All tasks implemented in separate feature branches from `development`.
A task is only done when: code works, tests pass, user has approved, branch merged.

Design spec: `docs/superpowers/specs/2026-06-07-cycle3-mobile-web-interface-design.md`
Implementation plan: `docs/superpowers/plans/2026-06-07-cycle3-mobile-web-interface.md`

---

## Task 21 — Backend: Auth & Mobile Endpoints Foundation

**Branch:** `feature/mobile-backend-auth`

### Player Model
- [x] Add `pin: str | None` column to `backend/app/models/player.py`
- [x] Add migration in `backend/app/database.py` (`ALTER TABLE players ADD COLUMN pin`)

### JWT Utility
- [x] Add `PyJWT` to `backend/pyproject.toml` via `uv add PyJWT`
- [x] Create `backend/app/auth.py`:
      - `create_mobile_token(player_id, name) → str`
      - `verify_mobile_token(token) → dict | None`

### Mobile Schemas
- [x] Create `backend/app/schemas/mobile.py` with all mobile Pydantic models:
      `MobileLoginRequest/Response`, `MobileLiveMatch`, `MobileUpcomingMatch`,
      `MobileCompletedMatch`, `MobileMatchesResponse`, `MobileStandingEntry`,
      `MobileStandingsResponse`, `MobileBracketMatch/Round/Response`,
      `MobileNebenrundeMatch`, `MobilePlayerStats`, `MobileStatsResponse`,
      `MobileProfileResponse`

### Mobile Router
- [x] Create `backend/app/routers/mobile.py` with:
      - `_get_active_tournament(db)` helper
      - `_get_current_player(credentials, db)` auth dependency (HTTPBearer + JWT)
      - `POST /mobile/auth/login` → verifies player_id + PIN, returns JWT

### Registration & CORS
- [x] Register `mobile.router` in `backend/app/main.py`
- [x] Update CORS `allow_origins` from localhost-only to `["*"]` (required for Cloudflare Tunnel)

### Tests (`backend/tests/test_mobile.py`)
- [x] JWT: `create_mobile_token` + `verify_mobile_token` round-trip
- [x] JWT: invalid token returns `None`
- [x] Login: valid credentials return token
- [x] Login: wrong PIN returns 401

---

## Task 22 — Backend: Mobile Data Endpoints

**Branch:** `feature/mobile-backend-endpoints`

### Endpoints (all in `backend/app/routers/mobile.py`)
- [x] `GET /mobile/matches` → `MobileMatchesResponse` (live / upcoming / completed)
- [x] `GET /mobile/standings` → `MobileStandingsResponse` (ranked table, KO-qualification flag)
- [x] `GET /mobile/bracket` → `MobileBracketResponse` (KO rounds + Nebenrunde matches)
- [x] `GET /mobile/stats` → `MobileStatsResponse` (per-player stats + event totals)
- [x] `GET /mobile/me` → `MobileProfileResponse` (logged-in player, rank, stats)

### Tests (`backend/tests/test_mobile.py`)
- [x] Each endpoint: no active tournament → returns empty/null response with 200
- [x] `GET /mobile/me`: returns correct player name and player_id from token

---

## Task 23 — Backend: PIN Seed Script

**Branch:** `feature/mobile-pin-setup`

### Script
- [x] Create `backend/scripts/set_pins.py`:
      Reads a dict of `{player_name: "XXXX"}` and sets `player.pin` for each.
      Run via `uv run python scripts/set_pins.py` before tournament start.
- [x] Document usage in script's docstring and in `README.md` (or a new `DEPLOYMENT.md`)
- [x] Add `.superpowers/` to root `.gitignore`

---

## Task 24 — Frontend: Mobile Foundation (Auth Utils, Layout, Routing)

**Branch:** `feature/mobile-frontend-foundation`

### Auth Utilities (`frontend/src/mobile/mobileAuth.ts`)
- [ ] `getToken()`, `setToken(token, playerId?)`, `clearToken()`, `isLoggedIn()`, `getStoredPlayerId()`

### API Client Additions
- [ ] Add `apiGetAuth` and `apiPostAuth` private helpers to `frontend/src/api/client.ts`
- [ ] Add mobile TypeScript types to `frontend/src/api/types.ts`
- [ ] Add mobile API functions to `frontend/src/api/client.ts`:
      `mobileLogin`, `getMobileMatches`, `getMobileStandings`,
      `getMobileBracket`, `getMobileStats`, `getMobileMe`

### Layout & Guard
- [ ] Create `frontend/src/mobile/MobileLayout.tsx` (header + `<Outlet />`)
- [ ] Create `frontend/src/mobile/MobileGuard.tsx` (redirect to `/mobile/login` if not logged in)

### Routing (`frontend/src/App.tsx`)
- [ ] Add `/mobile/*` route tree:
      `/mobile/login`, `/mobile` (home), `/mobile/spiele`, `/mobile/vorrunde`,
      `/mobile/bracket`, `/mobile/statistiken`, `/mobile/profil`
- [ ] Create stub components for all 7 screens (unblock TypeScript compilation)

### Tests
- [ ] `mobileAuth.ts`: token round-trip, `isLoggedIn`, `clearToken`
- [ ] `MobileGuard`: redirects when no token; renders children when token present

---

## Task 25 — Frontend: LoginScreen

**Branch:** `feature/mobile-login`

### Screen (`/mobile/login`)
- [ ] Name dropdown populated from `GET /players`
- [ ] 4-digit PIN input (numeric, max 4 chars)
- [ ] Submit → `mobileLogin(playerId, pin)` → store token → navigate to `/mobile`
- [ ] Error message on wrong PIN

### Tests
- [ ] Renders dropdown and submit button
- [ ] Wrong PIN → error message shown

---

## Task 26 — Frontend: HomeScreen (6 Tiles)

**Branch:** `feature/mobile-home`

### Screen (`/mobile`)
- [ ] 2×3 grid of tiles: Spiele, Vorrunde, KO-Bracket, Statistiken, Profil, Wetten
- [ ] Spiele tile: fetches `/mobile/matches` on mount, shows live match count as subtext
- [ ] Wetten tile: disabled (gray, dashed border, "Coming soon")
- [ ] All active tiles navigate to their respective route on tap

### Tests
- [ ] All 6 tiles rendered
- [ ] Wetten tile is not a navigation element

---

## Task 27 — Frontend: SpielePage

**Branch:** `feature/mobile-spiele`

### Screen (`/mobile/spiele`)
- [ ] Fetch `/mobile/matches` on mount
- [ ] If live match: subscribe `useWebSocket('match', liveMatchId)` for real-time score
- [ ] Display: live match (player names + remaining via WebSocket), upcoming queue, completed results

### Tests
- [ ] Shows live match player names
- [ ] Shows upcoming and completed matches

---

## Task 28 — Frontend: VorrundeSeite & BracketPage

**Branch:** `feature/mobile-bracket-screens`

### VorrundeSeite (`/mobile/vorrunde`)
- [ ] Standings table: Rank, Name, W/L, Avg, Punkte, Bonus
- [ ] KO-qualifizierte Zeilen (top 6) grün hervorgehoben
- [ ] Refresh on WebSocket `standings_update` event

### BracketPage (`/mobile/bracket`)
- [ ] Two tabs: "KO" and "Nebenrunde"
- [ ] KO tab: rounds (Viertelfinale → Halbfinale → Finale) with match results
- [ ] Nebenrunde tab: list of lightning matches with results
- [ ] Refresh on WebSocket `bracket_update` event

### Tests
- [ ] Vorrunde: renders player names; KO-qualified rows present
- [ ] BracketPage: KO tab shows Viertelfinale; tab switch shows Nebenrunde

---

## Task 29 — Frontend: StatisticsPage & ProfilPage

**Branch:** `feature/mobile-stats-profil`

### StatisticsPage (`/mobile/statistiken`)
- [ ] Player dropdown: "Alle Spieler" default, individual players selectable
- [ ] Top Averages: horizontal bar chart (relative to highest avg)
- [ ] Besondere Ereignisse tiles: 180er, Bulls Eye, Tripel 20, Bounce (totals or per-player)
- [ ] Refresh on WebSocket `standings_update` event

### ProfilPage (`/mobile/profil`)
- [ ] Photo (served via `/static/`), name, nickname, fun fact (from `playerProfiles.json`)
- [ ] Aktueller Stand card (rank + points)
- [ ] Spielstärke-Profil section: disabled, "Coming soon (Cycle 6)"
- [ ] Stats grid: W/L, Avg, Bonus-Pkt

### Tests
- [ ] StatisticsPage: renders player names and event count tiles
- [ ] ProfilPage: shows name and rank; "Coming soon" section present

---

## Notes for All Feature Branches

- Branches created from `development`
- Backend: `uv run python -m pytest tests/ -q` must pass (run from `backend/`)
- Frontend: `npm run test:run` must pass; `npm run lint` no errors (run from `frontend/`)
- Present work to user for review before merging into `development`
- Push `development` to remote after each merge: `git push origin development`

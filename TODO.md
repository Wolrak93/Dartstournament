# TODO — Cycle 2: Main Screen UI & API Layer

Referee-operated touch interface + FastAPI backend wiring.
Backend tasks first (Tasks 10–13), then frontend (Tasks 14–20).
All tasks implemented in separate feature branches from `development`.
A task is only done when: code works, tests pass, user has approved, branch merged.

---

## Task 10 — Pre-flight: Resolve Cycle 1 Technical Debt

**Branch:** `feature/preflight-fixes`

### EventType Unification
- [x] Audit both `EventType` definitions:
      `backend/app/models/special_event.py` (SQLAlchemy Enum, DB storage)
      `backend/app/services/events.py` (StrEnum, service layer)
- [x] Decide on canonical source:
      → Keep `services/events.py` as the single source of truth
      → Update `models/special_event.py` to import and reuse the same values
- [x] Align naming convention between both (e.g. `GEWORFEN_180` vs `180_geworfen`)
- [x] Run full test suite — confirm all 307 tests still pass (311 pass incl. new)

### Bonus Points Wiring
- [x] Add call to `update_standing_bonus()` inside `record_match_result()`
      OR extend `record_match_result()` signature to accept bonus events directly
- [x] Add inline TODO comment documenting the decision
- [x] Write regression test: verify bonus_points updates automatically on match result

### Test Utilities
- [x] Create `backend/tests/conftest.py` with shared fixtures:
      - `_miss()` helper: returns `Dart(score=0, band=DartBand.MISS, number=0)`
      - `make_visit(d1, d2, d3)` convenience builder
- [x] Update any existing tests that manually construct MISS darts to use `_miss()`

---

## Task 11 — Backend: Database Integration (Persistence Layer)

**Branch:** `feature/db-persistence`

### DB Session & Infrastructure
- [x] FastAPI dependency: `get_db()` yields async SQLAlchemy session
- [x] Ensure `database.py` calls `Base.metadata.create_all()` on startup
- [x] Verify all models are imported before `create_all` runs

### Repository Layer (`backend/app/repositories/`)
- [x] `player_repo.py`: create, get_by_id, list_all, update championship_count
- [x] `tournament_repo.py`: create, get_by_id (with players), update status
- [x] `tournament_player_repo.py`: add player to tournament, update reg/bonus/avg
- [x] `match_repo.py`: create, get_by_id, list_by_tournament, update status/winner
- [x] `visit_repo.py`: create visit, list_by_match_and_player
- [x] `special_event_repo.py`: create event, sum_bonus_by_player_and_tournament

### Service Wiring
- [x] `vorrunde.py`: after match result, persist standings to `TournamentPlayer`
- [x] `ko.py`: persist bracket state (winner progression) to `Match` records
- [x] `lightning.py`: persist lightning match results and schedule
- [x] `match.py`: persist each `Visit` to DB; call event detection and persist `SpecialEvent`
- [x] `bonus.py`: read from `SpecialEvent` table instead of in-memory history

### Tests
- [x] Integration tests using SQLite in-memory DB (`:memory:`)
- [x] Test: create player, tournament, add player, start tournament → verify DB state
- [x] Test: record visit → visit persisted, special event persisted if Vorrunde
- [x] Test: match result → standings updated in DB

---

## Task 12 — Backend: FastAPI REST Endpoints ✅

**Branch:** `feature/api-endpoints` → merged into `development`

### Player Endpoints (`backend/app/routers/players.py`)
- [x] `GET /players` — list all players
- [x] `POST /players` — create player (name, photo_path, music_path, championship_count)
- [x] `GET /players/{id}` — get player

### Tournament Endpoints (`backend/app/routers/tournaments.py`)
- [x] `POST /tournaments` — create tournament (player_ids, mode: swiss/fixed)
- [x] `GET /tournaments/{id}` — tournament with status, players, current round
- [x] `POST /tournaments/{id}/start` — generate Vorrunde schedule
- [x] `GET /tournaments/{id}/standings` — sorted standings (reg points + bonus)
- [x] `GET /tournaments/{id}/matches` — list all matches with status
- [x] `GET /tournaments/{id}/matches/next` — next unplayed match(es)
- [x] `POST /tournaments/{id}/ko/start` — run KO qualification, generate bracket
- [x] `GET /tournaments/{id}/ko/bracket` — full bracket with results
- [x] `GET /tournaments/{id}/lightning` — lightning round schedule and results

### Match Endpoints (`backend/app/routers/matches.py`)
- [x] `POST /matches/{id}/bull-throw` — record distances, returns starting player
- [x] `POST /matches/{id}/start` — set match status to in_progress
- [x] `POST /matches/{id}/visits` — record visit: `{dart1, dart2, dart3, bounce_flags, robin_hood_flags}`
- [x] `GET /matches/{id}/state` — full match state: remaining per player, visit count, checkout suggestion, current player, mode
- [x] `POST /matches/{id}/finish` — force-finish (referee override)

### Error Handling & Structure
- [x] Consistent error response schema: `{detail: str, code: str}`
- [x] 404 for missing resources, 409 for invalid state transitions, 422 for bad input
- [x] Include `backend/app/routers/__init__.py` and wire all routers into `main.py`

### Tests
- [x] API tests using FastAPI `TestClient` with in-memory DB fixture
- [x] Test each endpoint: happy path + main error cases
- [x] Test state machine: can't record visit before bull throw, can't start match twice

---

## Task 13 — Backend: WebSocket Real-time Layer ✅

**Branch:** `feature/websocket` → merged into `development`

### Connection Manager (`backend/app/websocket.py`)
- [x] `ConnectionManager` class: connect, disconnect, broadcast_match, broadcast_tournament
- [x] Support multiple clients per match/tournament channel
- [x] Dead-connection cleanup on every broadcast (asyncio-safe)

### WebSocket Endpoints (`backend/app/routers/ws.py`)
- [x] `WS /ws/match/{match_id}` — real-time match state
      - On connect: send current match state immediately (`match_state` event)
      - On each new visit: broadcast `score_update` + `special_event` (per event)
      - On match finish: broadcast `match_finished`
- [x] `WS /ws/tournament/{tournament_id}` — tournament-level updates
      - On connect: send `standings_update` (client fetches fresh data via REST)
      - On standings change: broadcast `standings_update`
      - On bracket change: broadcast `bracket_update`

### Event Protocol (outgoing JSON)
- [x] `{ type: "match_state", data: { match_id, status, round_type, player1_id, player2_id, ... } }`
- [x] `{ type: "score_update", data: { player_id, total, remaining_after, is_bust, special_events } }`
- [x] `{ type: "special_event", data: { player_id, event_type, bonus_value, count } }`
- [x] `{ type: "match_finished", data: { match_id, winner_id } }`
- [x] `{ type: "standings_update", data: { tournament_id } }`
- [x] `{ type: "bracket_update", data: { tournament_id } }`

### Reconnect Handling
- [x] Client re-subscribes and receives full current state on re-connect (no missed events needed)

### Tests
- [x] Test WebSocket connect → receives initial state
- [x] Test visit recorded via REST → WebSocket clients receive broadcast
- [x] Test disconnect handling (no crash on stale connection)

---

## Task 14 — Frontend: App Shell & Tournament Setup ✅

**Branch:** `feature/frontend-setup` → merged into `development`

### App Shell
- [x] React Router v6 setup with routes for all screens:
      `/setup`, `/bull-throw/:matchId`, `/score/:matchId`, `/walkon/:matchId`,
      `/standings`, `/bracket`, `/lightning`
- [x] Global tournament context (React Context API): tournament_id, current match, standings
- [x] `useWebSocket(channel, matchId|tournamentId)` custom hook:
      connects, parses events, exposes state, handles reconnect
- [x] `apiClient` utility: typed `fetch` wrapper for all REST endpoints

### Tournament Setup Screen (`/setup`)
- [x] Fetch player list from `GET /players`
- [x] Touch-friendly player selection (checkbox list with photos)
- [x] Player count validation (9–13; show error otherwise)
- [x] Mode toggle: Swiss / Fixed draw
- [x] "Start Tournament" button → `POST /tournaments` + `POST /tournaments/{id}/start`
- [x] Navigate to standings/overview on success

### Tests (Vitest + React Testing Library)
- [x] Setup screen: renders player list, validates count, calls API on submit

---

## Task 15 — Frontend: Bull Throw Screen ✅

**Branch:** `feature/frontend-bull-throw` → merged into `development`

### Screen (`/bull-throw/:matchId`)
- [x] Fetch match state (player names, photos)
- [x] Display both players/teams side by side
- [x] Touch-friendly click-to-select UI (singles: click winner; doubles: click best, then best opponent)
- [x] Submit → `POST /matches/{id}/bull-throw` → receive `starting_player_id`
- [x] Tie handling: "Unentschieden" button shows re-throw prompt, resets selection
- [x] Display result: "Player X wirft zuerst!"
- [x] "Weiter" button → calls `POST /matches/{id}/start` → navigate to Score Entry

### Tests
- [x] Renders both players, click to select shows result, tie handling, navigation

---

## Task 16 — Frontend: Score Entry Screen ✅

**Branch:** `feature/frontend-score-entry` → merged into `development`

### Screen (`/score/:matchId`)
- [x] Connect to `WS /ws/match/{matchId}` via `useWebSocket` hook
- [x] Score display panel: remaining score per player (large digits)
- [x] Current player indicator (highlighted name/side)
- [x] Visit counter per player
- [x] Large touch numpad: digits 0–9, DEL (backspace), CONFIRM
      - Input: up to 3 digits; shows running total as typed
      - CONFIRM → `POST /matches/{id}/visits`
- [x] Checkout suggestion panel: shown when remaining ≤ 170
- [x] Single-Out warning banner: shown after visit 15 (Vorrunde) or 25 (KO)
- [x] Bust feedback: red flash on score display, "BUST" overlay (auto-dismiss)
- [x] Match finished overlay: "Winner: [Name]", final scores, "Next Match" button
- [x] Special event popup: rendered as overlay (see Task 17)
- [x] Audio playback on confirmed visit (see Task 18)

### Tests
- [x] Numpad input → formats score correctly → calls API
- [x] Bust: shows bust overlay, score unchanged
- [x] Checkout suggestion: updates on each WebSocket `score_update`
- [x] Single-Out banner: appears at correct visit count

---

## Task 17 — Frontend: Special Event Popup ✅

**Branch:** `feature/frontend-events-popup` → merged into `development`

### Popup Component
- [x] Fullscreen overlay rendered above Score Entry screen
- [x] Triggered by `special_event` WebSocket message
- [x] Per event: show event name + animated counter (0 → bonus_value)
      - Positive values: count up (green); negative: count down (red)
- [x] Multiple events per visit: show sequentially (queue, not stacked)
- [x] Auto-dismiss after animation completes (no manual dismiss needed)
- [x] Dismisses to Score Entry screen state underneath

### Tests
- [x] Renders single event, completes animation, dismisses
- [x] Queue: two events shown in order

---

## Task 18 — Frontend: Audio Playback

**Branch:** `feature/frontend-audio`

### Audio Manager
- [x] Preload MP3 files from `user_input/sound/` on app start
      - Score files: `0.mp3` through `180.mp3` (verify available filenames)
      - Bust sound: if a bust MP3 exists, play on bust; otherwise skip
- [x] `playScore(total: number)` — plays matching MP3 after visit confirmed
- [x] `playBust()` — plays bust sound if available (`0.mp3`)
- [x] No overlap: cancel any currently playing sound before starting new one
- [x] Graceful fallback: if file missing, log warning and continue silently
- [x] Hook `useAudio()` for use in Score Entry screen

### Tests
- [x] `playScore(180)` calls correct audio file
- [x] Overlap: second call cancels first

---

## Task 19 — Frontend: Walk-on Screen

**Branch:** `feature/frontend-walkon`

### Screen (`/walkon/:matchId`)
- [ ] Fetch match state: get player IDs, map to photo + music assets
- [ ] Fullscreen layout:
      - Player photo (full bleed or centered large)
      - Player name overlay (large text)
      - Background: dark/dramatic
- [ ] Auto-play walk-on music from `user_input/music/` on screen mount
- [ ] Stop music when referee taps "Ready" button (or on navigate away)
- [ ] Trigger: navigate here before KO and Lightning Round matches only
      (Vorrunde matches go directly to Bull Throw)
- [ ] "Ready — Continue" button → navigate to Bull Throw screen

### Player → Asset Mapping
- [ ] Define mapping for all known players (Philipp, Mike, Henrik, Lars, Joachim,
      Jonas, Janni, Jens, Elina, Lena) to their photo + music files
- [ ] Fallback: blank photo and no music if player has no assets

### Tests
- [ ] Screen mounts → music plays, photo shown
- [ ] "Ready" → music stops, navigates to bull throw

---

## Task 20 — Frontend: Tournament Overview Screens ✅

**Branch:** `feature/frontend-overview` → merged into `development`

### Vorrunde Standings (`/standings`)
- [x] Connect to `WS /ws/tournament/{id}` for live updates
- [x] Standings table: rank, name, regular points, bonus points, average
- [x] Sorted: reg_points desc, bonus_points as tiebreaker
- [x] Highlight top 6 (KO direct) and positions 7–8 (bonus-point wildcard candidates)
- [x] Auto-update on `standings_update` WebSocket event

### KO Bracket (`/bracket`)
- [x] Visual bracket: QF → SF → Final + 3rd-place match
- [x] Each slot: player name, result (if played), TBD (if not yet)
- [x] Auto-update on `bracket_update` WebSocket event

### Lightning Round (`/lightning`)
- [x] List of lightning matches per KO round
- [x] Each entry: player names, status (pending/in progress/done), winner

### Next Matches Panel (shared component)
- [x] Shows upcoming unplayed matches in order
- [x] Used on standings and bracket screens as a sidebar/section
- [x] Updates live via WebSocket

### Navigation
- [x] Persistent nav bar or tab strip (Standings | KO Bracket | Lightning)
- [x] Accessible from score entry screen (referee can check standings between matches)

### Tests
- [x] Standings table: sorted correctly, highlights correct rows
- [x] Bracket: renders all 8 slots, shows result when match played
- [x] WebSocket update: standings re-render on new data

---

## Notes for All Feature Branches

- Branches created from `development`
- Backend: must pass `ruff` with no errors + all tests green
- Frontend: must pass `eslint`/`prettier` with no errors + Vitest tests pass
- Present work to user for review before merging into `development`
- Manual test instructions required for each task (Lesson 1 from Cycle 1)

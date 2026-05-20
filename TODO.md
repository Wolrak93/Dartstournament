# TODO — Cycle 2: Main Screen UI & API Layer

Referee-operated touch interface + FastAPI backend wiring.
Backend tasks first (Tasks 10–13), then frontend (Tasks 14–20).
All tasks implemented in separate feature branches from `development`.
A task is only done when: code works, tests pass, user has approved, branch merged.

---

## Task 10 — Pre-flight: Resolve Cycle 1 Technical Debt

**Branch:** `feature/preflight-fixes`

### EventType Unification
- [ ] Audit both `EventType` definitions:
      `backend/app/models/special_event.py` (SQLAlchemy Enum, DB storage)
      `backend/app/services/events.py` (StrEnum, service layer)
- [ ] Decide on canonical source:
      → Keep `services/events.py` as the single source of truth
      → Update `models/special_event.py` to import and reuse the same values
- [ ] Align naming convention between both (e.g. `GEWORFEN_180` vs `180_geworfen`)
- [ ] Run full test suite — confirm all 307 tests still pass

### Bonus Points Wiring
- [ ] Add call to `update_standing_bonus()` inside `record_match_result()`
      OR extend `record_match_result()` signature to accept bonus events directly
- [ ] Add inline TODO comment documenting the decision
- [ ] Write regression test: verify bonus_points updates automatically on match result

### Test Utilities
- [ ] Create `backend/tests/conftest.py` with shared fixtures:
      - `_miss()` helper: returns `Dart(score=0, band=DartBand.MISS, number=0)`
      - `make_visit(d1, d2, d3)` convenience builder
- [ ] Update any existing tests that manually construct MISS darts to use `_miss()`

---

## Task 11 — Backend: Database Integration (Persistence Layer)

**Branch:** `feature/db-persistence`

### DB Session & Infrastructure
- [ ] FastAPI dependency: `get_db()` yields async SQLAlchemy session
- [ ] Ensure `database.py` calls `Base.metadata.create_all()` on startup
- [ ] Verify all models are imported before `create_all` runs

### Repository Layer (`backend/app/repositories/`)
- [ ] `player_repo.py`: create, get_by_id, list_all, update championship_count
- [ ] `tournament_repo.py`: create, get_by_id (with players), update status
- [ ] `tournament_player_repo.py`: add player to tournament, update reg/bonus/avg
- [ ] `match_repo.py`: create, get_by_id, list_by_tournament, update status/winner
- [ ] `visit_repo.py`: create visit, list_by_match_and_player
- [ ] `special_event_repo.py`: create event, sum_bonus_by_player_and_tournament

### Service Wiring
- [ ] `vorrunde.py`: after match result, persist standings to `TournamentPlayer`
- [ ] `ko.py`: persist bracket state (winner progression) to `Match` records
- [ ] `lightning.py`: persist lightning match results and schedule
- [ ] `match.py`: persist each `Visit` to DB; call event detection and persist `SpecialEvent`
- [ ] `bonus.py`: read from `SpecialEvent` table instead of in-memory history

### Tests
- [ ] Integration tests using SQLite in-memory DB (`:memory:`)
- [ ] Test: create player, tournament, add player, start tournament → verify DB state
- [ ] Test: record visit → visit persisted, special event persisted if Vorrunde
- [ ] Test: match result → standings updated in DB

---

## Task 12 — Backend: FastAPI REST Endpoints

**Branch:** `feature/api-endpoints`

### Player Endpoints (`backend/app/routers/players.py`)
- [ ] `GET /players` — list all players
- [ ] `POST /players` — create player (name, photo_path, music_path, championship_count)
- [ ] `GET /players/{id}` — get player

### Tournament Endpoints (`backend/app/routers/tournaments.py`)
- [ ] `POST /tournaments` — create tournament (player_ids, mode: swiss/fixed)
- [ ] `GET /tournaments/{id}` — tournament with status, players, current round
- [ ] `POST /tournaments/{id}/start` — generate Vorrunde schedule
- [ ] `GET /tournaments/{id}/standings` — sorted standings (reg points + bonus)
- [ ] `GET /tournaments/{id}/matches` — list all matches with status
- [ ] `GET /tournaments/{id}/matches/next` — next unplayed match(es)
- [ ] `POST /tournaments/{id}/ko/start` — run KO qualification, generate bracket
- [ ] `GET /tournaments/{id}/ko/bracket` — full bracket with results
- [ ] `GET /tournaments/{id}/lightning` — lightning round schedule and results

### Match Endpoints (`backend/app/routers/matches.py`)
- [ ] `POST /matches/{id}/bull-throw` — record distances, returns starting player
- [ ] `POST /matches/{id}/start` — set match status to in_progress
- [ ] `POST /matches/{id}/visits` — record visit: `{dart1, dart2, dart3, bounce_flags, robin_hood_flags}`
- [ ] `GET /matches/{id}/state` — full match state: remaining per player, visit count, checkout suggestion, current player, mode
- [ ] `POST /matches/{id}/finish` — force-finish (referee override)

### Error Handling & Structure
- [ ] Consistent error response schema: `{detail: str, code: str}`
- [ ] 404 for missing resources, 409 for invalid state transitions, 422 for bad input
- [ ] Include `backend/app/routers/__init__.py` and wire all routers into `main.py`

### Tests
- [ ] API tests using FastAPI `TestClient` with in-memory DB fixture
- [ ] Test each endpoint: happy path + main error cases
- [ ] Test state machine: can't record visit before bull throw, can't start match twice

---

## Task 13 — Backend: WebSocket Real-time Layer

**Branch:** `feature/websocket`

### Connection Manager (`backend/app/websocket/manager.py`)
- [ ] `ConnectionManager` class: connect, disconnect, broadcast_to_match, broadcast_to_tournament
- [ ] Support multiple clients per match/tournament channel
- [ ] Thread-safe client registry

### WebSocket Endpoints (`backend/app/routers/ws.py`)
- [ ] `WS /ws/match/{match_id}` — real-time match state
      - On connect: send current match state immediately (`match_state` event)
      - On each new visit: broadcast `score_update` + `special_event` (if any)
      - On match finish: broadcast `match_finished`
- [ ] `WS /ws/tournament/{tournament_id}` — tournament-level updates
      - On connect: send current standings + next matches
      - On standings change: broadcast `standings_update`
      - On bracket change: broadcast `bracket_update`

### Event Protocol (outgoing JSON)
- [ ] `{ type: "match_state", data: { remaining_p1, remaining_p2, current_player, visit_count, checkout_suggestion, single_out_mode } }`
- [ ] `{ type: "score_update", data: { player_id, scored, remaining, is_bust } }`
- [ ] `{ type: "special_event", data: { player_id, events: [{name, bonus_value}] } }`
- [ ] `{ type: "match_finished", data: { winner_id, final_score_p1, final_score_p2 } }`
- [ ] `{ type: "standings_update", data: [ {player_id, reg_points, bonus_points, avg} ] }`
- [ ] `{ type: "bracket_update", data: { quarter_finals, semi_finals, final, third_place } }`

### Reconnect Handling
- [ ] Client re-subscribes and receives full current state on re-connect (no missed events needed)

### Tests
- [ ] Test WebSocket connect → receives initial state
- [ ] Test visit recorded via REST → WebSocket clients receive broadcast
- [ ] Test disconnect handling (no crash on stale connection)

---

## Task 14 — Frontend: App Shell & Tournament Setup

**Branch:** `feature/frontend-setup`

### App Shell
- [ ] React Router v6 setup with routes for all screens:
      `/setup`, `/bull-throw/:matchId`, `/score/:matchId`, `/walkon/:matchId`,
      `/standings`, `/bracket`, `/lightning`
- [ ] Global tournament context (React Context API): tournament_id, current match, standings
- [ ] `useWebSocket(channel, matchId|tournamentId)` custom hook:
      connects, parses events, exposes state, handles reconnect
- [ ] `apiClient` utility: typed `fetch` wrapper for all REST endpoints

### Tournament Setup Screen (`/setup`)
- [ ] Fetch player list from `GET /players`
- [ ] Touch-friendly player selection (checkbox list with photos)
- [ ] Player count validation (9–13; show error otherwise)
- [ ] Mode toggle: Swiss / Fixed draw
- [ ] "Start Tournament" button → `POST /tournaments` + `POST /tournaments/{id}/start`
- [ ] Navigate to standings/overview on success

### Tests (Vitest + React Testing Library)
- [ ] Setup screen: renders player list, validates count, calls API on submit

---

## Task 15 — Frontend: Bull Throw Screen

**Branch:** `feature/frontend-bull-throw`

### Screen (`/bull-throw/:matchId`)
- [ ] Fetch match state (player names, photos)
- [ ] Display both players/teams side by side
- [ ] Touch-friendly distance input per player (numeric, in mm or arbitrary units)
- [ ] Submit → `POST /matches/{id}/bull-throw` → receive `starting_player_id`
- [ ] Tie handling: show "Tie — re-throw" prompt, reset inputs
- [ ] Display result: "Player X throws first"
- [ ] "Continue" button → navigate to Walk-on (KO/Lightning) or Score Entry (Vorrunde)

### Tests
- [ ] Renders both players, submits distances, shows result, handles tie

---

## Task 16 — Frontend: Score Entry Screen

**Branch:** `feature/frontend-score-entry`

### Screen (`/score/:matchId`)
- [ ] Connect to `WS /ws/match/{matchId}` via `useWebSocket` hook
- [ ] Score display panel: remaining score per player (large digits)
- [ ] Current player indicator (highlighted name/side)
- [ ] Visit counter per player
- [ ] Large touch numpad: digits 0–9, DEL (backspace), CONFIRM
      - Input: up to 3 digits; shows running total as typed
      - CONFIRM → `POST /matches/{id}/visits`
- [ ] Checkout suggestion panel: shown when remaining ≤ 170
- [ ] Single-Out warning banner: shown after visit 15 (Vorrunde) or 25 (KO)
- [ ] Bust feedback: red flash on score display, "BUST" overlay (auto-dismiss)
- [ ] Match finished overlay: "Winner: [Name]", final scores, "Next Match" button
- [ ] Special event popup: rendered as overlay (see Task 17)
- [ ] Audio playback on confirmed visit (see Task 18)

### Tests
- [ ] Numpad input → formats score correctly → calls API
- [ ] Bust: shows bust overlay, score unchanged
- [ ] Checkout suggestion: updates on each WebSocket `score_update`
- [ ] Single-Out banner: appears at correct visit count

---

## Task 17 — Frontend: Special Event Popup

**Branch:** `feature/frontend-events-popup`

### Popup Component
- [ ] Fullscreen overlay rendered above Score Entry screen
- [ ] Triggered by `special_event` WebSocket message
- [ ] Per event: show event name + animated counter (0 → bonus_value)
      - Positive values: count up (green); negative: count down (red)
- [ ] Multiple events per visit: show sequentially (queue, not stacked)
- [ ] Auto-dismiss after animation completes (no manual dismiss needed)
- [ ] Dismisses to Score Entry screen state underneath

### Tests
- [ ] Renders single event, completes animation, dismisses
- [ ] Queue: two events shown in order

---

## Task 18 — Frontend: Audio Playback

**Branch:** `feature/frontend-audio`

### Audio Manager
- [ ] Preload MP3 files from `user_input/sound/` on app start
      - Score files: `0.mp3` through `180.mp3` (verify available filenames)
      - Bust sound: if a bust MP3 exists, play on bust; otherwise skip
- [ ] `playScore(total: number)` — plays matching MP3 after visit confirmed
- [ ] `playBust()` — plays bust sound if available
- [ ] No overlap: cancel any currently playing sound before starting new one
- [ ] Graceful fallback: if file missing, log warning and continue silently
- [ ] Hook `useAudio()` for use in Score Entry screen

### Tests
- [ ] `playScore(180)` calls correct audio file
- [ ] Overlap: second call cancels first

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

## Task 20 — Frontend: Tournament Overview Screens

**Branch:** `feature/frontend-overview`

### Vorrunde Standings (`/standings`)
- [ ] Connect to `WS /ws/tournament/{id}` for live updates
- [ ] Standings table: rank, name, regular points, bonus points, average
- [ ] Sorted: reg_points desc, bonus_points as tiebreaker
- [ ] Highlight top 6 (KO direct) and positions 7–8 (bonus-point wildcard candidates)
- [ ] Auto-update on `standings_update` WebSocket event

### KO Bracket (`/bracket`)
- [ ] Visual bracket: QF → SF → Final + 3rd-place match
- [ ] Each slot: player name, result (if played), TBD (if not yet)
- [ ] Auto-update on `bracket_update` WebSocket event

### Lightning Round (`/lightning`)
- [ ] List of lightning matches per KO round
- [ ] Each entry: player names, status (pending/in progress/done), winner

### Next Matches Panel (shared component)
- [ ] Shows upcoming unplayed matches in order
- [ ] Used on standings and bracket screens as a sidebar/section
- [ ] Updates live via WebSocket

### Navigation
- [ ] Persistent nav bar or tab strip (Standings | KO Bracket | Lightning)
- [ ] Accessible from score entry screen (referee can check standings between matches)

### Tests
- [ ] Standings table: sorted correctly, highlights correct rows
- [ ] Bracket: renders all 8 slots, shows result when match played
- [ ] WebSocket update: standings re-render on new data

---

## Notes for All Feature Branches

- Branches created from `development`
- Backend: must pass `ruff` with no errors + all tests green
- Frontend: must pass `eslint`/`prettier` with no errors + Vitest tests pass
- Present work to user for review before merging into `development`
- Manual test instructions required for each task (Lesson 1 from Cycle 1)

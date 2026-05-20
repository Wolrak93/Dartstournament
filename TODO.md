# TODO — Cycle 1: Foundation & Tournament Engine

Backend logic only. No UI in this cycle.
All tasks are implemented in separate feature branches branched from `development`.
A task is only done when: code works, tests pass, user has approved, branch merged.

---

## Task 1 — Project Scaffolding

**Branch:** `feature/project-scaffolding`

### Backend
- [x] Initialize uv project (`pyproject.toml`) with dependencies:
      FastAPI, uvicorn, SQLAlchemy, aiosqlite, websockets, pytest, ruff
- [x] Create `backend/app/main.py` with minimal FastAPI app (health endpoint)
- [x] Set up SQLAlchemy async engine with SQLite (`backend/app/database.py`)
- [x] Verify `ruff` linter runs cleanly on empty project
- [x] Verify `pytest` runs (no tests yet, just confirms setup)

### Frontend
- [x] Initialize Vite + React + TypeScript project in `frontend/`
- [x] Install ESLint + Prettier, configure for Airbnb style
- [x] Verify `npm run build` produces output without errors
- [x] Verify `npm run lint` runs cleanly

---

## Task 2 — Data Models

**Branch:** `feature/data-models`

### SQLAlchemy Models (`backend/app/models/`)
- [x] `Player`: id, name, photo_path, music_path, championship_count
- [x] `Tournament`: id, created_at, player_count, mode (swiss/fixed), status
- [x] `TournamentPlayer`: tournament_id, player_id, reg_points, bonus_points, avg_score
- [x] `Match`: id, tournament_id, round_type (vorrunde/ko/lightning), round_number,
      player1_id, player2_id, (optional) player3_id, player4_id,
      starting_score_p1, starting_score_p2, winner_id, status
- [x] `Visit`: id, match_id, player_id, dart1, dart2, dart3, total, is_bust, visit_number
- [x] `SpecialEvent`: id, visit_id, player_id, event_type, bonus_value
- [x] `BettingAccount`: id, player_id (nullable for spectators), name, balance
- [x] `Bet`: id, match_id, account_id, amount, picked_player_id, payout

### Pydantic Schemas (`backend/app/schemas/`)
- [x] Schemas for all models (Create, Read, Update variants)
- [x] Response schemas for API endpoints

### Tests
- [x] Test: create tournament with players, verify DB relations
- [x] Test: all model constraints (nullable fields, foreign keys)

---

## Task 3 — Vorrunde Logic

**Branch:** `feature/vorrunde-logic`

### Player count & mode selection (`backend/app/services/vorrunde.py`)
- [x] Helper: determine mode for n players
      (n=10 or 12 → doubles eligible; n=9,11,13 → singles only)
- [x] Helper: validate that n is between 9 and 13

### Fixed Draw
- [x] Generate all pairings upfront at tournament start
- [x] Singles (n=9,11,13): each player gets 3–4 opponents, no repeat pairings
- [x] Doubles (n=10,12): each player gets 6 matches with a unique partner each time
      (partner rotation: no player plays with same partner twice)
- [x] Produce a schedule (ordered list of rounds, each round = parallel matches)

### Swiss System
- [x] Round 1: random pairings
- [x] Round N>1: pair players with similar point totals, avoid repeat pairings
- [x] Bye handling if needed (odd number of non-doubles players in a round)
- [x] Produce round-by-round schedule (next round generated after each round finishes)

### Points Calculation
- [x] Win: +1 point; Loss: +0 points
- [x] After each match: compute 3-dart average for each player (total_score / visits / 3 * 3 = total/visits)
      Wait — 3-dart average = total points scored / number of visits
- [x] Add average × (1/100) to regular points
- [x] Standings: sort by (regular_points + avg_bonus) desc, then by bonus_points desc as tiebreaker

### Tests
- [x] Test Swiss pairings for n=9,10,11,12,13 — no repeat pairings, correct match count
- [x] Test fixed draw partner rotation (no duplicate partners in doubles)
- [x] Test points calculation with sample match data
- [x] Test standings ordering with tied regular points

---

## Task 4 — KO Bracket Logic

**Branch:** `feature/ko-bracket`

### Qualification (`backend/app/services/ko.py`)
- [x] Sort players by regular points (desc)
- [x] Top 6 qualify directly
- [x] From remaining: sort by bonus_points (desc), take top 2
- [x] Ensure no player appears in both lists (can't qualify via both channels)
- [x] Seed 8 players into quarter-final bracket (1v8, 2v7, 3v6, 4v5)

### Bracket Progression
- [x] Generate QF matches from seeding
- [x] After each QF: winners → SF, losers → Lightning Round
- [x] After each SF: winners → Final/3rd-place match, losers → Lightning Round
- [x] Final: 2 legs (best of 2, tiebreak leg if 1-1?)
- [x] Track bracket state: who is where at each stage

### Starting Score with Handicap
- [x] Before generating each KO match: call handicap calculator (Task 7)
- [x] Store result in `Match.starting_score_p1` / `starting_score_p2`
- [x] Doubles KO: n/a — KO and Lightning rounds are singles only

### Tests
- [x] Test qualification: 13 players, verify exactly 8 qualify, no overlap
- [x] Test edge case: player 6 and player 7 have same regular points (tiebreak)
- [x] Test bracket seeding for 8 players
- [x] Test that losers correctly feed into Lightning Round

---

## Task 5 — Lightning Round (Nebenrunde)

**Branch:** `feature/lightning-round`

### Scheduling (`backend/app/services/lightning.py`)
- [ ] Pool of eliminated players grows as KO progresses
- [ ] After each KO round: pair eliminated players for a Lightning match
- [ ] Goal: every eliminated player plays one Lightning match per KO round (if possible)
- [ ] Handle uneven pool sizes (bye for one player if odd count)
- [ ] 301 points, Single-Out (no Double-Out required)
- [ ] Track Lightning standings separately

### Tests
- [ ] Test with 5 eliminated players: correct pairing + 1 bye
- [ ] Test Lightning schedule across 3 KO rounds

---

## Task 6 — Match Flow Engine

**Branch:** `feature/match-flow`

### Bull Throw (`backend/app/services/match.py`)
- [ ] Record bull distance for each player/team
- [ ] Determine starting player (closest to bull goes first)
- [ ] Tie handling: re-throw (store multiple rounds if needed)

### Score Entry & Validation
- [ ] Accept a visit: (dart1, dart2, dart3) as individual values OR total
- [ ] Validate each dart: 0–60 (single fields), double fields, triple fields, bull (25/50)
- [ ] Compute visit total
- [ ] Bust detection: if remaining - total < 0, OR remaining - total == 1 (can't finish on 1 in Double-Out),
      OR total > remaining → bust, visit scores 0, player keeps current remaining
- [ ] Double-Out check: final dart must be a double (or bullseye=D25) — else bust
- [ ] Single-Out fallback: after visit limit (15 Vorrunde, 25 KO), switch to Single-Out rules

### Checkout Suggestion
- [ ] For each remaining score (2–170): precompute optimal checkout path
      (max 3 darts, standard dartboard, prefer known checkouts)
- [ ] Return suggestion(s) for current remaining score
- [ ] Handle scores with no 1-dart or 2-dart finish (show 3-dart path)
- [ ] Return empty suggestion if no checkout possible in 3 darts

### Single-Out Fallback Trigger
- [ ] Track visit count per player per leg
- [ ] After visit 15 (Vorrunde) or 25 (KO): set match flag `single_out_mode = True`
- [ ] In Single-Out mode: player may finish on any field (no double required)
- [ ] Bust still applies (can't overshoot)

### Tests
- [ ] Test bust: player on 32, throws 33 → bust, score unchanged
- [ ] Test Double-Out: player on 32, throws D16 → valid finish
- [ ] Test Double-Out: player on 32, throws S16 → bust
- [ ] Test Single-Out fallback triggers at correct visit count
- [ ] Test checkout suggestions for common scores (170, 121, 40, 2)
- [ ] Test bull throw: tie goes to re-throw

---

## Task 7 — Handicap Calculator

**Branch:** `feature/handicap`

### Logic (`backend/app/services/handicap.py`)
- [ ] Input: championship count of player A, championship count of player B
- [ ] Difference = abs(A - B)
- [ ] If difference < 3: no handicap
- [ ] If difference >= 3: stronger player's starting score += 100 + (difference - 3) * 40
      (e.g. diff=3 → +100, diff=4 → +140, diff=5 → +180)
- [ ] Doubles (2v2): compute 4 pairwise comparisons (p1 vs p3, p1 vs p4, p2 vs p3, p2 vs p4),
      sum all handicap values, divide by 4 (round to nearest integer)
- [ ] Return adjusted starting scores for both sides

### Tests
- [ ] diff=0 → no handicap
- [ ] diff=2 → no handicap
- [ ] diff=3 → stronger side +100
- [ ] diff=5 → stronger side +180
- [ ] doubles: mixed championship counts, verify quartered result

---

## Task 8 — Special Events Detection

**Branch:** `feature/special-events`

### Detection Engine (`backend/app/services/events.py`)
- [ ] Input: visit (dart1, dart2, dart3), remaining_before, remaining_after, match context
- [ ] Detect and return list of all triggered events per visit
- [ ] Implement each of the 18 events:

| Event | Detection logic |
|---|---|
| 26 geworfen | visit total == 26 |
| 180 geworfen | visit total == 180 |
| 170 Rest | remaining_after == 170 |
| Kack-Rest | remaining_after in [2, 3]; re-check if 3→threw 1→remaining now 2 |
| Bogey | remaining_after in [159,162,163,165,166,168,169] |
| Tripel | any dart lands in triple ring (value = triple field × 3) — count occurrences |
| Tripel 20 | any dart == T20 (60) — count occurrences |
| Bull | any dart == single bull (25) — count occurrences |
| Bulls Eye | any dart == bullseye (50) — count occurrences |
| Bounce | any dart flagged as bounce (referee input) — count occurrences |
| Robin Hood | any dart flagged as robin hood (referee input) — count occurrences |
| BE Finish | finish (remaining_after == 0) AND finishing dart == bullseye |
| odd Finish | finish AND finishing double is an odd number (D1,D3,...,D19) |
| Double Double | count of darts landing on any double field >= 2 |
| Mad House | finish AND finishing dart == D1 |
| Shanghai | all 3 darts land on same number (any of S/D/T of that number) |
| Bust | visit is a bust |
| Doppel-Treffer | any dart lands on a double field (not bust) — count occurrences |
| Gleiche Zahl | all 3 darts land in same numbered section (any band) |

- [ ] Bonus points only stored if match is in Vorrunde phase
- [ ] Events that can trigger multiple times per visit: return count × value

### Tests
- [ ] Test each of the 18 events with a crafted visit
- [ ] Test combined events (e.g. Mad House also triggers odd Finish)
- [ ] Test Bounce/Robin Hood (manual flag input path)
- [ ] Test: KO match → events detected but bonus_value = 0

---

## Task 9 — Bonus Points Aggregation

**Branch:** `feature/bonus-points`

### Aggregation (`backend/app/services/bonus.py`)
- [ ] Sum all SpecialEvent.bonus_value per player per tournament (Vorrunde only)
- [ ] Expose total bonus points per player for standings and KO qualification
- [ ] Real-time update: recalculate after each visit

### Tests
- [ ] Test running total updates correctly after each visit
- [ ] Test KO events produce 0 bonus (not added to total)

---

## Notes for All Feature Branches

- Each branch is created from `development`
- All new code must pass `ruff` (backend) and `eslint` (frontend) with no errors
- Each task needs at least the tests listed above before being considered done
- Present work to user for review before merging into `development`

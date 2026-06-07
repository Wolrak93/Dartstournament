# Project Roadmap — Backsberger Open (Darts Tournament)

## Goal

A clean, reusable darts tournament application for the annual Backsberger Open.
The main screen runs in a browser on a Windows touch PC operated by a referee.
Players and guests access a responsive web interface on their phones.
Designed to work year after year with varying player counts (9–13).

---

## Development Cycles

### Cycle 1 — Foundation & Tournament Engine ✓ COMPLETE

Backend logic only — no UI. 307 tests passing. Merged to development.

- [x] Project scaffolding (backend + frontend directories, pyproject.toml, package.json)
- [x] Data models: Player, Tournament, Match, Score, SpecialEvent, BonusPoints
- [x] Vorrunde logic
  - Swiss system implementation (dynamic pairing after each round)
  - Fixed draw implementation (all pairings set at tournament start)
  - Singles mode (n = 9, 11, 13): 3–4 matches per player
  - Doubles mode (n = 10, 12): 6 matches per player, rotating partners
  - Points: Win/Loss + 3-Dart-Average × (1/100)
- [x] KO bracket logic
  - Qualification: top 6 by regular points + top 2 bonus points among remaining
  - Quarter-finals → Semi-finals → 3rd-place match → Final (2 legs)
  - Single-Out fallback after 25 visits
- [x] Lightning Round (Nebenrunde) logic
  - Parallel to KO rounds, one match per KO round where possible
  - 301, Single-Out
- [x] Match flow engine
  - Bull throw to determine starting player
  - Score validation (bust detection, valid doubles for Double-Out)
  - Checkout suggestion calculator
  - Single-Out fallback trigger
- [x] Handicap calculator
  - Threshold: ≥ 3 championship difference → +100 points; +40 per additional
  - Doubles: divide total handicap by 4 (4 pairwise comparisons)
- [x] Special events detection engine (all 18 events from CLAUDE.md)
- [x] Bonus points aggregation per player

### Cycle 2 — Main Screen UI (Touch)

Referee-operated touch interface.

- [x] React + Vite + TypeScript project setup (ESLint, Prettier)
- [x] WebSocket connection to backend (real-time state updates)
- [x] Bull throw screen (referee enters Bull distance for each player)
- [x] Score entry screen
  - Large touch numpad
  - Current score, remaining, visit counter
  - Checkout suggestion panel
  - Single-Out warning display
- [x] Special event popup (animated counter overlay on score entry)
- [x] Audio: score announcement via MP3 playback
- [x] Walk-on screen: player photo + walk-on music (KO/Lightning rounds only)
- [x] Tournament overview screens
  - Vorrunde: standings table (regular points + bonus points)
  - KO bracket view
  - Lightning Round bracket view
  - Next matches queue

### Cycle 3 — Mobile Web Interface

Phone-accessible view for players and spectators.

- [ ] Responsive layout (mobile-first)
- [ ] Live fixtures (upcoming matches)
- [ ] Vorrunde standings table
- [ ] KO bracket view
- [ ] Lightning Round results
- [ ] Statistics page (total + per player: all special event counts, averages)
- [ ] Simple login (name selection + 4-digit PIN; no sensitive data)
- [ ] Player profile page (photo, stats, current standing)

### Cycle 4 — Betting System (¥$)

- [ ] ¥$ accounts (players + spectators, 1000 ¥$ starting budget)
- [ ] Bet placement UI (mobile + main screen sidebar)
  - One bet per match; changeable until match starts
  - Cannot bet on yourself
  - Shows total pot size only (split hidden until close)
- [ ] System auto-bet injection per match
  - Vorrunde/Lightning: 10 ¥$ per player involved
  - KO: 50 ¥$ per player involved
  - Doubles: 10 ¥$ × 4 players = 40 ¥$ per match
- [ ] Blind pari-mutuel payout calculation
- [ ] Bet history per user
- [ ] ¥$ leaderboard
- [ ] Certificate generation for Top 3 ¥$ earners (PDF or printable HTML)

### Cycle 5 — Polish, Testing & Hardening

- [ ] Full test suite (pytest for backend, Vitest for frontend)
- [ ] End-to-end tournament simulation for each player count (9–13)
- [ ] Edge cases: all-bets-on-one-side, handicap extremes, bust on last visit
- [ ] WebSocket reconnect handling (phone goes to sleep, refreshes page)
- [ ] Performance check (latency, touch responsiveness)
- [ ] Lessons-learned session

### Cycle 6 — Personalised Checkout Profiles

Generate player-specific optimal checkout suggestion tables via Monte Carlo simulation, driven by each player's manually configured throw profile. Players can update their profile at any time before or during the tournament; any change triggers an immediate recalculation.

Player profile parameters:
- Normal standard deviation (general aiming accuracy)
- Standard deviation on strong fields (tighter spread when aiming at a preferred field)
- List of strong fields (the fields where the reduced deviation applies)

Tasks:
- [ ] Player profile model: store the three parameters per player (normal σ, strong-field σ, strong-field list)
- [ ] Profile UI: settings screen where each player can view and edit their own profile
- [ ] Monte Carlo evaluator: for each score (1–230) and dart count (1–3), simulate N throws per candidate checkout path using the player's σ values and select the highest-probability finish
- [ ] Profile generator: produce `checkouts_<player>.json` in the existing table format on every profile save
- [ ] Backend: serve the correct personalised checkout table for the currently active player
- [ ] Frontend: display personalised checkout suggestions on the score entry screen
- [ ] Fallback: use the default single-out table if no profile exists for a player

### Cycle 7 (Optional) — Camera-Based Dart Detection

- [ ] Webcam integration
- [ ] Computer vision: detect dart positions and calculate score
- [ ] Referee override UI (correct misread scores)

---

## Clarified Decisions

| Topic | Decision |
|---|---|
| Doubles mode | Only with 10 or 12 players |
| Vorrunde scoring | Win/Loss + 3-Dart-Average × (1/100) |
| Matches per player | 6 (doubles mode), 3–4 (singles mode) |
| Score entry | Referee at main screen only; players do not touch the app |
| Betting odds | Blind pari-mutuel; total pot visible, split hidden until close |
| Betting currency | ¥$ (Backsberger Taler), 1000 ¥$ start |
| KO qualification | 6 via regular points, 2 via bonus points (no double-qualifying) |
| Handicap doubles | Sum of 4 pairwise comparisons, divided by 4 |
| System auto-bet | 10 ¥$ (Vorrunde), 50 ¥$ (KO) per player per match; not from player budget |

## Open Questions

None — all requirements clarified.

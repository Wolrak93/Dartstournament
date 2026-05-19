# Project Roadmap — Backsberger Open (Darts Tournament)

## Goal

A clean, reusable darts tournament application for the annual Backsberger Open.
The main screen runs in a browser on a Windows touch PC operated by a referee.
Players and guests access a responsive web interface on their phones.
Designed to work year after year with varying player counts (9–13).

---

## Development Cycles

### Cycle 1 — Foundation & Tournament Engine

Backend logic only — no UI yet.

- [ ] Project scaffolding (backend + frontend directories, pyproject.toml, package.json)
- [ ] Data models: Player, Tournament, Match, Score, SpecialEvent, BonusPoints
- [ ] Vorrunde logic
  - Swiss system implementation (dynamic pairing after each round)
  - Fixed draw implementation (all pairings set at tournament start)
  - Singles mode (n = 9, 11, 13): 3–4 matches per player
  - Doubles mode (n = 10, 12): 6 matches per player, rotating partners
  - Points: Win/Loss + 3-Dart-Average × (1/100)
- [ ] KO bracket logic
  - Qualification: top 6 by regular points + top 2 bonus points among remaining
  - Quarter-finals → Semi-finals → 3rd-place match → Final (2 legs)
  - Single-Out fallback after 25 visits
- [ ] Lightning Round (Nebenrunde) logic
  - Parallel to KO rounds, one match per KO round where possible
  - 301, Single-Out
- [ ] Match flow engine
  - Bull throw to determine starting player
  - Score validation (bust detection, valid doubles for Double-Out)
  - Checkout suggestion calculator
  - Single-Out fallback trigger
- [ ] Handicap calculator
  - Threshold: ≥ 3 championship difference → +100 points; +40 per additional
  - Doubles: divide total handicap by 4 (4 pairwise comparisons)
- [ ] Special events detection engine (all 18 events from CLAUDE.md)
- [ ] Bonus points aggregation per player

### Cycle 2 — Main Screen UI (Touch)

Referee-operated touch interface.

- [ ] React + Vite + TypeScript project setup (ESLint, Prettier)
- [ ] WebSocket connection to backend (real-time state updates)
- [ ] Bull throw screen (referee enters Bull distance for each player)
- [ ] Score entry screen
  - Large touch numpad
  - Current score, remaining, visit counter
  - Checkout suggestion panel
  - Single-Out warning display
- [ ] Special event popup (animated counter overlay on score entry)
- [ ] Audio: score announcement via MP3 playback
- [ ] Walk-on screen: player photo + walk-on music (KO/Lightning rounds only)
- [ ] Tournament overview screens
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

### Cycle 6 (Optional) — Camera-Based Dart Detection

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

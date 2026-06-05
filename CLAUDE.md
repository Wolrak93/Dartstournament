# CLAUDE.md — Local Project Config: DartsTournament (Backsberger Open)

## PROJECT CONTEXT

PROJECT_TYPE:      private
GITHUB_ACCOUNT:    Wolrak93 (SSH alias: github-privat)
REMOTE:            git@github-privat:Wolrak93/Dartstournament.git
LANGUAGE:          Python (backend), TypeScript (frontend)
FRAMEWORK:         FastAPI + WebSockets (backend), React + Vite (frontend)
PACKAGE_MANAGER:   uv (Python), npm (frontend)
TEST_FRAMEWORK:    pytest (backend), Vitest (frontend)
STYLE_GUIDE:       PEP8 (backend), Airbnb (frontend)
LINTER/FORMATTER:  ruff (backend), ESLint + Prettier (frontend)
DATABASE:          SQLite (via SQLAlchemy)

## PROJECT SUMMARY

Family darts tournament app ("Backsberger Open") for 9–13 players.
Main screen runs in a browser on a Windows touch PC.
Players/guests access a mobile web interface on their phones.

## TOURNAMENT STRUCTURE

### Vorrunde (Preliminary Round)
- Two modes: Swiss system OR fixed draw (offer both, choose per player count)
- Doubles mode only when player count is exactly 10 or 12; singles otherwise
- Doubles: rotating partners (new partner each match)
- Target matches per player: 6 in doubles mode, 3–4 in singles mode
- 301 points, Double-Out; Single-Out after 15 visits
- Bonus points from special events count only in Vorrunde
- Scoring: Win/Loss points + 3-Dart-Average × (1/100)
  (example: Average of 100 = 1 extra point, equivalent to one win)

### KO-Turnier
- Quarter-finals, Semi-finals, 3rd-place match, Final
- 501 points, Double-Out; Single-Out after 25 visits
- Final: 2 legs
- Walk-on music + player photo for each match
- Qualifikation: 6 spots via regular points, 2 spots via bonus points
  (top 6 by regular points qualify first, then 2 best bonus-point scores
  among remaining players; no player can qualify via both channels)

### Nebenrunde (Lightning Round)
- Anyone eliminated after Vorrunde or in KO goes here
- Each KO round should produce a parallel Lightning Round match if possible
- 301 points, Single-Out

## MATCH MECHANICS

- Bull throw to determine who goes first
- A referee always operates the main screen; players never enter scores themselves
- Touch-screen score entry with on-screen numpad (referee input)
- Checkout suggestions displayed at all times
- Scores announced via audio (MP3 files in user_input/sound/)
- Walk-on music + player photo only in KO/Lightning rounds

## HANDICAP SYSTEM

For each match: compare championship counts of both players (or teams).
- Difference < 3:  no handicap
- Difference = 3:  stronger player starts at 101 (100 extra points to play down for 301) or 601 for 501
- Each additional championship beyond 3: +40 more starting points
- In doubles (2v2): 4 pairwise comparisons; sum all differences, divide total handicap by 4

## SPECIAL EVENTS (besondere Ereignisse)

Special events trigger popups with counter animation.
Bonus points only apply in Vorrunde.

| Event          | Trigger                                                              | Value  |
|----------------|----------------------------------------------------------------------|--------|
| 26 geworfen    | Score exactly 26 in one visit                                        | +26    |
| 180 geworfen   | Score 180 in one visit (maximum)                                     | +1800  |
| 170 Rest       | Leave exactly 170 remaining (Big Fish setup)                         | +170   |
| Kack-Rest      | Leave 2 or 3 remaining; re-triggers if 3→1                          | +32    |
| Bogey          | Leave a bogey number [159,162,163,165,166,168,169]                   | -25    |
| Tripel         | Hit any triple field (can trigger multiple times per visit)          | +3     |
| Tripel 20      | Hit triple 20 (Tripel also triggers; multiple per visit)             | +17    |
| Bull           | Hit single bull (multiple per visit)                                 | +25    |
| Bulls Eye      | Hit bullseye (multiple per visit)                                    | +50    |
| Bounce         | A dart falls out of the board (multiple per visit)                   | -10    |
| Robin Hood     | A dart sticks in another dart (multiple per visit)                   | +65    |
| BE Finish      | Finish with bullseye (Bulls Eye also triggers)                       | +50    |
| odd Finish     | Finish on an odd double (e.g. D19; Mad House also triggers)          | +34    |
| Double Double  | Hit at least two double fields in one visit                          | +80    |
| Mad House      | Finish on Double 1 (odd Finish also triggers)                        | +17    |
| Shanghai       | Single + Double + Triple of the same number in one visit             | +120   |
| Bust           | Overthrow — score goes over remaining points                         | -1     |
| Doppel-Treffer | Hit any double field (not necessarily for checkout; multiple/visit)  | +8     |
| Gleiche Zahl   | All 3 darts land in fields of the same number (any band)             | +12    |

## BETTING SYSTEM (¥$ — Backsberger Taler)

- Starting budget: 1000 ¥$ per person (players + spectators)
- Currency: ¥$ (internal family joke name)
- Model: Blind pari-mutuel
  - Visible while open: total pot size only (no split shown)
  - Final odds revealed only after betting window closes
  - Pot distributed proportionally to winners
  - No house edge (100% redistributed)
- Rules:
  - Cannot bet on yourself
  - One bet per match; can change amount or pick until window closes
  - No live betting; window closes when match starts
- System auto-bets (from system budget, not player budget):
  - Vorrunde / Lightning Round: 10 ¥$ per player per match
  - KO-Runde: 50 ¥$ per player per match
  - In doubles (2v2): 10 ¥$ per player = 40 ¥$ total per match
  - Purpose: prevents division by zero; winners always get something;
    grows the money supply over the tournament
- End of tournament: Top 3 ¥$ earners receive a "Darts Expert" certificate

## ASSETS (user_input/)

- sound/           — MP3 files for score announcements (0–180+)
- pics/            — Player photos (Philipp, Mike, Henrik, Lars, Joachim,
                     Jonas, Janni, Jens, Elina, Lena + blank + ¥$)
- music/           — Walk-on music per player
- GUI/             — Reference mockups (design may deviate)
- besonderes.txt   — Original special events list

## OPTIONAL / FUTURE

- Automatic dart detection via camera (Cycle 2 or later)
- Webcam-based recognition with manual override by referee

# Walk-on Screen Design — Task 19

**Date:** 2026-06-05
**Branch:** `feature/frontend-walkon`
**Route:** `/walkon/:matchId`

---

## Goal

Display a dramatic walk-on screen for each player before KO and Lightning round matches.
Vorrunde matches skip this screen entirely and go directly to Bull Throw.

---

## Files Changed / Created

| File | Action |
|------|--------|
| `frontend/src/data/playerProfiles.json` | Create — static per-player data |
| `frontend/src/screens/WalkOnScreen.tsx` | Create — main screen component |
| `frontend/src/screens/WalkOnScreen.css` | Create — styling |
| `frontend/src/__tests__/WalkOnScreen.test.tsx` | Create — tests |
| `frontend/src/components/NextMatchesPanel.tsx` | Update — `matchLink()` routing |
| `frontend/src/App.tsx` | Update — replace placeholder with `<WalkOnScreen />` |

---

## State Machine

Phase type: `'p1-idle' | 'p1-playing' | 'p2-idle' | 'p2-playing'`

```
p1-idle   →[tap "Musik starten"]→  p1-playing
p1-playing →[tap "Ready — Weiter"]→ p2-idle      (music stops)
p2-idle   →[tap "Musik starten"]→  p2-playing
p2-playing →[tap "Ready — Weiter"]→ navigate /bull-throw/:matchId  (music stops)
```

Button label:
- `*-idle` phase → `"▶ Musik starten"`
- `*-playing` phase → `"Ready — Weiter"`

No transition animation between player 1 and player 2.

---

## Layout

Split layout (full-screen, dark theme `#0f0f1a`):

- **Left 45 %:** Player photo via `playerPhotoUrl(photo_path)`, fills the column height. Fallback: `blank.png`.
- **Right 55 %:** Player info (see below), flex column, padding `28px`, bottom padding `80px` to clear the button.
- **Bottom-right corner (absolute):** Button — "▶ Musik starten" or "Ready — Weiter".

Info shown on the right side (top to bottom):
1. **Name** (large, bold, `#f3f4f6`)
2. **Nickname** (medium, purple `#a78bfa`) — from `playerProfiles.json`
3. Divider line
4. **Fun Fact** (label + text) — from `playerProfiles.json`
5. **Best Performance** (label + text, amber `#fbbf24`) — from `playerProfiles.json`
6. Three stat tiles side-by-side:
   - Average (green `#34d399`) — from standings `avg_score`
   - Siege (blue `#60a5fa`) — from standings `wins`
   - Niederlagen (red `#f87171`) — computed as `games_played - wins`

If a player has no standings entry (e.g. in an edge case), tiles show `—`.

---

## Data Sources

| Field | Source |
|-------|--------|
| `photo_path`, `music_path`, `name` | `GET /players` via `getPlayers()` |
| `player1_id`, `player2_id`, `round_type` | `GET /matches/{id}` via `getMatch()` |
| `avg_score`, `wins`, `games_played` | `GET /tournaments/{id}/standings` via `getStandings(tournamentId)` |
| `nickname`, `funFact`, `bestPerformance` | `frontend/src/data/playerProfiles.json` (static, edited manually) |
| `tournamentId` | `TournamentContext` |

---

## Music Playback

- Managed via `useRef<HTMLAudioElement>` directly in the component (not `useAudio` hook).
- URL: `` `${API_BASE}/static/${player.music_path}` ``
- On "Musik starten": `audio.currentTime = 0; audio.play()`
- On "Ready — Weiter": `audio.pause(); audio.currentTime = 0`
- On unmount (navigate away): pause and reset.
- If `music_path` is `null`: skip silently, no error.

---

## Navigation Trigger Change (NextMatchesPanel)

`matchLink()` in `frontend/src/components/NextMatchesPanel.tsx` line 20–22:

**Before:**
```ts
return match.status === 'in_progress' ? `/score/${match.id}` : `/bull-throw/${match.id}`
```

**After:**
```ts
if (match.status === 'in_progress') return `/score/${match.id}`
if (match.status === 'pending' && (match.round_type === 'ko' || match.round_type === 'lightning'))
  return `/walkon/${match.id}`
return `/bull-throw/${match.id}`
```

Rationale: A match in `bull_throw` status already had the walk-on — skip it and go directly to bull throw.

---

## playerProfiles.json Structure

```json
{
  "Philipp":  { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Mike":     { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Henrik":   { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Lars":     { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Joachim":  { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Jonas":    { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Janni":    { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Jens":     { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Elina":    { "nickname": "", "funFact": "", "bestPerformance": "" },
  "Lena":     { "nickname": "", "funFact": "", "bestPerformance": "" }
}
```

Lookup key is `player.name` — casing must match exactly.
Missing fields display nothing (no crash).

---

## Tests

File: `frontend/src/__tests__/WalkOnScreen.test.tsx`

| Test | Description |
|------|-------------|
| Renders player 1 info | Name, nickname visible on mount; button = "Musik starten" |
| Musik starten | Tap button → `audio.play()` called; button changes to "Ready — Weiter" |
| Advance to player 2 | Tap "Ready — Weiter" → player 2 name visible; audio paused; button = "Musik starten" |
| Navigate to bull throw | Tap "Musik starten" → "Ready — Weiter" → `navigate('/bull-throw/42')` called |
| Missing music_path | No crash, no audio.play call |
| Missing profile entry | Nickname/funFact/bestPerformance fields simply absent — no error |

---

## Out of Scope

- Transition animation between players (not needed per user decision)
- Walk-on for Vorrunde matches (skipped by design)
- Editing player profiles via UI (manual JSON edit only)

# Walk-on Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the walk-on screen (`/walkon/:matchId`) that displays each player's photo and stats, plays their entrance music on demand, and routes to Bull Throw — KO and Lightning matches only.

**Architecture:** A new `WalkOnScreen` component manages a 4-state phase machine (`p1-idle → p1-playing → p2-idle → p2-playing`). Static per-player data (nickname, fun fact, best performance) is read from `playerProfiles.json`; live stats (average, wins, losses) come from the standings API. Music is handled directly in the component via `HTMLAudioElement`. The existing `NextMatchesPanel` routing function is updated to route KO/Lightning pending matches to `/walkon/` instead of `/bull-throw/`.

**Tech Stack:** React 18, TypeScript, React Router v6, Vitest + React Testing Library, Vite/jsdom

---

## File Map

| File | Action |
|------|--------|
| `frontend/src/data/playerProfiles.json` | Create |
| `frontend/src/screens/WalkOnScreen.tsx` | Create |
| `frontend/src/screens/WalkOnScreen.css` | Create |
| `frontend/src/__tests__/WalkOnScreen.test.tsx` | Create |
| `frontend/src/__tests__/NextMatchesPanel.test.tsx` | Create |
| `frontend/src/components/NextMatchesPanel.tsx` | Modify line 20–22 |
| `frontend/src/App.tsx` | Modify line 9 + 17 |

---

## Task 1: Create feature branch and playerProfiles.json

**Files:**
- Create: `frontend/src/data/playerProfiles.json`

- [ ] **Step 1: Create the feature branch**

```bash
git checkout development
git checkout -b feature/frontend-walkon
```

Expected: `Switched to a new branch 'feature/frontend-walkon'`

- [ ] **Step 2: Create playerProfiles.json**

Create `frontend/src/data/playerProfiles.json`:

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

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/playerProfiles.json
git commit -m "feat: add playerProfiles.json with empty entries for all players"
```

---

## Task 2: Write failing WalkOnScreen tests

**Files:**
- Create: `frontend/src/__tests__/WalkOnScreen.test.tsx`

- [ ] **Step 1: Create the test file**

Create `frontend/src/__tests__/WalkOnScreen.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import WalkOnScreen from '../screens/WalkOnScreen'

// ---------------------------------------------------------------------------
// Module mocks — hoisted by vitest, must be at top level
// ---------------------------------------------------------------------------

vi.mock('../api/client', () => ({
  API_BASE: 'http://localhost:8000',
  playerPhotoUrl: (path: string) => `http://localhost:8000/static/${path}`,
  getMatch: vi.fn(),
  getPlayers: vi.fn(),
  getStandings: vi.fn(),
}))

vi.mock('../contexts/TournamentContext', () => ({
  useTournament: () => ({
    tournamentId: 1,
    currentMatchId: null,
    setTournamentId: vi.fn(),
    setCurrentMatchId: vi.fn(),
  }),
}))

vi.mock('../data/playerProfiles.json', () => ({
  default: {
    Lars: { nickname: 'Der Hammer', funFact: 'Niemals verloren', bestPerformance: 'Sieger 2022' },
    Mike: { nickname: 'Speedy', funFact: 'Schnellster Spieler', bestPerformance: 'Finalist 2023' },
  },
}))

import { getMatch, getPlayers, getStandings } from '../api/client'
import type { MatchRead, Player, StandingEntry } from '../api/types'

// ---------------------------------------------------------------------------
// Audio mock — stubbedGlobal per test in beforeEach
// ---------------------------------------------------------------------------

const mockPlay = vi.fn().mockResolvedValue(undefined)
const mockPause = vi.fn()

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMatch(overrides: Partial<MatchRead> = {}): MatchRead {
  return {
    id: 42,
    tournament_id: 1,
    round_type: 'ko',
    round_number: 1,
    player1_id: 10,
    player2_id: 20,
    player3_id: null,
    player4_id: null,
    starting_score_p1: 501,
    starting_score_p2: 501,
    winner_id: null,
    starting_player_id: null,
    status: 'pending',
    ...overrides,
  }
}

function makePlayer(
  id: number,
  name: string,
  musicPath: string | null = `music/${name}.mp3`,
): Player {
  return { id, name, photo_path: null, music_path: musicPath, championship_count: 0 }
}

function makeStanding(
  playerId: number,
  avg: number,
  wins: number,
  played: number,
): StandingEntry {
  return {
    rank: 1,
    player_id: playerId,
    reg_points: 10,
    bonus_points: 0,
    avg_score: avg,
    total_points: 10,
    wins,
    games_played: played,
  }
}

function renderWalkOn(matchId = '42') {
  return render(
    <MemoryRouter initialEntries={[`/walkon/${matchId}`]}>
      <Routes>
        <Route path="/walkon/:matchId" element={<WalkOnScreen />} />
        <Route path="/bull-throw/:matchId" element={<div>Bull Throw Screen</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('WalkOnScreen', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockPlay.mockResolvedValue(undefined)
    vi.stubGlobal(
      'Audio',
      vi.fn(() => ({ play: mockPlay, pause: mockPause, currentTime: 0 })),
    )
  })

  it('renders player 1 name, nickname and "Musik starten" button on mount', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])
    vi.mocked(getStandings).mockResolvedValue([
      makeStanding(10, 72.4, 4, 5),
      makeStanding(20, 55.1, 2, 5),
    ])

    renderWalkOn()

    await waitFor(() => {
      expect(screen.getByText('Lars')).toBeInTheDocument()
      expect(screen.getByText('"Der Hammer"')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /musik starten/i })).toBeInTheDocument()
    })
  })

  it('clicking "Musik starten" creates Audio with player music URL and starts playback', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])
    vi.mocked(getStandings).mockResolvedValue([])

    const user = userEvent.setup()
    renderWalkOn()
    await waitFor(() => screen.getByRole('button', { name: /musik starten/i }))

    await user.click(screen.getByRole('button', { name: /musik starten/i }))

    expect(global.Audio).toHaveBeenCalledWith('http://localhost:8000/static/music/Lars.mp3')
    expect(mockPlay).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: /ready/i })).toBeInTheDocument()
  })

  it('clicking "Ready — Weiter" stops music and shows player 2 with "Musik starten"', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])
    vi.mocked(getStandings).mockResolvedValue([])

    const user = userEvent.setup()
    renderWalkOn()
    await waitFor(() => screen.getByRole('button', { name: /musik starten/i }))

    await user.click(screen.getByRole('button', { name: /musik starten/i }))
    await user.click(screen.getByRole('button', { name: /ready/i }))

    expect(mockPause).toHaveBeenCalled()
    await waitFor(() => {
      expect(screen.getByText('Mike')).toBeInTheDocument()
      expect(screen.getByText('"Speedy"')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /musik starten/i })).toBeInTheDocument()
    })
  })

  it('full flow navigates to /bull-throw/:matchId after player 2 ready', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])
    vi.mocked(getStandings).mockResolvedValue([])

    const user = userEvent.setup()
    renderWalkOn()
    await waitFor(() => screen.getByRole('button', { name: /musik starten/i }))

    // Player 1 walk-on
    await user.click(screen.getByRole('button', { name: /musik starten/i }))
    await user.click(screen.getByRole('button', { name: /ready/i }))

    // Player 2 walk-on
    await waitFor(() => screen.getByRole('button', { name: /musik starten/i }))
    await user.click(screen.getByRole('button', { name: /musik starten/i }))
    await user.click(screen.getByRole('button', { name: /ready/i }))

    await waitFor(() => {
      expect(screen.getByText('Bull Throw Screen')).toBeInTheDocument()
    })
  })

  it('does not call Audio when player has no music_path', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([
      makePlayer(10, 'Lars', null),
      makePlayer(20, 'Mike'),
    ])
    vi.mocked(getStandings).mockResolvedValue([])

    const user = userEvent.setup()
    renderWalkOn()
    await waitFor(() => screen.getByRole('button', { name: /musik starten/i }))

    await user.click(screen.getByRole('button', { name: /musik starten/i }))

    expect(global.Audio).not.toHaveBeenCalled()
    expect(mockPlay).not.toHaveBeenCalled()
    // Phase still advances to p1-playing
    expect(screen.getByRole('button', { name: /ready/i })).toBeInTheDocument()
  })

  it('renders without crash when player name has no profile entry', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([
      makePlayer(10, 'Kahn'),  // not in profiles mock
      makePlayer(20, 'Mike'),
    ])
    vi.mocked(getStandings).mockResolvedValue([])

    renderWalkOn()

    await waitFor(() => {
      expect(screen.getByText('Kahn')).toBeInTheDocument()
    })
    // No nickname rendered
    expect(screen.queryByText(/"/)).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests and confirm they fail with "Cannot find module"**

```bash
cd frontend && npx vitest run src/__tests__/WalkOnScreen.test.tsx
```

Expected: FAIL — `Cannot find module '../screens/WalkOnScreen'`

---

## Task 3: Implement WalkOnScreen component and CSS

**Files:**
- Create: `frontend/src/screens/WalkOnScreen.tsx`
- Create: `frontend/src/screens/WalkOnScreen.css`

- [ ] **Step 1: Create WalkOnScreen.css**

Create `frontend/src/screens/WalkOnScreen.css`:

```css
/* WalkOnScreen */

.walkon-screen {
  min-height: 100vh;
  background: #0f0f1a;
  display: flex;
  position: relative;
  overflow: hidden;
}

.walkon-photo-col {
  flex: 0 0 45%;
  position: relative;
  overflow: hidden;
}

.walkon-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.walkon-photo-placeholder {
  width: 100%;
  height: 100%;
  min-height: 100vh;
  background: linear-gradient(160deg, #2a2a3a 0%, #0a0a14 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3a3a5a;
  font-size: 5rem;
}

.walkon-photo-fade {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 60px;
  background: linear-gradient(to right, transparent, #0f0f1a);
}

.walkon-info-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 2rem 2rem 5rem 1.5rem;
  gap: 0.75rem;
  color: #f3f4f6;
}

.walkon-name {
  font-size: 2.2rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #f3f4f6;
  line-height: 1.1;
}

.walkon-nickname {
  font-size: 1.15rem;
  font-weight: 600;
  color: #a78bfa;
  margin-top: 0.2rem;
}

.walkon-divider {
  width: 40px;
  height: 2px;
  background: #4a4a6a;
  margin: 0.25rem 0;
}

.walkon-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #9ca3af;
  margin-bottom: 0.2rem;
}

.walkon-text {
  font-size: 0.875rem;
  color: #e2e8f0;
  line-height: 1.5;
}

.walkon-best {
  font-size: 0.875rem;
  font-weight: 600;
  color: #fbbf24;
}

.walkon-stats {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.25rem;
}

.walkon-stat {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 0.625rem 0.75rem;
  text-align: center;
  flex: 1;
}

.walkon-stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  margin-top: 0.15rem;
}

.walkon-stat-value--avg   { color: #34d399; }
.walkon-stat-value--wins  { color: #60a5fa; }
.walkon-stat-value--losses { color: #f87171; }

.walkon-stat-sub {
  font-size: 0.6rem;
  color: #6b7280;
  margin-top: 0.1rem;
}

.walkon-btn {
  position: absolute;
  bottom: 1.25rem;
  right: 1.5rem;
  background: #dc2626;
  color: #fff;
  padding: 0.875rem 2rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 700;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(220, 38, 38, 0.4);
  touch-action: manipulation;
}

.walkon-btn:active {
  background: #b91c1c;
}

.walkon-loading,
.walkon-error {
  min-height: 100vh;
  background: #0f0f1a;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}

.walkon-error { color: #fca5a5; }
```

- [ ] **Step 2: Create WalkOnScreen.tsx**

Create `frontend/src/screens/WalkOnScreen.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { API_BASE, getMatch, getPlayers, getStandings, playerPhotoUrl } from '../api/client'
import type { MatchRead, Player, StandingEntry } from '../api/types'
import { useTournament } from '../contexts/TournamentContext'
import profiles from '../data/playerProfiles.json'
import './WalkOnScreen.css'

type WalkOnPhase = 'p1-idle' | 'p1-playing' | 'p2-idle' | 'p2-playing'

interface PlayerProfile {
  nickname: string
  funFact: string
  bestPerformance: string
}

const playerProfiles = profiles as Record<string, PlayerProfile>

export default function WalkOnScreen() {
  const { matchId } = useParams<{ matchId: string }>()
  const navigate = useNavigate()
  const { tournamentId } = useTournament()

  const [match, setMatch] = useState<MatchRead | null>(null)
  const [playerMap, setPlayerMap] = useState<Map<number, Player>>(new Map())
  const [standings, setStandings] = useState<StandingEntry[]>([])
  const [phase, setPhase] = useState<WalkOnPhase>('p1-idle')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (!matchId) return
    const id = parseInt(matchId, 10)
    const standingsPromise =
      tournamentId != null ? getStandings(tournamentId) : Promise.resolve([])
    Promise.all([getMatch(id), getPlayers(), standingsPromise])
      .then(([matchData, playerList, standingsList]) => {
        setMatch(matchData)
        setPlayerMap(new Map(playerList.map((p) => [p.id, p])))
        setStandings(standingsList)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden')
      })
      .finally(() => setLoading(false))
  }, [matchId, tournamentId])

  useEffect(() => {
    return () => {
      audioRef.current?.pause()
    }
  }, [])

  function stopMusic(): void {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
  }

  function startMusic(player: Player): void {
    stopMusic()
    if (!player.music_path) return
    const audio = new Audio(`${API_BASE}/static/${player.music_path}`)
    audioRef.current = audio
    audio.play()?.catch((err: unknown) => {
      console.warn('[WalkOnScreen] Music playback failed:', err)
    })
  }

  function handleButton(): void {
    if (!match) return
    const p1 = playerMap.get(match.player1_id)
    const p2 = playerMap.get(match.player2_id)
    switch (phase) {
      case 'p1-idle':
        if (p1) startMusic(p1)
        setPhase('p1-playing')
        break
      case 'p1-playing':
        stopMusic()
        setPhase('p2-idle')
        break
      case 'p2-idle':
        if (p2) startMusic(p2)
        setPhase('p2-playing')
        break
      case 'p2-playing':
        stopMusic()
        navigate(`/bull-throw/${matchId}`)
        break
    }
  }

  if (loading) return <div className="walkon-loading">Laden…</div>
  if (error || !match) {
    return <div className="walkon-error">{error ?? 'Match nicht gefunden'}</div>
  }

  const activePlayerId = phase.startsWith('p1') ? match.player1_id : match.player2_id
  const activePlayer = playerMap.get(activePlayerId)
  const standingEntry = standings.find((s) => s.player_id === activePlayerId)
  const profile: PlayerProfile | undefined = activePlayer
    ? playerProfiles[activePlayer.name]
    : undefined
  const avg = standingEntry ? standingEntry.avg_score.toFixed(1) : '—'
  const wins = standingEntry ? String(standingEntry.wins) : '—'
  const losses = standingEntry
    ? String(standingEntry.games_played - standingEntry.wins)
    : '—'
  const buttonLabel = phase.endsWith('idle') ? '▶ Musik starten' : 'Ready — Weiter'

  return (
    <div className="walkon-screen">
      <div className="walkon-photo-col">
        {activePlayer?.photo_path != null ? (
          <img
            src={playerPhotoUrl(activePlayer.photo_path)}
            alt={activePlayer.name}
            className="walkon-photo"
          />
        ) : (
          <div className="walkon-photo-placeholder">📷</div>
        )}
        <div className="walkon-photo-fade" />
      </div>

      <div className="walkon-info-col">
        <div>
          <div className="walkon-name">{activePlayer?.name ?? '—'}</div>
          {profile?.nickname && (
            <div className="walkon-nickname">"{profile.nickname}"</div>
          )}
        </div>

        <div className="walkon-divider" />

        {profile?.funFact && (
          <div>
            <div className="walkon-label">Fun Fact</div>
            <div className="walkon-text">{profile.funFact}</div>
          </div>
        )}

        {profile?.bestPerformance && (
          <div>
            <div className="walkon-label">Best Performance</div>
            <div className="walkon-best">{profile.bestPerformance}</div>
          </div>
        )}

        <div className="walkon-stats">
          <div className="walkon-stat">
            <div className="walkon-label">Average</div>
            <div className="walkon-stat-value walkon-stat-value--avg">{avg}</div>
            <div className="walkon-stat-sub">dieses Turnier</div>
          </div>
          <div className="walkon-stat">
            <div className="walkon-label">Siege</div>
            <div className="walkon-stat-value walkon-stat-value--wins">{wins}</div>
            <div className="walkon-stat-sub">dieses Turnier</div>
          </div>
          <div className="walkon-stat">
            <div className="walkon-label">Niederlagen</div>
            <div className="walkon-stat-value walkon-stat-value--losses">{losses}</div>
            <div className="walkon-stat-sub">dieses Turnier</div>
          </div>
        </div>
      </div>

      <button className="walkon-btn" onClick={handleButton}>
        {buttonLabel}
      </button>
    </div>
  )
}
```

- [ ] **Step 3: Run WalkOnScreen tests — confirm they pass**

```bash
cd frontend && npx vitest run src/__tests__/WalkOnScreen.test.tsx
```

Expected: 6 tests PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/screens/WalkOnScreen.tsx frontend/src/screens/WalkOnScreen.css frontend/src/__tests__/WalkOnScreen.test.tsx
git commit -m "feat: implement WalkOnScreen with sequential walk-on per player"
```

---

## Task 4: Update NextMatchesPanel routing

**Files:**
- Create: `frontend/src/__tests__/NextMatchesPanel.test.tsx`
- Modify: `frontend/src/components/NextMatchesPanel.tsx` line 20–22

- [ ] **Step 1: Write failing test for NextMatchesPanel routing**

Create `frontend/src/__tests__/NextMatchesPanel.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import NextMatchesPanel from '../components/NextMatchesPanel'
import type { MatchRead } from '../api/types'

vi.mock('../api/client', () => ({
  getNextMatches: vi.fn(),
  playerPhotoUrl: (path: string) => `http://localhost:8000/static/${path}`,
}))

import { getNextMatches } from '../api/client'

function makeMatch(overrides: Partial<MatchRead> = {}): MatchRead {
  return {
    id: 1,
    tournament_id: 1,
    round_type: 'vorrunde',
    round_number: 1,
    player1_id: 10,
    player2_id: 20,
    player3_id: null,
    player4_id: null,
    starting_score_p1: 301,
    starting_score_p2: 301,
    winner_id: null,
    starting_player_id: null,
    status: 'pending',
    ...overrides,
  }
}

function renderPanel(matches: MatchRead[]) {
  vi.mocked(getNextMatches).mockResolvedValue(matches)
  return render(
    <MemoryRouter>
      <NextMatchesPanel tournamentId={1} playerMap={{}} lastWsEvent={null} />
    </MemoryRouter>,
  )
}

describe('NextMatchesPanel — matchLink routing', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('links a pending KO match to /walkon/:id', async () => {
    renderPanel([makeMatch({ id: 5, round_type: 'ko', status: 'pending' })])

    const link = await screen.findByRole('link', { name: /starten/i })
    expect(link).toHaveAttribute('href', '/walkon/5')
  })

  it('links a pending lightning match to /walkon/:id', async () => {
    renderPanel([makeMatch({ id: 6, round_type: 'lightning', status: 'pending' })])

    const link = await screen.findByRole('link', { name: /starten/i })
    expect(link).toHaveAttribute('href', '/walkon/6')
  })

  it('links a pending vorrunde match to /bull-throw/:id', async () => {
    renderPanel([makeMatch({ id: 7, round_type: 'vorrunde', status: 'pending' })])

    const link = await screen.findByRole('link', { name: /starten/i })
    expect(link).toHaveAttribute('href', '/bull-throw/7')
  })

  it('links a bull_throw KO match to /bull-throw/:id (walk-on already done)', async () => {
    renderPanel([makeMatch({ id: 8, round_type: 'ko', status: 'bull_throw' })])

    const link = await screen.findByRole('link', { name: /starten/i })
    expect(link).toHaveAttribute('href', '/bull-throw/8')
  })

  it('links an in_progress match to /score/:id', async () => {
    renderPanel([makeMatch({ id: 3, status: 'in_progress' })])

    const link = await screen.findByRole('link', { name: /fortsetzen/i })
    expect(link).toHaveAttribute('href', '/score/3')
  })
})
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd frontend && npx vitest run src/__tests__/NextMatchesPanel.test.tsx
```

Expected: FAIL — `links a pending KO match to /walkon/:id` fails because link currently points to `/bull-throw/5`

- [ ] **Step 3: Update matchLink() in NextMatchesPanel.tsx**

In `frontend/src/components/NextMatchesPanel.tsx`, replace lines 20–22:

```tsx
// Before:
function matchLink(match: MatchRead): string {
  return match.status === 'in_progress' ? `/score/${match.id}` : `/bull-throw/${match.id}`
}

// After:
function matchLink(match: MatchRead): string {
  if (match.status === 'in_progress') return `/score/${match.id}`
  if (
    match.status === 'pending' &&
    (match.round_type === 'ko' || match.round_type === 'lightning')
  )
    return `/walkon/${match.id}`
  return `/bull-throw/${match.id}`
}
```

- [ ] **Step 4: Run NextMatchesPanel tests — confirm they pass**

```bash
cd frontend && npx vitest run src/__tests__/NextMatchesPanel.test.tsx
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/NextMatchesPanel.tsx frontend/src/__tests__/NextMatchesPanel.test.tsx
git commit -m "feat: route KO and lightning matches through walk-on screen"
```

---

## Task 5: Wire App.tsx and run full suite

**Files:**
- Modify: `frontend/src/App.tsx` lines 9 + 17

- [ ] **Step 1: Update App.tsx**

In `frontend/src/App.tsx`, add the import after line 9 (after `import NextMatchesScreen`) and replace the placeholder on line 17:

```tsx
// Add import (after the existing screen imports):
import WalkOnScreen from './screens/WalkOnScreen'

// Replace the placeholder route:
// Before:
{ path: '/walkon/:matchId', element: <div>Walk-on (Task 19)</div> },

// After:
{ path: '/walkon/:matchId', element: <WalkOnScreen /> },
```

The full updated router section in App.tsx should look like:

```tsx
import WalkOnScreen from './screens/WalkOnScreen'

const router = createBrowserRouter([
  { path: '/', element: <HomeScreen /> },
  { path: '/setup', element: <SetupScreen /> },
  { path: '/bull-throw/:matchId', element: <BullThrowScreen /> },
  { path: '/score/:matchId', element: <ScoreEntryScreen /> },
  { path: '/walkon/:matchId', element: <WalkOnScreen /> },
  { path: '/standings', element: <StandingsScreen /> },
  { path: '/next-matches', element: <NextMatchesScreen /> },
  { path: '/bracket', element: <BracketScreen /> },
  { path: '/lightning', element: <LightningScreen /> },
])
```

- [ ] **Step 2: Run the full test suite**

```bash
cd frontend && npx vitest run
```

Expected: All tests pass (no regressions)

- [ ] **Step 3: Run ESLint**

```bash
cd frontend && npx eslint src/screens/WalkOnScreen.tsx src/components/NextMatchesPanel.tsx src/__tests__/WalkOnScreen.test.tsx src/__tests__/NextMatchesPanel.test.tsx
```

Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire WalkOnScreen into router (Task 19 complete)"
```

---

## Manual Test Instructions

1. Start backend: `cd backend && uv run uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173`, create tournament, start it
4. In the "Nächste Matches" panel, start a **Vorrunde** match → should go directly to Bull Throw (no walk-on)
5. Trigger KO phase, then start a **KO** match → should open Walk-on Screen
6. Verify: player 1 photo and name shown, button says "▶ Musik starten"
7. Tap "▶ Musik starten" → music plays (if `music_path` is set), button changes to "Ready — Weiter"
8. Tap "Ready — Weiter" → music stops, player 2 info appears
9. Repeat steps 6–8 for player 2
10. After player 2 taps "Ready — Weiter" → navigates to Bull Throw screen
11. Fill in `frontend/src/data/playerProfiles.json` with real nicknames/facts and verify they appear

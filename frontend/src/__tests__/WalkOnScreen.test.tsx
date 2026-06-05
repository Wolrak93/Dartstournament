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
      vi.fn(function () { return { play: mockPlay, pause: mockPause, currentTime: 0 } }),
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

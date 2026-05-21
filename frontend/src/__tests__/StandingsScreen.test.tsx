import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import StandingsScreen from '../screens/StandingsScreen'
import type { StandingEntry, Player } from '../api/types'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock('../contexts/TournamentContext', () => ({
  useTournament: () => ({
    tournamentId: 1,
    currentMatchId: null,
    setTournamentId: vi.fn(),
    setCurrentMatchId: vi.fn(),
  }),
}))

vi.mock('../api/client', () => ({
  API_BASE: 'http://localhost:8000',
  WS_BASE: 'ws://localhost:8000',
  playerPhotoUrl: (path: string) => `http://localhost:8000/static/${path}`,
  getPlayers: vi.fn(),
  getStandings: vi.fn(),
  getNextMatches: vi.fn(),
}))

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({ lastEvent: null, isConnected: false })),
}))

import { getPlayers, getStandings, getNextMatches } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MOCK_PLAYERS: Player[] = Array.from({ length: 9 }, (_, i) => ({
  id: i + 1,
  name: `Player ${i + 1}`,
  photo_path: null,
  music_path: null,
  championship_count: 0,
}))

function makeStandings(): StandingEntry[] {
  return MOCK_PLAYERS.map((p, i) => ({
    rank: i + 1,
    player_id: p.id,
    reg_points: (9 - i) * 2.5,
    bonus_points: (9 - i) * 10,
    avg_score: 80 - i * 5,
    total_points: (9 - i) * 2.5 + (9 - i) * 0.1,
  }))
}

function renderStandings() {
  return render(
    <MemoryRouter initialEntries={['/standings']}>
      <StandingsScreen />
    </MemoryRouter>,
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('StandingsScreen', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(useWebSocket).mockReturnValue({ lastEvent: null, isConnected: false })
    vi.mocked(getPlayers).mockResolvedValue(MOCK_PLAYERS)
    vi.mocked(getStandings).mockResolvedValue(makeStandings())
    vi.mocked(getNextMatches).mockResolvedValue([])
  })

  it('renders standings table with player names in rank order', async () => {
    renderStandings()

    await waitFor(() => expect(screen.getByText('Player 1')).toBeInTheDocument())
    expect(screen.getByText('Player 9')).toBeInTheDocument()

    // Rank 1 row comes before rank 9
    const rows = screen.getAllByRole('row')
    // rows[0] is the thead row; data rows start at index 1
    expect(rows[1]).toHaveTextContent('1')
    expect(rows[1]).toHaveTextContent('Player 1')
    expect(rows[9]).toHaveTextContent('9')
    expect(rows[9]).toHaveTextContent('Player 9')
  })

  it('highlights top 6 rows with KO qualifier class', async () => {
    renderStandings()

    await waitFor(() => expect(screen.getByText('Player 1')).toBeInTheDocument())

    const dataRows = screen.getAllByRole('row').slice(1)
    for (let i = 0; i < 6; i++) {
      expect(dataRows[i]).toHaveClass('standings-row--ko')
    }
  })

  it('highlights rows 7 and 8 with wildcard class', async () => {
    renderStandings()

    await waitFor(() => expect(screen.getByText('Player 1')).toBeInTheDocument())

    const dataRows = screen.getAllByRole('row').slice(1)
    expect(dataRows[6]).toHaveClass('standings-row--wildcard')
    expect(dataRows[7]).toHaveClass('standings-row--wildcard')
  })

  it('does not apply KO or wildcard class to rank 9 and beyond', async () => {
    renderStandings()

    await waitFor(() => expect(screen.getByText('Player 1')).toBeInTheDocument())

    const dataRows = screen.getAllByRole('row').slice(1)
    expect(dataRows[8]).not.toHaveClass('standings-row--ko')
    expect(dataRows[8]).not.toHaveClass('standings-row--wildcard')
  })

  it('re-fetches standings when a standings_update WebSocket event fires', async () => {
    const { rerender } = renderStandings()

    await waitFor(() => expect(getStandings).toHaveBeenCalledTimes(1))

    vi.mocked(useWebSocket).mockReturnValue({
      lastEvent: { type: 'standings_update', data: { tournament_id: 1 } },
      isConnected: true,
    })

    rerender(
      <MemoryRouter initialEntries={['/standings']}>
        <StandingsScreen />
      </MemoryRouter>,
    )

    await waitFor(() => expect(getStandings).toHaveBeenCalledTimes(2))
  })
})

import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import BracketScreen from '../screens/BracketScreen'
import type { KOBracketResponse, KOMatchupRead, Player } from '../api/types'

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
  getKOBracket: vi.fn(),
  getNextMatches: vi.fn(),
}))

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({ lastEvent: null, isConnected: false })),
}))

import { getPlayers, getKOBracket, getNextMatches } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MOCK_PLAYERS: Player[] = Array.from({ length: 8 }, (_, i) => ({
  id: i + 1,
  name: ['Alice', 'Bob', 'Carol', 'Dave', 'Eve', 'Frank', 'Grace', 'Hank'][i],
  photo_path: null,
  music_path: null,
  championship_count: 0,
}))

function makeMatchup(
  id: number,
  stage: KOMatchupRead['stage'],
  p1: number,
  p2: number,
  winnerId: number | null = null,
): KOMatchupRead {
  return {
    match_id: id,
    stage,
    player1_id: p1,
    player2_id: p2,
    starting_score_p1: 501,
    starting_score_p2: 501,
    status: winnerId !== null ? 'finished' : 'pending',
    winner_id: winnerId,
  }
}

function makeFullBracket(): KOBracketResponse {
  return {
    qualified_players: [],
    quarter_finals: [
      makeMatchup(1, 'qf', 1, 2),
      makeMatchup(2, 'qf', 3, 4),
      makeMatchup(3, 'qf', 5, 6),
      makeMatchup(4, 'qf', 7, 8),
    ],
    semi_finals: [
      makeMatchup(5, 'sf', 1, 3),
      makeMatchup(6, 'sf', 5, 7),
    ],
    final: makeMatchup(7, 'final', 1, 5),
    third_place: makeMatchup(8, 'third_place', 3, 7),
    lightning_player_ids: [],
  }
}

function renderBracket() {
  return render(
    <MemoryRouter initialEntries={['/bracket']}>
      <BracketScreen />
    </MemoryRouter>,
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('BracketScreen', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(useWebSocket).mockReturnValue({ lastEvent: null, isConnected: false })
    vi.mocked(getPlayers).mockResolvedValue(MOCK_PLAYERS)
    vi.mocked(getKOBracket).mockResolvedValue(makeFullBracket())
    vi.mocked(getNextMatches).mockResolvedValue([])
  })

  it('renders all 8 bracket slots (4 QF + 2 SF + Final + 3rd place)', async () => {
    renderBracket()

    await waitFor(() => {
      expect(screen.getAllByTestId('bracket-match')).toHaveLength(8)
    })
  })

  it('displays player names in QF matches', async () => {
    renderBracket()

    // Alice, Bob, Carol all appear (Bob is only in QF1; use getByText for Bob)
    await waitFor(() => expect(screen.getAllByText('Alice').length).toBeGreaterThan(0))
    expect(screen.getByText('Bob')).toBeInTheDocument()
    expect(screen.getAllByText('Carol').length).toBeGreaterThan(0)
  })

  it('highlights the winner in a finished match', async () => {
    const bracket = makeFullBracket()
    // QF1: Alice (id=1) wins vs Bob (id=2)
    bracket.quarter_finals[0] = makeMatchup(1, 'qf', 1, 2, 1)
    vi.mocked(getKOBracket).mockResolvedValue(bracket)

    renderBracket()

    await waitFor(() => expect(screen.getAllByText('Alice').length).toBeGreaterThan(0))

    // Alice appears in QF1 (winner), SF1, and Final — at least one should be marked winner
    const aliceElements = screen.getAllByText('Alice')
    const winnerAlice = aliceElements.find(el =>
      el.closest('.bracket-player')?.classList.contains('bracket-player--winner'),
    )
    expect(winnerAlice).toBeDefined()

    // Bob is only in QF1 and should NOT be the winner
    const bobEl = screen.getByText('Bob').closest('.bracket-player')
    expect(bobEl).not.toHaveClass('bracket-player--winner')
  })

  it('shows empty-state message when bracket is not yet available', async () => {
    vi.mocked(getKOBracket).mockRejectedValue(new Error('not started'))

    renderBracket()

    await waitFor(() => {
      expect(
        screen.getByText('Das KO-Bracket beginnt nach der Vorrunde.'),
      ).toBeInTheDocument()
    })
  })

  it('shows TBD placeholders for SF/Final/3rd when not yet determined', async () => {
    const bracket = makeFullBracket()
    bracket.semi_finals = []
    bracket.final = null
    bracket.third_place = null
    vi.mocked(getKOBracket).mockResolvedValue(bracket)

    renderBracket()

    await waitFor(() => expect(screen.getAllByTestId('bracket-match')).toHaveLength(8))
    // TBD text should appear for the 4 unfilled slots (SF×2, Final, 3rd)
    const tbdElements = screen.getAllByText('TBD')
    // Each TbdMatch renders 2 × "TBD" (player1 + player2)
    expect(tbdElements.length).toBeGreaterThanOrEqual(4)
  })

  it('re-fetches bracket on bracket_update WebSocket event', async () => {
    const { rerender } = renderBracket()

    await waitFor(() => expect(getKOBracket).toHaveBeenCalledTimes(1))

    vi.mocked(useWebSocket).mockReturnValue({
      lastEvent: { type: 'bracket_update', data: { tournament_id: 1 } },
      isConnected: true,
    })

    rerender(
      <MemoryRouter initialEntries={['/bracket']}>
        <BracketScreen />
      </MemoryRouter>,
    )

    await waitFor(() => expect(getKOBracket).toHaveBeenCalledTimes(2))
  })
})

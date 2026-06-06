import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import BullThrowScreen from '../screens/BullThrowScreen'
import { TournamentProvider } from '../contexts/TournamentContext'
import type { BullThrowResponse, MatchRead, Player } from '../api/types'

// ---------------------------------------------------------------------------
// Module mock — must be declared at top level (hoisted by vitest)
// ---------------------------------------------------------------------------

vi.mock('../api/client', () => ({
  API_BASE: 'http://localhost:8000',
  WS_BASE: 'ws://localhost:8000',
  playerPhotoUrl: (path: string) => `http://localhost:8000/static/${path}`,
  getMatch: vi.fn(),
  getPlayers: vi.fn(),
  recordBullThrow: vi.fn(),
  startMatch: vi.fn(),
}))

import { getMatch, getPlayers, recordBullThrow, startMatch } from '../api/client'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

function makePlayer(id: number, name: string): Player {
  return { id, name, photo_path: null, music_path: null, championship_count: 0 }
}

function makeBullResult(starterId: number, order: number[]): BullThrowResponse {
  return { starting_player_id: starterId, play_order: order }
}

function renderBullThrow(matchId = '1') {
  return render(
    <MemoryRouter initialEntries={[`/bull-throw/${matchId}`]}>
      <TournamentProvider>
        <Routes>
          <Route path="/bull-throw/:matchId" element={<BullThrowScreen />} />
          <Route path="/score/:matchId" element={<div>Score Screen</div>} />
          <Route path="/walkon/:matchId" element={<div>Walkon Screen</div>} />
        </Routes>
      </TournamentProvider>
    </MemoryRouter>,
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('BullThrowScreen', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(startMatch).mockResolvedValue({})
  })

  it('renders both player names after loading', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])

    renderBullThrow()

    await waitFor(() => {
      expect(screen.getByText('Lars')).toBeInTheDocument()
      expect(screen.getByText('Mike')).toBeInTheDocument()
    })
  })

  it('clicking a player card and submitting shows result banner', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])
    vi.mocked(recordBullThrow).mockResolvedValue(makeBullResult(10, [10, 20]))

    const user = userEvent.setup()
    renderBullThrow()
    await waitFor(() => screen.getByText('Lars'))

    // Click Lars card (player 10) to select as winner
    await user.click(screen.getByRole('button', { name: /lars/i }))
    await user.click(screen.getByRole('button', { name: /auswerten/i }))

    await waitFor(() => {
      expect(recordBullThrow).toHaveBeenCalledWith(1, { winner_id: 10 })
      expect(screen.getByText('Lars wirft zuerst!')).toBeInTheDocument()
    })
  })

  it('clicking Unentschieden shows tie message and resets selection without calling API', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])

    const user = userEvent.setup()
    renderBullThrow()
    await waitFor(() => screen.getByText('Lars'))

    // Select Lars first, then declare a tie
    await user.click(screen.getByRole('button', { name: /lars/i }))
    await user.click(screen.getByRole('button', { name: /unentschieden/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/unentschieden/i)
    })
    expect(recordBullThrow).not.toHaveBeenCalled()
  })

  it('navigates to score screen after clicking Weiter', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])
    vi.mocked(recordBullThrow).mockResolvedValue(makeBullResult(10, [10, 20]))

    const user = userEvent.setup()
    renderBullThrow()
    await waitFor(() => screen.getByText('Lars'))

    await user.click(screen.getByRole('button', { name: /lars/i }))
    await user.click(screen.getByRole('button', { name: /auswerten/i }))
    await waitFor(() => screen.getByText('Lars wirft zuerst!'))

    await user.click(screen.getByRole('button', { name: /weiter/i }))

    await waitFor(() => {
      expect(startMatch).toHaveBeenCalledWith(1)
      expect(screen.getByText('Score Screen')).toBeInTheDocument()
    })
  })
})

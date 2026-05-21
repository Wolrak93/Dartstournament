import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SetupScreen from '../screens/SetupScreen'
import { TournamentProvider } from '../contexts/TournamentContext'
import type { Player, Tournament } from '../api/types'

// ---------------------------------------------------------------------------
// Module mock — must be declared at top level (hoisted by vitest)
// ---------------------------------------------------------------------------

vi.mock('../api/client', () => ({
  API_BASE: 'http://localhost:8000',
  WS_BASE: 'ws://localhost:8000',
  playerPhotoUrl: (path: string) => `http://localhost:8000/static/${path}`,
  getPlayers: vi.fn(),
  createTournament: vi.fn(),
  startTournament: vi.fn(),
}))

import { getPlayers, createTournament, startTournament } from '../api/client'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makePlayers(count: number): Player[] {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `Player ${i + 1}`,
    photo_path: null,
    music_path: null,
    championship_count: 0,
  }))
}

function renderSetup() {
  return render(
    <MemoryRouter initialEntries={['/setup']}>
      <TournamentProvider>
        <SetupScreen />
      </TournamentProvider>
    </MemoryRouter>,
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SetupScreen', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders the player list returned by the API', async () => {
    vi.mocked(getPlayers).mockResolvedValue(makePlayers(10))

    renderSetup()

    await waitFor(() => {
      expect(screen.getByText('Player 1')).toBeInTheDocument()
    })
    expect(screen.getByText('Player 10')).toBeInTheDocument()
  })

  it('start button is disabled and shows validation error when fewer than 9 players are selected', async () => {
    vi.mocked(getPlayers).mockResolvedValue(makePlayers(5))

    renderSetup()

    // Wait for players to load — none selected by default
    await waitFor(() => expect(screen.getByText('Player 1')).toBeInTheDocument())

    expect(screen.getByRole('button', { name: /turnier starten/i })).toBeDisabled()
    expect(screen.getByRole('alert', { name: undefined })).toBeInTheDocument()
    expect(screen.getByText(/mindestens 9/i)).toBeInTheDocument()
  })

  it('calls createTournament and startTournament when exactly 9 players are selected', async () => {
    vi.mocked(getPlayers).mockResolvedValue(makePlayers(9))
    const mockTournament: Tournament = {
      id: 42,
      created_at: '2026-01-01T00:00:00',
      player_count: 9,
      mode: 'swiss',
      status: 'pending',
    }
    vi.mocked(createTournament).mockResolvedValue(mockTournament)
    vi.mocked(startTournament).mockResolvedValue(undefined)

    const user = userEvent.setup()
    renderSetup()

    // Wait for the player list to render
    await waitFor(() => expect(screen.getByText('Player 1')).toBeInTheDocument())

    // Select all 9 players
    for (let i = 1; i <= 9; i++) {
      await user.click(screen.getByRole('checkbox', { name: `Player ${i}` }))
    }

    // Start button must now be enabled
    const startBtn = screen.getByRole('button', { name: /turnier starten/i })
    expect(startBtn).not.toBeDisabled()

    await user.click(startBtn)

    await waitFor(() => {
      expect(createTournament).toHaveBeenCalledWith({
        player_ids: [1, 2, 3, 4, 5, 6, 7, 8, 9],
        mode: 'swiss',
      })
    })
    expect(startTournament).toHaveBeenCalledWith(42)
  })

  it('mode toggle switches between Swiss and Feste Auslosung', async () => {
    vi.mocked(getPlayers).mockResolvedValue(makePlayers(3))

    const user = userEvent.setup()
    renderSetup()

    await waitFor(() => expect(screen.getByText('Player 1')).toBeInTheDocument())

    const fixedBtn = screen.getByRole('button', { name: /feste auslosung/i })
    await user.click(fixedBtn)

    expect(fixedBtn).toHaveClass('mode-btn--active')
    expect(screen.getByRole('button', { name: /^swiss$/i })).not.toHaveClass(
      'mode-btn--active',
    )
  })

  it('shows an error message when the API call to createTournament fails', async () => {
    vi.mocked(getPlayers).mockResolvedValue(makePlayers(9))
    vi.mocked(createTournament).mockRejectedValue(new Error('Server nicht erreichbar'))

    const user = userEvent.setup()
    renderSetup()

    await waitFor(() => expect(screen.getByText('Player 1')).toBeInTheDocument())

    for (let i = 1; i <= 9; i++) {
      await user.click(screen.getByRole('checkbox', { name: `Player ${i}` }))
    }

    await user.click(screen.getByRole('button', { name: /turnier starten/i }))

    await waitFor(() => {
      expect(screen.getByText('Server nicht erreichbar')).toBeInTheDocument()
    })
  })
})

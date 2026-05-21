import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ScoreEntryScreen from '../screens/ScoreEntryScreen'
import { TournamentProvider } from '../contexts/TournamentContext'
import type { MatchRead, MatchStateResponse, Player, VisitResponse } from '../api/types'
import { splitTotal } from '../utils/dartUtils'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock('../api/client', () => ({
  API_BASE: 'http://localhost:8000',
  WS_BASE: 'ws://localhost:8000',
  playerPhotoUrl: (path: string) => `http://localhost:8000/static/${path}`,
  getMatch: vi.fn(),
  getPlayers: vi.fn(),
  getMatchState: vi.fn(),
  recordVisit: vi.fn(),
}))

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({ lastEvent: null, isConnected: false })),
}))

import { getMatch, getPlayers, getMatchState, recordVisit } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'

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
    starting_player_id: 10,
    status: 'in_progress',
    ...overrides,
  }
}

function makeMatchState(overrides: Partial<MatchStateResponse> = {}): MatchStateResponse {
  return {
    match_id: 1,
    status: 'in_progress',
    round_type: 'vorrunde',
    starting_player_id: 10,
    current_player_id: 10,
    remaining_p1: 301,
    remaining_p2: 301,
    visit_count_p1: 0,
    visit_count_p2: 0,
    single_out_mode: false,
    checkout_suggestion: null,
    ...overrides,
  }
}

function makePlayer(id: number, name: string): Player {
  return { id, name, photo_path: null, music_path: null, championship_count: 0 }
}

function makeVisitResponse(overrides: Partial<VisitResponse> = {}): VisitResponse {
  return {
    visit_id: 1,
    player_id: 10,
    visit_number: 1,
    total: 60,
    is_bust: false,
    remaining_after: 241,
    match_finished: false,
    winner_id: null,
    special_events: [],
    ...overrides,
  }
}

function renderScoreEntry(matchId = '1') {
  return render(
    <MemoryRouter initialEntries={[`/score/${matchId}`]}>
      <TournamentProvider>
        <Routes>
          <Route path="/score/:matchId" element={<ScoreEntryScreen />} />
          <Route path="/standings" element={<div>Standings</div>} />
        </Routes>
      </TournamentProvider>
    </MemoryRouter>,
  )
}

/** Wait for the screen to finish loading (numpad becomes visible). */
async function waitForLoaded() {
  await waitFor(() => screen.getByRole('button', { name: 'DEL' }))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ScoreEntryScreen', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(useWebSocket).mockReturnValue({ lastEvent: null, isConnected: false })
    vi.mocked(getMatch).mockResolvedValue(makeMatch())
    vi.mocked(getPlayers).mockResolvedValue([makePlayer(10, 'Lars'), makePlayer(20, 'Mike')])
    vi.mocked(getMatchState).mockResolvedValue(makeMatchState())
    vi.mocked(recordVisit).mockResolvedValue(makeVisitResponse())
  })

  // ---- initial render ----------------------------------------------------------------

  it('renders both player names and remaining scores after loading', async () => {
    renderScoreEntry()
    await waitForLoaded()

    // Player names appear in player panels and/or active indicator
    expect(screen.queryAllByText('Lars').length).toBeGreaterThan(0)
    expect(screen.queryAllByText('Mike').length).toBeGreaterThan(0)
    // Both start at 301 — each panel shows the remaining score
    expect(screen.getAllByText('301')).toHaveLength(2)
  })

  // ---- numpad input ----------------------------------------------------------------

  it('numpad digit input builds a three-digit number', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '1' }))
    await user.click(screen.getByRole('button', { name: '4' }))
    await user.click(screen.getByRole('button', { name: '0' }))

    expect(screen.getByText('140')).toBeInTheDocument()
  })

  it('DEL removes the last digit', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '1' }))
    await user.click(screen.getByRole('button', { name: '4' }))
    // "14" is now showing — verify it was typed
    expect(screen.getByText('14')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'DEL' }))

    // After DEL, the display should no longer show "14"
    expect(screen.queryByText('14')).not.toBeInTheDocument()
  })

  it('CONFIRM button is disabled when input is empty', async () => {
    renderScoreEntry()
    await waitForLoaded()

    expect(screen.getByRole('button', { name: '✓' })).toBeDisabled()
  })

  it('CONFIRM submits visit with correct player_id and split darts', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    // Type "60"
    await user.click(screen.getByRole('button', { name: '6' }))
    await user.click(screen.getByRole('button', { name: '0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(recordVisit).toHaveBeenCalledWith(1, {
        player_id: 10,
        dart1: 60,
        dart2: 0,
        dart3: 0,
        bounce_flags: [false, false, false],
        robin_hood_flags: [false, false, false],
      })
    })
  })

  it('CONFIRM splits total > 60 across multiple darts', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    // "140" → should split as 60+60+20
    await user.click(screen.getByRole('button', { name: '1' }))
    await user.click(screen.getByRole('button', { name: '4' }))
    await user.click(screen.getByRole('button', { name: '0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(recordVisit).toHaveBeenCalledWith(1, {
        player_id: 10,
        dart1: 60,
        dart2: 60,
        dart3: 20,
        bounce_flags: [false, false, false],
        robin_hood_flags: [false, false, false],
      })
    })
  })

  it('clears the input after a successful confirm', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '6' }))
    await user.click(screen.getByRole('button', { name: '0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(recordVisit).toHaveBeenCalled()
    })
    // The input display should no longer show '60'
    expect(screen.queryByText('60')).not.toBeInTheDocument()
  })

  // ---- bust overlay ----------------------------------------------------------------

  it('shows BUST overlay when recordVisit returns is_bust=true', async () => {
    vi.mocked(recordVisit).mockResolvedValue(makeVisitResponse({ is_bust: true }))
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '6' }))
    await user.click(screen.getByRole('button', { name: '0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(screen.getByText('BUST!')).toBeInTheDocument()
    })
  })

  // ---- checkout suggestion --------------------------------------------------------

  it('shows checkout suggestion when remaining <= 170', async () => {
    vi.mocked(getMatchState).mockResolvedValue(
      makeMatchState({
        remaining_p1: 170,
        checkout_suggestion: {
          darts: ['T20', 'T18', 'Bull'],
          is_finish: true,
          leave: 0,
        },
      }),
    )

    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByText(/T20/)).toBeInTheDocument()
    })
    expect(screen.getByText(/T18/)).toBeInTheDocument()
  })

  it('does not show checkout suggestion when remaining > 170', async () => {
    vi.mocked(getMatchState).mockResolvedValue(
      makeMatchState({
        remaining_p1: 180,
        checkout_suggestion: null,
      }),
    )

    renderScoreEntry()
    await waitForLoaded()

    expect(screen.queryByText(/Checkout/)).not.toBeInTheDocument()
  })

  it('re-fetches match state on WebSocket score_update to update checkout suggestion', async () => {
    const { rerender } = renderScoreEntry()
    await waitFor(() => expect(getMatchState).toHaveBeenCalledTimes(1))

    vi.mocked(useWebSocket).mockReturnValue({
      lastEvent: {
        type: 'score_update',
        data: {
          player_id: 10,
          is_bust: false,
          remaining_after: 170,
          match_finished: false,
          winner_id: null,
        },
      },
      isConnected: true,
    })

    rerender(
      <MemoryRouter initialEntries={['/score/1']}>
        <TournamentProvider>
          <Routes>
            <Route path="/score/:matchId" element={<ScoreEntryScreen />} />
            <Route path="/standings" element={<div>Standings</div>} />
          </Routes>
        </TournamentProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      // Called at least twice: initial load + after WS event
      expect(getMatchState).toHaveBeenCalledTimes(2)
    })
  })

  // ---- single-out banner ----------------------------------------------------------

  it('shows single-out banner when visit_count_p1 >= 15 in vorrunde', async () => {
    vi.mocked(getMatchState).mockResolvedValue(makeMatchState({ visit_count_p1: 15 }))

    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByText(/Single-Out aktiv/i)).toBeInTheDocument()
    })
  })

  it('does not show single-out banner before visit 15', async () => {
    vi.mocked(getMatchState).mockResolvedValue(makeMatchState({ visit_count_p1: 14 }))

    renderScoreEntry()
    await waitForLoaded()

    expect(screen.queryByText(/Single-Out aktiv/i)).not.toBeInTheDocument()
  })

  it('shows single-out banner from visit 25 in KO round', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch({ round_type: 'ko' }))
    vi.mocked(getMatchState).mockResolvedValue(
      makeMatchState({ round_type: 'ko', visit_count_p1: 25 }),
    )

    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByText(/Single-Out aktiv/i)).toBeInTheDocument()
    })
  })

  // ---- match finished overlay -----------------------------------------------------

  it('shows match finished overlay when recordVisit returns match_finished=true', async () => {
    vi.mocked(recordVisit).mockResolvedValue(
      makeVisitResponse({ match_finished: true, winner_id: 10, remaining_after: 0 }),
    )
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '6' }))
    await user.click(screen.getByRole('button', { name: '0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByRole('dialog')).toHaveTextContent('Spiel beendet!')
      expect(screen.getByRole('dialog')).toHaveTextContent('Sieger: Lars')
    })
  })

  it('navigates to standings when "Nächstes Match" is clicked', async () => {
    vi.mocked(recordVisit).mockResolvedValue(
      makeVisitResponse({ match_finished: true, winner_id: 10, remaining_after: 0 }),
    )
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '6' }))
    await user.click(screen.getByRole('button', { name: '0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => screen.getByRole('dialog'))

    await user.click(screen.getByRole('button', { name: /Nächstes Match/i }))

    await waitFor(() => {
      expect(screen.getByText('Standings')).toBeInTheDocument()
    })
  })

  // ---- doubles mode ---------------------------------------------------------------

  it('shows doubles hint to select a player in doubles mode', async () => {
    vi.mocked(getMatch).mockResolvedValue(
      makeMatch({ player3_id: 30, player4_id: 40, round_type: 'vorrunde' }),
    )
    vi.mocked(getPlayers).mockResolvedValue([
      makePlayer(10, 'Lars'),
      makePlayer(20, 'Mike'),
      makePlayer(30, 'Jonas'),
      makePlayer(40, 'Henrik'),
    ])
    vi.mocked(getMatchState).mockResolvedValue(makeMatchState({ current_player_id: null }))

    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByText(/Bitte Spieler antippen/i)).toBeInTheDocument()
    })
  })

  it('in doubles mode, CONFIRM is disabled until a player is selected', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch({ player3_id: 30, player4_id: 40 }))
    vi.mocked(getPlayers).mockResolvedValue([
      makePlayer(10, 'Lars'),
      makePlayer(20, 'Mike'),
      makePlayer(30, 'Jonas'),
      makePlayer(40, 'Henrik'),
    ])
    vi.mocked(getMatchState).mockResolvedValue(makeMatchState({ current_player_id: null }))

    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '6' }))
    await user.click(screen.getByRole('button', { name: '0' }))

    expect(screen.getByRole('button', { name: '✓' })).toBeDisabled()
  })

  // ---- active player indicator ----------------------------------------------------

  it('shows active player indicator in singles mode', async () => {
    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByText(/Am Zug:/i)).toBeInTheDocument()
    })
    // Lars name appears in the indicator
    expect(screen.queryAllByText('Lars').length).toBeGreaterThan(0)
  })

  // ---- input clamps ---------------------------------------------------------------

  it('does not allow input above 180', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    // Type "200" — last digit should be rejected because 200 > 180
    await user.click(screen.getByRole('button', { name: '2' }))
    await user.click(screen.getByRole('button', { name: '0' }))
    await user.click(screen.getByRole('button', { name: '0' }))

    expect(screen.queryByText('200')).not.toBeInTheDocument()
  })

  it('caps input at 3 digits maximum', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '1' }))
    await user.click(screen.getByRole('button', { name: '2' }))
    await user.click(screen.getByRole('button', { name: '3' }))
    // 4th digit should be rejected
    await user.click(screen.getByRole('button', { name: '4' }))

    expect(screen.queryByText('1234')).not.toBeInTheDocument()
    expect(screen.getByText('123')).toBeInTheDocument()
  })

  // ---- error handling -------------------------------------------------------------

  it('shows an error message when recordVisit fails', async () => {
    vi.mocked(recordVisit).mockRejectedValue(new Error('Verbindungsfehler'))
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: '6' }))
    await user.click(screen.getByRole('button', { name: '0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Verbindungsfehler')
    })
  })

  // ---- loading state --------------------------------------------------------------

  it('shows loading indicator initially', () => {
    // Delay resolution so the loading state is visible
    vi.mocked(getMatch).mockReturnValue(new Promise(() => undefined))
    renderScoreEntry()

    expect(screen.getByText('Lade...')).toBeInTheDocument()
  })

  it('shows error page when match fetch fails', async () => {
    vi.mocked(getMatch).mockRejectedValue(new Error('Match nicht gefunden'))
    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Match nicht gefunden')
    })
  })
})

// ---------------------------------------------------------------------------
// splitTotal helper tests (unit, no DOM)
// ---------------------------------------------------------------------------

describe('splitTotal helper', () => {
  it.each([
    [0, [0, 0, 0]],
    [26, [26, 0, 0]],
    [60, [60, 0, 0]],
    [61, [60, 1, 0]],
    [120, [60, 60, 0]],
    [121, [60, 60, 1]],
    [180, [60, 60, 60]],
    [140, [60, 60, 20]],
    [100, [60, 40, 0]],
  ])('splitTotal(%i) → %j', (total, expected) => {
    expect(splitTotal(total)).toEqual(expected)
  })

  it.each([0, 26, 60, 61, 120, 121, 180, 140, 100])(
    'splitTotal(%i) sums back to original',
    (total) => {
      const [d1, d2, d3] = splitTotal(total)
      expect(d1 + d2 + d3).toBe(total)
    },
  )

  it.each([0, 26, 60, 61, 120, 121, 180, 140, 100])(
    'splitTotal(%i) all darts are in range 0–60',
    (total) => {
      const darts = splitTotal(total)
      for (const d of darts) {
        expect(d).toBeGreaterThanOrEqual(0)
        expect(d).toBeLessThanOrEqual(60)
      }
    },
  )
})

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
  getMatchVisits: vi.fn(),
  undoLastVisit: vi.fn(),
  recordVisit: vi.fn(),
}))

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({ lastEvent: null, isConnected: false })),
}))

import { getMatch, getPlayers, getMatchState, getMatchVisits, recordVisit } from '../api/client'
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
    visit_count_p3: null,
    visit_count_p4: null,
    avg_p1: 0,
    avg_p2: 0,
    avg_p3: null,
    avg_p4: null,
    last_visit_total: null,
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

/** Wait for the screen to finish loading (DEL button becomes visible). */
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
    vi.mocked(getMatchVisits).mockResolvedValue([])
    vi.mocked(recordVisit).mockResolvedValue(makeVisitResponse())
  })

  // ---- initial render ----------------------------------------------------------------

  it('renders both player names and remaining scores after loading', async () => {
    renderScoreEntry()
    await waitForLoaded()

    expect(screen.queryAllByText('Lars').length).toBeGreaterThan(0)
    expect(screen.queryAllByText('Mike').length).toBeGreaterThan(0)
    // Both teams start at 301
    expect(screen.getAllByText('301')).toHaveLength(2)
  })

  it('shows player averages (0.00) on initial load', async () => {
    renderScoreEntry()
    await waitForLoaded()

    // Both players start with 0.00 average
    const avgElements = screen.getAllByText('0.00')
    expect(avgElements.length).toBeGreaterThanOrEqual(2)
  })

  // ---- dart field selector ----------------------------------------------------------------

  it('clicking a single field assigns it to dart slot 1', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'T20' }))

    // Slot 1 shows T20
    expect(screen.getByLabelText('Dart 1: T20')).toBeInTheDocument()
  })

  it('clicking three fields enables CONFIRM', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    expect(screen.getByRole('button', { name: '✓' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'T20' }))
    await user.click(screen.getByRole('button', { name: 'T19' }))
    await user.click(screen.getByRole('button', { name: 'D12' }))

    expect(screen.getByRole('button', { name: '✓' })).not.toBeDisabled()
  })

  it('CONFIRM button is disabled when no dart is selected', async () => {
    renderScoreEntry()
    await waitForLoaded()

    expect(screen.getByRole('button', { name: '✓' })).toBeDisabled()
  })

  it('CONFIRM enabled after selecting just one field', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'T20' }))

    expect(screen.getByRole('button', { name: '✓' })).not.toBeDisabled()
  })

  it('CONFIRM submits visit with selected field values', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    // Select T20 (60 pts) as dart 1, leave dart 2 and 3 empty
    await user.click(screen.getByRole('button', { name: 'T20' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(recordVisit).toHaveBeenCalledWith(1, {
        player_id: 10,
        dart1: 60,
        dart2: 0,
        dart3: 0,
        bounce_flags: [false, false, false],
        robin_hood_flags: [false, false, false],
        dart_bands: ['triple', 'miss', 'miss'],
      })
    })
  })

  it('CONFIRM sends multiple dart values when multiple fields selected', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    // T20=60, T19=57, D12=24
    await user.click(screen.getByRole('button', { name: 'T20' }))
    await user.click(screen.getByRole('button', { name: 'T19' }))
    await user.click(screen.getByRole('button', { name: 'D12' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(recordVisit).toHaveBeenCalledWith(1, {
        player_id: 10,
        dart1: 60,
        dart2: 57,
        dart3: 24,
        bounce_flags: [false, false, false],
        robin_hood_flags: [false, false, false],
        dart_bands: ['triple', 'triple', 'double'],
      })
    })
  })

  it('B0 (bounce) button sends bounce_flags=true for that dart', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'B0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(recordVisit).toHaveBeenCalledWith(1, {
        player_id: 10,
        dart1: 0,
        dart2: 0,
        dart3: 0,
        bounce_flags: [true, false, false],
        robin_hood_flags: [false, false, false],
        dart_bands: ['miss', 'miss', 'miss'],
      })
    })
  })

  it('R0 (robin hood) button sends robin_hood_flags=true for that dart', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'R0' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(recordVisit).toHaveBeenCalledWith(1, {
        player_id: 10,
        dart1: 0,
        dart2: 0,
        dart3: 0,
        bounce_flags: [false, false, false],
        robin_hood_flags: [true, false, false],
        dart_bands: ['miss', 'miss', 'miss'],
      })
    })
  })

  it('DEL clears the current dart slot', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'T20' }))
    // Slot 1 now has T20; active slot moved to slot 2
    // Click on slot 1 to re-select it
    await user.click(screen.getByLabelText('Dart 1: T20'))
    // Now DEL clears slot 1
    await user.click(screen.getByRole('button', { name: 'DEL' }))

    expect(screen.getByLabelText('Dart 1: leer')).toBeInTheDocument()
  })

  it('resets dart slots after a successful confirm', async () => {
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'T20' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(recordVisit).toHaveBeenCalled()
    })

    // After confirm, CONFIRM should be disabled again (no darts selected)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '✓' })).toBeDisabled()
    })
  })

  // ---- bust special event popup ---------------------------------------------------

  it('shows BUST special event popup when recordVisit returns is_bust=true with bust event', async () => {
    vi.mocked(recordVisit).mockResolvedValue(
      makeVisitResponse({
        is_bust: true,
        special_events: [{ event_type: 'bust', bonus_value: -1, count: 1, tournament_count: 1 }],
      }),
    )
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'T20' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(screen.getByText('BUST')).toBeInTheDocument()
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
          text: 'T20 T18 Bull',
        },
      }),
    )

    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByText('T20 T18 Bull')).toBeInTheDocument()
    })
  })

  it('shows raw text from checkout table for non-finish suggestions', async () => {
    vi.mocked(getMatchState).mockResolvedValue(
      makeMatchState({
        remaining_p1: 229,
        checkout_suggestion: {
          darts: ['T20'],
          is_finish: false,
          leave: 169,
          text: 'No Finish (T20)',
        },
      }),
    )

    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByText('No Finish (T20)')).toBeInTheDocument()
    })
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

    // Checkout is only shown in the team block when activePlayerId matches
    // and checkout_suggestion is non-null; here it's null so nothing to show
    expect(screen.queryByText(/T20.*T18/)).not.toBeInTheDocument()
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

  it('shows single-out banner when single_out_mode=true in vorrunde', async () => {
    vi.mocked(getMatchState).mockResolvedValue(
      makeMatchState({ visit_count_p1: 15, single_out_mode: true }),
    )

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

  it('shows single-out banner when single_out_mode=true in KO round', async () => {
    vi.mocked(getMatch).mockResolvedValue(makeMatch({ round_type: 'ko' }))
    vi.mocked(getMatchState).mockResolvedValue(
      makeMatchState({ round_type: 'ko', visit_count_p1: 25, single_out_mode: true }),
    )

    renderScoreEntry()

    await waitFor(() => {
      expect(screen.getByText(/Single-Out aktiv/i)).toBeInTheDocument()
    })
  })

  it('updates single-out checkout to "No Finish (T20)" after one dart entered mid-visit', async () => {
    // Remaining 123, single-out active: server suggestion for 3 darts = "T20 T20 S3".
    // After entering S20 (20 pts), remaining → 103, dartsLeft = 2.
    // 103 cannot be finished in 2 darts single-out → expect "No Finish (T20)".
    vi.mocked(getMatchState).mockResolvedValue(
      makeMatchState({
        remaining_p1: 123,
        single_out_mode: true,
        checkout_suggestion: {
          darts: ['T20', 'T20', 'S3'],
          is_finish: true,
          leave: 0,
          text: 'T20 T20 S3',
        },
      }),
    )

    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    // Initial server suggestion shown
    expect(screen.getByText('T20 T20 S3')).toBeInTheDocument()

    // Enter single 20 (label "20", value 20) as first dart
    await user.click(screen.getByRole('button', { name: '20' }))

    // Checkout should now show "No Finish (T20)" for remaining=103, 2 darts left
    expect(screen.getByText('No Finish (T20)')).toBeInTheDocument()
    expect(screen.queryByText('T20 T20 S3')).not.toBeInTheDocument()
  })

  // ---- match finished overlay -----------------------------------------------------

  it('shows match finished overlay when recordVisit returns match_finished=true', async () => {
    vi.mocked(recordVisit).mockResolvedValue(
      makeVisitResponse({ match_finished: true, winner_id: 10, remaining_after: 0 }),
    )
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'T20' }))
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

    await user.click(screen.getByRole('button', { name: 'T20' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => screen.getByRole('dialog'))

    await user.click(screen.getByRole('button', { name: /Nächstes Match/i }))

    await waitFor(() => {
      expect(screen.getByText('Standings')).toBeInTheDocument()
    })
  })

  // ---- doubles mode ---------------------------------------------------------------

  it('renders all four player names in doubles mode', async () => {
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
      expect(screen.getByText('Lars')).toBeInTheDocument()
      expect(screen.getByText('Jonas')).toBeInTheDocument()
      expect(screen.getByText('Mike')).toBeInTheDocument()
      expect(screen.getByText('Henrik')).toBeInTheDocument()
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

    await user.click(screen.getByRole('button', { name: 'T20' }))

    expect(screen.getByRole('button', { name: '✓' })).toBeDisabled()
  })

  // ---- active player indicator (singles) ------------------------------------------

  it('shows active player indicator arrow in singles mode', async () => {
    renderScoreEntry()
    await waitForLoaded()

    // The ">" arrow is shown before the active player's name
    expect(screen.getByText('>')).toBeInTheDocument()
    expect(screen.queryAllByText('Lars').length).toBeGreaterThan(0)
  })

  // ---- error handling -------------------------------------------------------------

  it('shows an error message when recordVisit fails', async () => {
    vi.mocked(recordVisit).mockRejectedValue(new Error('Verbindungsfehler'))
    const user = userEvent.setup()
    renderScoreEntry()
    await waitForLoaded()

    await user.click(screen.getByRole('button', { name: 'T20' }))
    await user.click(screen.getByRole('button', { name: '✓' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Verbindungsfehler')
    })
  })

  // ---- loading state --------------------------------------------------------------

  it('shows loading indicator initially', () => {
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

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
